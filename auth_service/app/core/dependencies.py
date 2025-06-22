from typing import Any
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, Request, status
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from auth_service.app.core.security import decode_jwt
from auth_service.app.db.session import db_helper
from auth_service.app.models import Role, User, UserRole
from auth_service.app.schemas.error import ErrorResponseModel
from auth_service.app.utils.cache import redis_client

logger = structlog.get_logger(__name__)


def get_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Отсутствует или неверный токен авторизации")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_header[7:]


async def get_cached_permissions(user_id: UUID, db: AsyncSession) -> list[str]:
    user_id_str = str(user_id)
    permissions_str = await redis_client.get(f"permissions:{user_id_str}")
    if permissions_str:
        logger.debug("Разрешения получены из кэша Redis", user_id=user_id_str)
        return permissions_str.split(",")

    result = await db.execute(
        select(Role.permissions)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    all_permissions = set()
    for row in result.scalars().all():
        all_permissions.update(row)

    user_result = await db.execute(select(User.is_superuser).where(User.id == user_id))
    is_superuser = user_result.scalar_one_or_none()
    if is_superuser:
        all_permissions.update(
            ["manage_roles", "view_content", "manage_users", "admin_panel"]
        )
        logger.info(
            "Пользователь является суперпользователем, добавлены все разрешения",
            user_id=user_id_str,
        )

    permissions_list = list(all_permissions)
    if permissions_list:
        await redis_client.setex(
            f"permissions:{user_id_str}", 3600, ",".join(permissions_list)
        )
        logger.debug("Разрешения кэшированы в Redis", user_id=user_id_str)
    else:
        logger.info(
            "Для пользователя не найдено разрешений, по умолчанию 'view_content'",
            user_id=user_id_str,
        )
        permissions_list = ["view_content"]

    return permissions_list


async def get_current_user(
    token: str = Depends(get_token), db: AsyncSession = Depends(db_helper.get_db_session)
) -> dict[str, Any]:
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
        if user_obj.is_superuser:
            permissions = ["*"]

        logger.debug(
            "Текущий пользователь успешно аутентифицирован",
            user_id=user_id,
            login=user_obj.login,
            permissions=permissions,
        )
        return {
            "id": str(user_id),
            "login": payload.get("login", user_obj.login),
            "mfa_verified": payload.get("mfa_verified", False),
            "is_superuser": user_obj.is_superuser,
            "permissions": permissions,
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
            detail=ErrorResponseModel(detail={"token": "Token is blacklisted"}).model_dump(),
        )
    except Exception as e:
        logger.exception(
            "Произошла непредвиденная ошибка при получении текущего пользователя"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


def require_permission(permission: str) -> dict[str, Any]:
    def _require_permission(
        current_user: dict[str, Any] = Depends(get_current_user)
    ) -> dict[str, Any]:
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
