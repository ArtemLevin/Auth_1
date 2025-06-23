from typing import List, Literal
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_DIR = Path(__file__).resolve().parents[1]

class ConfigBase(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env", case_sensitive=False, env_file_encoding="utf-8", extra="ignore"
    )
    

class Settings(ConfigBase):
    ENVIRONMENT: Literal["development", "test", "staging", "production"] = "development"

    APP_NAME: str = Field("")
    APP_DESCRIPTION: str = Field("")
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: SecretStr = Field(..., description="PostgreSQL username for database authentication")
    POSTGRES_PASSWORD: SecretStr = Field(..., description="PostgreSQL password for the specified user")
    POSTGRES_DB: SecretStr = Field(..., description="Name of the PostgreSQL database to connect to")
    POSTGRES_PORT: int = Field(..., description="Port number PostgreSQL is running on")
    POSTGRES_HOST: SecretStr = Field(..., description="Hostname or IP address where PostgreSQL is hosted")

    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    JWT_SECRET_KEY: SecretStr = Field(..., description="Secret key for access tokens")
    JWT_REFRESH_SECRET_KEY: SecretStr = Field(
        ..., description="Secret key for refresh tokens"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REDIS_URL: SecretStr = Field(
        default=SecretStr("redis://localhost:6379"),
        description="URL подключения к Redis",
    )

    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = False

    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["*"]
    RATE_LIMIT_DEFAULT: str = "5/minute"
    RATE_LIMIT_STORAGE: str = "redis"

    MFA_TOTP_ISSUER: str = "OnlineCinema Auth"

    # @field_validator("DATABASE_URL", mode="after")
    # def check_database_url(cls, v):
    #     if not v.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
    #         raise ValueError(
    #             "DATABASE_URL должен начинаться с postgresql+asyncpg:// или sqlite+aiosqlite://"
    #         )
    #     return v

    @field_validator("JWT_SECRET_KEY", "JWT_REFRESH_SECRET_KEY", mode="after")
    def check_jwt_secrets(cls, v: SecretStr, info):
        if len(v.get_secret_value()) < 16:
            raise ValueError(
                f"{info.field_name} должен быть длиной не менее 16 символов"
            )
        return v

    @field_validator("REDIS_URL", mode="after")
    def parse_redis_url(cls, v: SecretStr):
        url = v.get_secret_value()
        if not url.startswith("redis://"):
            raise ValueError("REDIS_URL должен начинаться с redis://")
        return v


settings = Settings()

if __name__ == "__main__":
    print(settings.model_dump(exclude={"JWT_SECRET_KEY", "JWT_REFRESH_SECRET_KEY"}))
    print(PROJECT_DIR)