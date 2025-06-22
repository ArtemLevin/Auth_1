import structlog
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse  # Для кастомного обработчика исключений
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_ipaddr

from app.api.v1.routes import auth, roles
from app.settings import settings
from app.utils.cache import redis_client, test_connection
from app.core.logging_config import setup_logging
from app.schemas.error import ErrorResponseModel

logger = structlog.get_logger(__name__)

# Определяем временный тип для app.state, чтобы добавить атрибут limiter
if TYPE_CHECKING:
    from starlette.datastructures import State as StarletteState

    class AppStateWithLimiter(StarletteState):
        limiter: Limiter
else:
    AppStateWithLimiter = object  # Заглушка для runtime, если TYPE_CHECKING не True

limiter = Limiter(
    key_func=get_ipaddr,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.REDIS_URL.get_secret_value(),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Приложение запускается...")
    await test_connection()
    yield
    logger.info("Приложение завершает работу...")
    await redis_client.close()


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="0.1.0",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Явно приводим тип app.state
app.state = cast(AppStateWithLimiter, app.state)
app.state.limiter = limiter


# Обработчик исключений для RateLimitExceeded
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(
        "Превышен лимит запросов", ip_address=request.client.host, detail=exc.detail
    )
    error_detail = {"rate_limit": f"Rate limit exceeded: {exc.detail}"}
    return JSONResponse(
        content=ErrorResponseModel(detail=error_detail).model_dump(),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )


# Используем собственный обработчик
app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(roles.router, prefix=settings.API_V1_STR)
