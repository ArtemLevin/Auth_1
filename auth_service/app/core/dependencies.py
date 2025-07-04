from typing import Any
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose.exceptions import ExpiredSignatureError, JWTError

from app.core.security import decode_jwt
from app.db.session import get_db_session
from app.models import Role, User, UserRole
from app.schemas.error import ErrorResponseModel
from app.utils.cache import redis_client
from app.utils.rate_limiter import RedisLeakyBucketRateLimiter

from app.utils.rate_limiter import get_rate_limiter

logger = structlog.get_logger(__name__)
http_bearer = HTTPBearer(auto_error=False)


async def get_cached_permissions(user_id: UUID, db: AsyncSession) -> list[str]:
    user_id_str = str(user_id)
    permissions_str = await redis_client.get(f"permissions:{user_id_str}")
    if permissions_str:
        logger.debug("Разрешения получены из кэша Redis", user_id=user_id_str)
        return permissions_str.split(",")

    user_result = await db.execute(select(User.is_superuser).where(User.id == user_id))
    is_superuser = user_result.scalar_one_or_none()

    if is_superuser:
        logger.info(
            "Пользователь является суперпользователем, добавлены все разрешения",
            user_id=user_id_str,
        )
        permissions_list = ["*"]
    else:
        result = await db.execute(
            select(Role.permissions)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        all_permissions = set()
        for row in result.scalars().all():
            all_permissions.update(row)

        permissions_list = list(all_permissions)
        if not permissions_list:
            logger.info(
                "Для пользователя не найдено разрешений, по умолчанию 'view_content'",
                user_id=user_id_str,
            )
            permissions_list = ["view_content"]

    if permissions_list:
        await redis_client.setex(
            f"permissions:{user_id_str}", 3600, ",".join(permissions_list)
        )
        logger.debug("Разрешения кэшированы в Redis", user_id=user_id_str)

    return permissions_list


async def get_user_roles(user_id: UUID, db: AsyncSession) -> list[str]:
    roles_list = []
    user_result = await db.execute(select(User.is_superuser).where(User.id == user_id))
    is_superuser = user_result.scalar_one_or_none()

    if is_superuser:
        roles_list.append("superuser")

    role_names_result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    roles_list.extend(role_names_result.scalars().all())

    if not is_superuser and not roles_list:
        roles_list.append("user")

    return list(set(roles_list))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer), db: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    if not credentials or not credentials.credentials:
        logger.warning("Access token истек или отсутствует в заголовках")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid access token",
        )

    token = credentials.credentials
    try:
        payload = await decode_jwt(token)

        user_id_str = payload.get("sub")
        if not user_id_str:
            logger.warning("Неверный токен: отсутствует ID пользователя")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            logger.warning(
                "Неверный токен: некорректный формат ID пользователя",
                user_id_str=user_id_str,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: invalid user ID format",
            )

        user_obj = await db.get(User, user_id)
        if not user_obj:
            logger.warning("Пользователь не найден по ID из токена", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        permissions = await get_cached_permissions(user_id, db)
        roles = await get_user_roles(user_id, db)

        logger.debug(
            "Текущий пользователь успешно аутентифицирован",
            user_id=user_id,
            login=user_obj.login,
            permissions=permissions,
            roles=roles,
        )
        return {
            "id": str(user_id),
            "login": payload.get("login", user_obj.login),
            "mfa_verified": payload.get("mfa_verified", False),
            "is_superuser": user_obj.is_superuser,
            "permissions": permissions,
            "roles": roles,
        }

    except ExpiredSignatureError:
        logger.warning("Токен истек")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except JWTError:
        logger.warning("Неверный токен")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    except ValueError as e:
        logger.warning("Ошибка валидации токена", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponseModel(
                detail={"token": "Token is blacklisted"}
            ).model_dump(),
        )
    except Exception:
        logger.exception(
            "Произошла непредвиденная ошибка при получении текущего пользователя"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


def require_permission(permission: str):
    async def _require_permission(
        current_user: dict[str, Any] = Depends(get_current_user),
    ):
        if current_user["is_superuser"] or "*" in current_user["permissions"]:
            logger.debug(
                "Суперпользователь или имеет все разрешения",
                user_id=current_user["id"],
                required_permission=permission,
            )
            return current_user

        if permission not in current_user["permissions"]:
            logger.warning(
                "Пользователь не имеет необходимых разрешений",
                user_id=current_user["id"],
                required_permission=permission,
                user_permissions=current_user["permissions"],
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {permission}",
            )
        logger.debug(
            "Пользователь имеет необходимые разрешения",
            user_id=current_user["id"],
            required_permission=permission,
        )
        return current_user

    return _require_permission


async def rate_limit_dependency(
        request: Request,
        traffic_type: str,
        current_user: dict[str, Any] | None = Depends(get_current_user),
        rate_limiter: RedisLeakyBucketRateLimiter = Depends(get_rate_limiter)
):
    identifier = request.client.host if request.client else "unknown_ip"
    user_roles = ["guest"]

    if current_user:
        identifier = current_user["id"]
        user_roles = current_user["roles"]
        if not user_roles:
            user_roles = ["user"]

    if not current_user and "guest" not in user_roles:
        user_roles.append("guest")
    elif current_user and not user_roles:
        user_roles.append("user")

    allowed = await rate_limiter.allow_request(identifier, user_roles, traffic_type)

    if not allowed:
        logger.warning(
            "Превышен лимит запросов",
            identifier=identifier,
            traffic_type=traffic_type,
            user_roles=user_roles,
            path=request.url.path
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponseModel(
                detail={"rate_limit": "Too many requests. Please try again later."}
            ).model_dump(),
        )
    logger.debug(
        "Проверка лимита запросов пройдена",
        identifier=identifier,
        traffic_type=traffic_type,
        user_roles=user_roles
    )
