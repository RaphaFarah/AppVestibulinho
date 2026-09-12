# -*- coding: utf-8 -*-
"""API do AppVestibulinho.

Responsabilidade única: guardar e devolver o que o aluno respondeu. O banco de
questões não passa por aqui -- é estático e servido como arquivo, o que deixa o
simulado rodar offline e mantém esta API fora do caminho crítico.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .auth import usuario_atual
from .config import config
from .schemas import (DesempenhoItem, TentativaEnviada, TentativaResumo)


@asynccontextmanager
async def ciclo(app: FastAPI):
    await db.abrir()
    yield
    await db.fechar()


app = FastAPI(title="AppVestibulinho", version="0.1.0",
              summary="Tentativas e desempenho em provas simuladas",
              lifespan=ciclo)

app.add_middleware(CORSMiddleware, allow_origins=config.origens,
                   allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])


async def usuario_com_banco(usuario: str = Depends(usuario_atual)) -> str:
    """Autentica e só então confere a infraestrutura.

    A ordem importa: dependência de rota executa antes de dependência de
    parâmetro, então declarar a guarda do banco no decorador fazia quem chamava
    sem token receber 503 -- revelando estado de configuração do servidor a um
    chamador anônimo, que deve receber 401 e nada mais."""
    if not db.disponivel():
        raise HTTPException(503, "banco não configurado: defina DATABASE_URL")
    return usuario


@app.get("/saude", tags=["infra"])
async def saude() -> dict:
    """Diz se a API subiu e se o ambiente já está configurado."""
    return {"ok": True, "banco": db.disponivel(),
            "auth": bool(config.supabase_url),
            "modo_assinatura": "HS256" if config.supabase_jwt_secret else "JWKS"}


@app.post("/tentativas", tags=["tentativas"], status_code=201)
async def gravar_tentativa(env: TentativaEnviada,
                           usuario: str = Depends(usuario_com_banco)) -> dict:
    """Grava uma prova terminada. Idempotente por (usuário, cliente_id)."""
    if len(env.respostas) != env.total_questoes:
        raise HTTPException(422, f"{len(env.respostas)} respostas para "
                                 f"{env.total_questoes} questões")
    acertos = sum(1 for r in env.respostas if r.correta)
    async with db.conexao() as con:
        async with con.cursor() as cur:
            await cur.execute(
                """insert into tentativa (usuario_id, cliente_id, modo, semente,
                       total_questoes, duracao_segundos, acertos, finalizado_em)
                   values (%s,%s,%s,%s,%s,%s,%s,%s)
                   on conflict (usuario_id, cliente_id) do update
                       set acertos = excluded.acertos,
                           duracao_segundos = excluded.duracao_segundos,
                           finalizado_em = excluded.finalizado_em
                   returning id, (criado_em = now()) as nova""",
                (usuario, env.cliente_id, env.modo, env.semente,
                 env.total_questoes, env.duracao_segundos, acertos,
                 env.finalizado_em))
            tentativa_id = (await cur.fetchone())["id"]

            # reenvio substitui as respostas, nunca duplica
            await cur.execute("delete from resposta where tentativa_id = %s",
                              (tentativa_id,))
            await cur.executemany(
                """insert into resposta (tentativa_id, questao_id, marcada,
                                         correta, segundos)
                   values (%s,%s,%s,%s,%s)""",
                [(tentativa_id, r.questao_id, r.marcada, r.correta, r.segundos)
                 for r in env.respostas])
    return {"id": str(tentativa_id), "acertos": acertos,
            "total": env.total_questoes}


@app.get("/tentativas", tags=["tentativas"])
async def listar_tentativas(limite: int = 50,
                            usuario: str = Depends(usuario_com_banco)
                            ) -> list[TentativaResumo]:
    async with db.conexao() as con:
        cur = await con.execute(
            """select id::text, cliente_id, modo, total_questoes, acertos,
                      duracao_segundos, criado_em, finalizado_em
                 from tentativa where usuario_id = %s
                order by criado_em desc limit %s""",
            (usuario, min(limite, 200)))
        return [TentativaResumo(**r) for r in await cur.fetchall()]


@app.get("/desempenho", tags=["desempenho"])
async def desempenho(usuario: str = Depends(usuario_com_banco)
                     ) -> list[DesempenhoItem]:
    """Acertos por questão, para o app apontar onde o aluno erra mais."""
    async with db.conexao() as con:
        cur = await con.execute(
            """select questao_id, respondidas, acertos, segundos_medio
                 from v_desempenho where usuario_id = %s
                order by acertos::float / respondidas, respondidas desc""",
            (usuario,))
        return [DesempenhoItem(**r) for r in await cur.fetchall()]
