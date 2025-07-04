import time
from typing import List
import structlog
from redis import asyncio as aioredis
from redis.commands.json.path import Path

from app.settings import Settings, settings

from app.schemas.ratelimiting import RateLimitConfigDict, RateLimitConfig, RoleBasedLimits

logger = structlog.get_logger(__name__)


class RedisLeakyBucketRateLimiter:
    def __init__(self, redis_client: aioredis.Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings
        self.rate_limit_config: RateLimitConfigDict = settings.rate_limit_config

    async def _get_effective_config(self, user_roles: List[str], traffic_type: str) -> RateLimitConfig:
        config_for_traffic_type: RoleBasedLimits = getattr(self.rate_limit_config, traffic_type,
                                                           self.rate_limit_config.default)

        effective_config: RateLimitConfig = config_for_traffic_type.default

        if "superuser" in user_roles and config_for_traffic_type.superuser:
            effective_config = config_for_traffic_type.superuser
        elif "premium" in user_roles and config_for_traffic_type.premium:
            effective_config = config_for_traffic_type.premium
        elif "user" in user_roles and config_for_traffic_type.user:
            effective_config = config_for_traffic_type.user
        elif "guest" in user_roles and config_for_traffic_type.guest:
            effective_config = config_for_traffic_type.guest

        return effective_config


async def allow_request(self, identifier: str, user_roles: List[str], traffic_type: str = "default") -> bool:
    key = f"rate_limit:{traffic_type}:{identifier}"

    config: RateLimitConfig = await self._get_effective_config(user_roles, traffic_type)
    capacity = config.capacity
    leak_rate = config.leak_rate
    ttl_seconds = config.ttl_seconds

    current_time = time.time()

    bucket_state = await self.redis.json().get(key, Path.root())

    if bucket_state is None:
        current_level = 1.0
        last_refill_time = current_time
        logger.debug("Rate limit bucket initialized", key=key, identifier=identifier, traffic_type=traffic_type,
                     capacity=capacity, leak_rate=leak_rate)
    else:
        last_refill_time = bucket_state.get("last_refill", current_time)
        previous_level = bucket_state.get("level", 0.0)

        time_passed = current_time - last_refill_time
        leaked_amount = time_passed * leak_rate

        current_level = max(0.0, previous_level - leaked_amount)

        current_level += 1.0
        last_refill_time = current_time

        logger.debug("Rate limit bucket updated", key=key, identifier=identifier, traffic_type=traffic_type,
                     previous_level=previous_level, leaked_amount=leaked_amount,
                     current_level_after_leak=current_level - 1.0, new_level=current_level)


    if current_level > capacity:
        logger.warning("Rate limit exceeded", key=key, identifier=identifier, traffic_type=traffic_type,
                       current_level=current_level, capacity=capacity)
        return False

    await self.redis.json().set(key, Path.root(), {"level": current_level, "last_refill": last_refill_time})
    await self.redis.expire(key, ttl_seconds)

    logger.debug("Request allowed", key=key, identifier=identifier, traffic_type=traffic_type, current_level=current_level,
                 capacity=capacity)
    return True



async def get_rate_limiter(
    redis_client: aioredis.Redis,
    settings: Settings
) -> RedisLeakyBucketRateLimiter:

    return RedisLeakyBucketRateLimiter(redis_client, settings)