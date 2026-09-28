from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "SIH26129 Interoperability API"
    database_url: str = "postgresql+psycopg://localhost/govflow"
    debug: bool = True
    data_mode: str = "production"
    secret_key: str = "change-this-secret-before-deployment"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    auth_cookie_secure: bool | None = None
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:8081",
            "http://127.0.0.1:8081",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if not self.debug and (
            self.secret_key == "change-this-secret-before-deployment"
            or len(self.secret_key) < 32
        ):
            raise ValueError("SECRET_KEY must be at least 32 characters when DEBUG is false.")
        if self.access_token_expire_minutes <= 0 or self.refresh_token_expire_days <= 0:
            raise ValueError("Authentication token lifetimes must be positive.")
        if self.auth_cookie_samesite == "none" and self.auth_cookie_secure is False:
            raise ValueError("SameSite=None refresh cookies must be Secure.")
        return self


settings = Settings()
