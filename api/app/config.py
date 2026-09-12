# -*- coding: utf-8 -*-
"""Configuração lida do ambiente. Nenhum segredo mora no código."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres do Supabase (Project Settings -> Database -> Connection string)
    database_url: str = ""

    # URL do projeto Supabase, ex. https://xxxx.supabase.co
    supabase_url: str = ""

    # Projetos antigos assinam o JWT em HS256 com este segredo compartilhado
    # (Project Settings -> API -> JWT Secret). Projetos novos usam chave
    # assimétrica e o segredo fica vazio: aí a validação usa o JWKS público.
    supabase_jwt_secret: str = ""

    # Origens autorizadas a chamar a API, separadas por vírgula
    cors_origins: str = "http://localhost:5173"

    @property
    def origens(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def configurado(self) -> bool:
        return bool(self.database_url and self.supabase_url)


config = Config()
