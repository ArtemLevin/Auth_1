from redis import asyncio as aioredis
import structlog

from app.settings import settings

logger = structlog.get_logger(__name__)

redis_client = aioredis.from_url(
    settings.redis_url.get_secret_value(), decode_responses=True
)


async def get_redis_client() -> aioredis.Redis:
    return redis_client


async def test_connection():
    try:
        pong = await redis_client.ping()
        if pong:
            logger.info("Подключение к Redis успешно")
    except Exception as e:
        logger.error("Ошибка подключения к Redis", error=str(e))