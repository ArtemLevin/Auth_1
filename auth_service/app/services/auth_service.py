from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from auth_service.app.core.security import (create_access_token,
                                            create_refresh_token,
                                            get_password_hash, verify_password)
from auth_service.app.models import User

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def login(self, login: str, password: str) -> dict | None:
        result = await self.db_session.execute(select(User).where(User.login == login))
        user = result.scalars().first()
        if not user or not verify_password(password, user.password_hash):
            logger.warning(
                "Неудачная попытка входа: неверный логин или пароль", login=login
            )
            return None

        access_token = create_access_token(
            subject=user.id, payload={"login": user.login}
        )
        refresh_token = create_refresh_token(subject=user.id)

        logger.info(
            "Пользователь успешно вошел в систему", user_id=user.id, login=user.login
        )
        return {"access_token": access_token, "refresh_token": refresh_token}

    async def register(
        self, login: str, password: str, email: str | None = None
    ) -> tuple[bool, dict[str, str]]:
        success = True
        errors: dict[str, str] = {}

        existing_user = await self.db_session.execute(
            select(User).where(User.login == login)
        )

        if existing_user.scalar_one_or_none():
            success = False
            logger.warning(
                "Попытка регистрации с уже существующим логином", login=login
            )
            errors["login"] = f"User with login '{login}' already exists."

        if email:
            user_with_same_email = await self.db_session.execute(
                select(User).where(User.email == email)
            )
            if user_with_same_email.scalar_one_or_none():
                success = False
                logger.warning(
                    "Попытка регистрации с уже существующим адресом электронной почты",
                    email=email
                )
                errors["email"] = f"User with email '{email}' already exists."

        if success:
            hashed_password = get_password_hash(password)
            user = User(login=login, password_hash=hashed_password, email=email)
            self.db_session.add(user)
            await self.db_session.commit()
            await self.db_session.refresh(user)
            logger.info(
                "Новый пользователь успешно зарегистрирован",
                user_id=user.id,
                login=user.login,
            )

        return success, errors

    async def update_profile(
        self,
        user_id: UUID,
        login: str | None = None,
        password: str | None = None,
        email: str | None = None,
    ) -> User:
        user = await self.db_session.get(User, user_id)
        if not user:
            logger.warning(
                "Пользователь не найден для обновления профиля", user_id=user_id
            )
            raise ValueError("User not found")

        if login:
            if login != user.login:
                existing_user = await self.db_session.execute(
                    select(User).where(User.login == login)
                )
                if existing_user.scalar_one_or_none():
                    logger.warning(
                        "Попытка изменить логин на уже существующий",
                        user_id=user_id,
                        new_login=login,
                    )
                    raise ValueError(f"Login '{login}' is already taken.")
            user.login = login
        if password:
            user.password_hash = get_password_hash(password)
        if email:
            user.email = email

        await self.db_session.commit()
        await self.db_session.refresh(user)
        logger.info("Профиль пользователя успешно обновлен", user_id=user_id)
        return user

    async def get_login_history(self, user_id: UUID) -> list:
        # Здесь должна быть логика получения истории входов,
        # предполагается, что модель LoginHistory уже существует и связана с User.
        # Пример:
        # result = await self.db_session.execute(
        #     select(LoginHistory).where(LoginHistory.user_id == user_id).order_by(LoginHistory.login_at.desc())
        # )
        # return result.scalars().all()
        logger.info("Запрошена история входов пользователя", user_id=user_id)
        return (
            []
        )  # Заглушка, пока не реализована модель LoginHistory и ее использование

    async def logout(self, jti: str, token_ttl: int):
        # await add_to_blacklist(jti, token_ttl)
        logger.info("Пользователь вышел из системы", jti=jti)

    async def logout_all_other_sessions(
        self, user_id: UUID, current_jti: str, access_token_ttl: int
    ):
        logger.warning(
            "Функционал 'Выйти из остальных аккаунтов' требует дополнительной реализации.",
            user_id=user_id,
        )
        pass
