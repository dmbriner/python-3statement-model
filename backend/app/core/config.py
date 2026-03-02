from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "3-Statement Platform API"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    database_url: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/statement_model")

    auth_provider: str = Field(default="clerk")
    clerk_secret_key: str | None = None
    clerk_publishable_key: str | None = None
    clerk_jwt_issuer: str | None = None

    alpha_vantage_api_key: str | None = None
    fmp_api_key: str | None = None
    financial_modeling_prep_api_key: str | None = None


settings = Settings()
