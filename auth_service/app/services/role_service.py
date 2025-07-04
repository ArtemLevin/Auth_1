from typing import List
from uuid import UUID

import structlog
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.role import RoleCreate, RoleUpdate
from app.utils.cache import redis_client

logger = structlog.get_logger(__name__)


class RoleService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_role(self, role_data: RoleCreate) -> Role:
        existing_role = await self.db_session.execute(
            select(Role).where(Role.name == role_data.name)
        )
        if existing_role.scalar_one_or_none():
            logger.warning(
                "Попытка создать роль с уже существующим именем",
                role_name=role_data.name,
            )
            raise ValueError(f"Role with name '{role_data.name}' already exists.")

        role = Role(**role_data.model_dump())
        self.db_session.add(role)
        await self.db_session.commit()
        await self.db_session.refresh(role)
        logger.info("Роль успешно создана", role_id=role.id, role_name=role.name)
        return role

    async def get_all_roles(self) -> list[Role]:
        result = await self.db_session.execute(select(Role))
        roles = result.scalars().all()
        logger.debug("Получен список всех ролей", count=len(roles))
        return list(roles)

    async def get_role_by_id(self, role_id: UUID) -> Role | None:
        role = await self.db_session.get(Role, role_id)
        if role:
            logger.debug("Роль найдена по ID", role_id=role_id)
        else:
            logger.debug("Роль не найдена по ID", role_id=role_id)
        return role

    async def update_role(self, role_id: UUID, role_update: RoleUpdate) -> Role | None:
        role = await self.db_session.get(Role, role_id)
        if not role:
            logger.warning("Роль не найдена для обновления", role_id=role_id)
            return None

        update_data = role_update.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != role.name:
            existing_role = await self.db_session.execute(
                select(Role).where(Role.name == update_data["name"])
            )
            if existing_role.scalar_one_or_none():
                logger.warning(
                    "Попытка обновить роль на уже существующее имя",
                    role_id=role_id,
                    new_name=update_data["name"],
                )
                raise ValueError(
                    f"Role with name '{update_data['name']}' already exists."
                )

        for field, value in update_data.items():
            setattr(role, field, value)

        await self.db_session.commit()
        await self.db_session.refresh(role)
        logger.info(
            "Роль успешно обновлена", role_id=role.id, updated_fields=update_data.keys()
        )
        return role

    async def delete_role(self, role_id: UUID) -> bool:
        result = await self.db_session.execute(delete(Role).where(Role.id == role_id))
        await self.db_session.commit()
        if result.rowcount > 0:
            logger.info("Роль успешно удалена", role_id=role_id)
            return True
        else:
            logger.warning("Роль не найдена для удаления", role_id=role_id)
            return False

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> bool:
        user_exists = await self.db_session.get(User, user_id)
        role_exists = await self.db_session.get(Role, role_id)
        if not user_exists or not role_exists:
            logger.warning(
                "Пользователь или роль не найдены для назначения",
                user_id=user_id,
                role_id=role_id,
            )
            return False

        existing_assignment = await self.db_session.execute(
            select(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
        )
        if existing_assignment.scalar_one_or_none():
            logger.warning(
                "Роль уже назначена этому пользователю",
                user_id=user_id,
                role_id=role_id,
            )
            return False

        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.db_session.add(user_role)
        await self.db_session.commit()
        await redis_client.delete(f"permissions:{user_id}")
        logger.info(
            "Роль успешно назначена пользователю", user_id=user_id, role_id=role_id
        )
        return True

    async def revoke_role_from_user(self, user_id: UUID, role_id: UUID) -> bool:
        result = await self.db_session.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id
            )
        )
        await self.db_session.commit()
        if result.rowcount > 0:
            await redis_client.delete(f"permissions:{user_id}")
            logger.info(
                "Роль успешно отозвана у пользователя", user_id=user_id, role_id=role_id
            )
            return True
        else:
            logger.warning(
                "Назначение роли не найдено для отзыва",
                user_id=user_id,
                role_id=role_id,
            )
            return False

    async def get_user_permissions(self, user_id: UUID) -> List[str]:
        result = await self.db_session.execute(
            select(Role.permissions)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        all_permissions = set()
        for row in result.scalars().all():
            all_permissions.update(row)

        logger.debug(
            "Получены разрешения пользователя",
            user_id=user_id,
            permissions=list(all_permissions),
        )
        return list(all_permissions)
