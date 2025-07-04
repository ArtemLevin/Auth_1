import os
from typing import List, Literal

from app.schemas.ratelimiting import (RateLimitConfig, RateLimitConfigDict,
                                      RoleBasedLimits)
from dotenv import load_dotenv
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

DOTENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(DOTENV_PATH)

class Settings(BaseSettings):
    environment: Literal["development", "test", "staging", "production"] = "development"

    app_name: str = "Auth Service"
    debug: bool = False
    api_v1_str: str = "/api/v1"

    # ключи авторизации
    social_auth_secret_key: str = Field(None, description="Secret key")
    yandex_client_id: str = Field(None, description="Yandex client Id")
    yandex_client_secret: str = Field(None, description="Yandex client Secret")

    vk_client_id: str = Field(None, description="VK client Id")
    vk_client_secret: str = Field(None, description="VK client Secret")

    google_client_id: str = Field(None, description="Google client Id")
    google_client_secret: str = Field(None, description="Google client Secret")

    database_url: str = Field(..., description="PostgreSQL async URL")
    test_database_url: str = Field(..., description="PostgreSQL async URL for tests")
    sync_database_url: str = ""

    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False

    jwt_secret_key: SecretStr = Field(..., description="Secret key for access tokens")
    jwt_refresh_secret_key: SecretStr = Field(
        ..., description="Secret key for refresh tokens"
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    redis_url: SecretStr = Field(
        default=SecretStr("redis://localhost:6379"),
        description="URL подключения к Redis",
    )

    log_level: str = "INFO"
    log_json_format: bool = False

    allowed_hosts: List[str] = ["*"]
    cors_origins: List[str] = ["*"]

    mfa_totp_issuer: str = "OnlineCinema Auth"

    rate_limit_config: RateLimitConfigDict = Field(
        default_factory=lambda: RateLimitConfigDict(
            default=RoleBasedLimits(
                default=RateLimitConfig(capacity=10, leak_rate=1, ttl_seconds=60),
                guest=RateLimitConfig(capacity=5, leak_rate=0.5, ttl_seconds=60),
                user=RateLimitConfig(capacity=20, leak_rate=2, ttl_seconds=300),
                premium=RateLimitConfig(capacity=100, leak_rate=10, ttl_seconds=3600),
                superuser=RateLimitConfig(capacity=500, leak_rate=50, ttl_seconds=86400),
            ),
            login=RoleBasedLimits(
                default=RateLimitConfig(capacity=5, leak_rate=0.5, ttl_seconds=300),
                guest=RateLimitConfig(capacity=3, leak_rate=0.3, ttl_seconds=300),
                user=RateLimitConfig(capacity=10, leak_rate=1, ttl_seconds=600),
                premium=RateLimitConfig(capacity=20, leak_rate=2, ttl_seconds=1200),
                superuser=RateLimitConfig(capacity=50, leak_rate=5, ttl_seconds=3600),
            ),
            register=RoleBasedLimits(
                default=RateLimitConfig(capacity=3, leak_rate=0.3, ttl_seconds=300),
            )
        )
    )

    @field_validator("database_url", mode="after")
    def check_database_url(cls, v, info):
        if not v.startswith(("postgresql+asyncpg://", "sqlite+aiosqlite://")):
            raise ValueError(
                "database_url должен начинаться с postgresql+asyncpg:// или sqlite+aiosqlite://"
            )
        info.data["sync_database_url"] = v.replace("+asyncpg", "")
        return v

    @field_validator("jwt_secret_key", "jwt_refresh_secret_key", mode="after")
    def check_jwt_secrets(cls, v: SecretStr, info):
        if len(v.get_secret_value()) < 16:
            raise ValueError(
                f"{info.field_name} должен быть длиной не менее 16 символов"
            )
        return v

    @field_validator("redis_url", mode="after")
    def parse_redis_url(cls, v: SecretStr):
        url = v.get_secret_value()
        if not url.startswith("redis://"):
            raise ValueError("redis_url должен начинаться с redis://")
        return v

settings = Settings()

if __name__ == "__main__":
    print(settings.model_dump(exclude={"jwt_secret_key", "jwt_refresh_secret_key"}))