from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "SIH26129 Interoperability API"
    database_url: str = f"sqlite:///{(BASE_DIR / 'sih26129.db').as_posix()}"
    debug: bool = True
    secret_key: str = "sih26129-intergov-mesh-secret-key-2026"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
