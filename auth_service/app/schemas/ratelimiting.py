from pydantic import BaseModel


class RateLimitConfig(BaseModel):
    capacity: int
    leak_rate: float
    ttl_seconds: int  #


class RoleBasedLimits(BaseModel):
    default: RateLimitConfig
    guest: RateLimitConfig | None = None
    user: RateLimitConfig | None = None
    premium: RateLimitConfig | None = None
    superuser: RateLimitConfig | None = None


class RateLimitConfigDict(BaseModel):
    default: RoleBasedLimits
    login: RoleBasedLimits | None = None
    register: RoleBasedLimits | None = None
