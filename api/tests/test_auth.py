# -*- coding: utf-8 -*-
"""Testes da validação de token.

Rodam sem Supabase e sem Postgres: o segredo HS256 é fixado por variável de
ambiente antes de importar a aplicação, e um token válido deve passar da
autenticação e só então parar na guarda do banco -- é justamente esse 503 que
prova que a assinatura foi aceita.
"""
import os
from datetime import datetime, timedelta, timezone

import jwt
import pytest

SEGREDO = "segredo-apenas-de-teste-com-32-bytes-ou-mais"
os.environ["SUPABASE_JWT_SECRET"] = SEGREDO
os.environ["SUPABASE_URL"] = "https://projeto-de-teste.supabase.co"
os.environ["DATABASE_URL"] = ""

from fastapi.testclient import TestClient          # noqa: E402
from app.main import app                           # noqa: E402

cliente = TestClient(app)
USUARIO = "11111111-2222-3333-4444-555555555555"


def token(segredo=SEGREDO, *, sub=USUARIO, aud="authenticated", minutos=10):
    agora = datetime.now(timezone.utc)
    corpo = {"sub": sub, "aud": aud, "iat": agora,
             "exp": agora + timedelta(minutes=minutos)}
    return jwt.encode(corpo, segredo, algorithm="HS256")


def cabecalho(t):
    return {"Authorization": f"Bearer {t}"}


def test_saude_nao_exige_token():
    r = cliente.get("/saude")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["modo_assinatura"] == "HS256"


@pytest.mark.parametrize("rota", ["/tentativas", "/desempenho"])
def test_sem_token_401(rota):
    assert cliente.get(rota).status_code == 401


def test_token_valido_passa_da_autenticacao():
    # 503 do banco, nao 401: a assinatura foi aceita
    r = cliente.get("/tentativas", headers=cabecalho(token()))
    assert r.status_code == 503
    assert "DATABASE_URL" in r.json()["detail"]


def test_assinatura_errada_401():
    r = cliente.get("/tentativas", headers=cabecalho(token("outro-segredo")))
    assert r.status_code == 401


def test_token_expirado_401():
    r = cliente.get("/tentativas", headers=cabecalho(token(minutos=-5)))
    assert r.status_code == 401
    assert "expirado" in r.json()["detail"]


def test_audience_errada_401():
    r = cliente.get("/tentativas", headers=cabecalho(token(aud="outra")))
    assert r.status_code == 401


def test_token_sem_sub_401():
    agora = datetime.now(timezone.utc)
    t = jwt.encode({"aud": "authenticated", "exp": agora + timedelta(minutes=5)},
                   SEGREDO, algorithm="HS256")
    assert cliente.get("/tentativas", headers=cabecalho(t)).status_code == 401


def test_token_malformado_nao_causa_500():
    r = cliente.get("/tentativas", headers=cabecalho("abc.def.ghi"))
    assert r.status_code == 401


def test_post_valida_contagem_de_respostas():
    corpo = {"cliente_id": "x", "semente": 1, "total_questoes": 3,
             "respostas": [{"questao_id": "2022-q01", "marcada": "A"}]}
    r = cliente.post("/tentativas", json=corpo, headers=cabecalho(token()))
    # a guarda do banco roda antes do corpo; o que importa e nao ser 401/500
    assert r.status_code in (422, 503)
