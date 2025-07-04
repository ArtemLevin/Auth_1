import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.routes import auth, roles
from app.settings import settings
from app.utils.cache import redis_client, test_connection
from app.core.logging_config import setup_logging
from app.utils.rate_limiter import RedisLeakyBucketRateLimiter

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Приложение запускается...")
    await test_connection()
    app.state.rate_limiter = RedisLeakyBucketRateLimiter(redis_client, settings)
    yield
    logger.info("Приложение завершает работу...")
    await redis_client.close()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    docs_url=f"{settings.api_v1_str}/docs",
    redoc_url=f"{settings.api_v1_str}/redoc",
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.social_auth_secret_key)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.api_v1_str)
# app.include_router(social_auth.router, prefix=settings.api_v1_str)
app.include_router(roles.router, prefix=settings.api_v1_str)

async def get_rate_limiter(request: Request) -> RedisLeakyBucketRateLimiter:
    return request.app.state.rate_limiter
