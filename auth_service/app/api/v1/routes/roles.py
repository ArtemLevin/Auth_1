import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from auth_service.app.core.dependencies import (get_current_user,
                                                require_permission, http_bearer)
from auth_service.app.db.session import db_helper
from auth_service.app.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from auth_service.app.services.role_service import RoleService
from auth_service.app.models.user import User
from auth_service.app.schemas.permission import UserPermissionsResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/roles", tags=["Roles"], dependencies=[Depends(http_bearer)])


async def get_role_service(db: AsyncSession = Depends(db_helper.get_db_session)) -> RoleService:
    return RoleService(db)


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    role_service: RoleService = Depends(get_role_service),
    user: dict = Depends(require_permission("manage_roles")),
):
    try:
        role = await role_service.create_role(role_data)
        logger.info("Роль успешно создана", role_name=role.name, role_id=role.id)
        return role
    except ValueError as e:
        logger.error(
            "Ошибка при создании роли", detail=str(e), role_name=role_data.name
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/", response_model=list[RoleResponse])
async def get_all_roles(
    role_service: RoleService = Depends(get_role_service),
    user: dict = Depends(get_current_user),
):
    roles = await role_service.get_all_roles()
    logger.info("Получен список всех ролей", count=len(roles))
    return roles


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role_by_id(
    role_id: UUID,
    role_service: RoleService = Depends(get_role_service),
    user: dict = Depends(get_current_user),
):
    role = await role_service.get_role_by_id(role_id)
    if not role:
        logger.warning("Роль не найдена", role_id=role_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    logger.info("Роль успешно получена", role_id=role_id)
    return role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_update: RoleUpdate,
    role_service: RoleService = Depends(get_role_service),
    user: dict = Depends(require_permission("manage_roles")),
):
    role = await role_service.update_role(role_id, role_update)
    if not role:
        logger.warning("Роль не найдена для обновления", role_id=role_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    logger.info("Роль успешно обновлена", role_id=role_id)
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    role_service: RoleService = Depends(get_role_service),
    user: dict = Depends(require_permission("manage_roles")),
):
    deleted = await role_service.delete_role(role_id)
    if not deleted:
        logger.warning("Роль не найдена для удаления", role_id=role_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    logger.info("Роль успешно удалена", role_id=role_id)
    return {"message": "Role deleted successfully"}


@router.post("/{role_id}/assign/{user_id}", status_code=status.HTTP_200_OK)
async def assign_role_to_user(
    role_id: UUID,
    user_id: UUID,
    role_service: RoleService = Depends(get_role_service),
    user: dict = Depends(require_permission("manage_roles")),
):
    assigned = await role_service.assign_role_to_user(user_id, role_id)
    if not assigned:
        logger.warning(
            "Не удалось назначить роль пользователю", user_id=user_id, role_id=role_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User or Role not found, or role already assigned",
        )
    logger.info("Роль успешно назначена пользователю", user_id=user_id, role_id=role_id)
    return {"message": "Role assigned successfully"}


@router.delete("/{role_id}/revoke/{user_id}", status_code=status.HTTP_200_OK)
async def revoke_role_from_user(
    role_id: UUID,
    user_id: UUID,
    role_service: RoleService = Depends(get_role_service),
    user: dict = Depends(require_permission("manage_roles")),
):
    revoked = await role_service.revoke_role_from_user(user_id, role_id)
    if not revoked:
        logger.warning(
            "Не удалось отозвать роль у пользователя", user_id=user_id, role_id=role_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User-Role assignment not found",
        )
    logger.info(
        "Роль успешно отозвана у пользователя", user_id=user_id, role_id=role_id
    )
    return {"message": "Role revoked successfully"}


@router.get("/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions_endpoint(
    user_id: UUID,
    role_service: RoleService = Depends(get_role_service),
    db: AsyncSession = Depends(db_helper.get_db_session),
    current_user: dict = Depends(require_permission("manage_roles")),
):
    user_obj = await db.get(User, user_id)
    if not user_obj:
        logger.warning(
            "Пользователь не найден для получения разрешений", user_id=user_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    permissions = await role_service.get_user_permissions(user_id)
    logger.info(
        "Получены разрешения для пользователя", user_id=user_id, permissions=permissions
    )
    return UserPermissionsResponse(user_id=user_id, permissions=permissions)
