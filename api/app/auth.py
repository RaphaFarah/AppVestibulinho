# -*- coding: utf-8 -*-
"""Validação do JWT emitido pelo Supabase Auth.

Senha nunca chega nesta API: o React autentica direto no Supabase, recebe o
token e manda no cabeçalho. Aqui só se verifica a assinatura e se extrai o id
do usuário. Assim nenhuma rotina de senha, confirmação de e-mail ou reset
precisa existir neste código -- é onde mais se erra em autenticação artesanal.

Dois formatos de assinatura são aceitos:
  * HS256 com o JWT Secret do projeto (projetos Supabase mais antigos)
  * RS256/ES256 verificado contra o JWKS público (projetos novos)
"""
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import config

_esquema = HTTPBearer(auto_error=False)
_jwks: PyJWKClient | None = None


def _cliente_jwks() -> PyJWKClient:
    global _jwks
    if _jwks is None:
        # cacheia as chaves para não buscar o JWKS a cada requisição
        _jwks = PyJWKClient(config.jwks_url, cache_keys=True)
    return _jwks


def _decodificar(token: str) -> dict:
    comum = dict(audience="authenticated", options={"require": ["exp", "sub"]})
    if config.supabase_jwt_secret:
        return jwt.decode(token, config.supabase_jwt_secret,
                          algorithms=["HS256"], **comum)
    chave = _cliente_jwks().get_signing_key_from_jwt(token).key
    return jwt.decode(token, chave, algorithms=["RS256", "ES256"], **comum)


async def usuario_atual(
    cred: HTTPAuthorizationCredentials | None = Depends(_esquema),
) -> str:
    """Devolve o id (uuid) do usuário autenticado, ou 401."""
    # sem isto, ambiente não configurado devolve 500 em vez de dizer o que falta
    if not (config.supabase_jwt_secret or config.supabase_url):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "autenticação não configurada: defina SUPABASE_URL")
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token ausente",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        dados = _decodificar(cred.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expirado")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"token inválido: {e}")
    except PyJWKClientError as e:
        # não herda de InvalidTokenError: sem este ramo, vira 500
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            f"não foi possível validar o token: {e}")
    sub = dados.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token sem sub")
    return sub
