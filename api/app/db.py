# -*- coding: utf-8 -*-
"""Pool de conexões com o Postgres."""
from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from .config import config

_pool: AsyncConnectionPool | None = None


async def abrir() -> None:
    global _pool
    if config.database_url and _pool is None:
        _pool = AsyncConnectionPool(config.database_url, min_size=1, max_size=8,
                                    open=False, kwargs={"row_factory": dict_row})
        await _pool.open()


async def fechar() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def disponivel() -> bool:
    return _pool is not None


@asynccontextmanager
async def conexao():
    if _pool is None:
        raise RuntimeError("banco não configurado: defina DATABASE_URL")
    async with _pool.connection() as con:
        yield con
