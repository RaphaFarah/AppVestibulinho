# -*- coding: utf-8 -*-
"""Contratos de entrada e saída da API."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Letra = Literal["A", "B", "C", "D", "E"]


class RespostaEnviada(BaseModel):
    questao_id: str = Field(max_length=32, examples=["2022-q44"])
    marcada: Letra | None = None          # None = deixou em branco
    correta: bool | None = None
    segundos: int | None = Field(default=None, ge=0)


class TentativaEnviada(BaseModel):
    """Prova terminada, enviada pela fila de sincronização do app.

    `cliente_id` é gerado no aparelho antes de haver rede; é ele que torna o
    envio idempotente, para que reenviar após falha não duplique a tentativa."""
    cliente_id: str = Field(max_length=64)
    modo: Literal["simulado", "treino"] = "simulado"
    semente: int
    total_questoes: int = Field(ge=1)
    duracao_segundos: int | None = Field(default=None, ge=0)
    finalizado_em: datetime | None = None
    respostas: list[RespostaEnviada]


class TentativaResumo(BaseModel):
    id: str
    cliente_id: str
    modo: str
    total_questoes: int
    acertos: int | None
    duracao_segundos: int | None
    criado_em: datetime
    finalizado_em: datetime | None


class DesempenhoItem(BaseModel):
    questao_id: str
    respondidas: int
    acertos: int
    segundos_medio: float | None
