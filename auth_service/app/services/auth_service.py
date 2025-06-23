import datetime
from uuid import UUID

import structlog
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, or_

from app.core.security import (create_access_token,
                                            create_refresh_token,
                                            get_password_hash, verify_password,
                                            add_to_blacklist, decode_jwt, is_token_blacklisted)
from app.models import User, LoginHistory
from app.settings import settings

from app.utils.cache import redis_client

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def login(self, login: str, password: str, ip_address: str | None = None, user_agent: str | None = None) -> dict | None:
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

        refresh_payload = await decode_jwt(refresh_token, refresh=True)
        refresh_jti = refresh_payload["jti"]
        await redis_client.sadd(f"user_active_refresh_jtis:{user.id}", refresh_jti)
        await redis_client.expire(f"user_active_refresh_jtis:{user.id}", settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600) # В секундах

        login_history_entry = LoginHistory(
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db_session.add(login_history_entry)
        await self.db_session.commit()
        await self.db_session.refresh(login_history_entry)

        logger.info(
            "Пользователь успешно вошел в систему", user_id=user.id, login=user.login
        )
        return {"access_token": access_token, "refresh_token": refresh_token}

    async def register(
        self, login: str, password: str, email: str | None = None
    ) -> tuple[bool, dict[str, str]]:
        success = True
        errors: dict[str, str] = {}

        query_conditions = [User.login == login]
        if email:
            query_conditions.append(User.email == email)

        existing_user_query = await self.db_session.execute(
            select(User).where(or_(*query_conditions))
        )
        existing_user = existing_user_query.scalars().first()

        if existing_user:
            if existing_user.login == login:
                success = False
                logger.warning(
                    "Попытка регистрации с уже существующим логином", login=login
                )
                errors["login"] = f"User with login '{login}' already exists."
            if email and existing_user.email == email:
                success = False
                logger.warning(
                    "Попытка регистрации с уже существующим адресом электронной почты",
                    email=email,
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

    async def get_login_history(self, user_id: UUID) -> list[LoginHistory]:
        result = await self.db_session.execute(
            select(LoginHistory)
            .where(LoginHistory.user_id == user_id)
            .order_by(desc(LoginHistory.login_at))
        )
        history = result.scalars().all()
        logger.info("Запрошена история входов пользователя", user_id=user_id, count=len(history))
        return list(history)

    async def logout(self, refresh_token: str) -> None:
        token = await decode_jwt(refresh_token, refresh=True)
        jti = token["jti"]
        user_id = UUID(token["sub"])

        token_expire_date = datetime.datetime.fromtimestamp(token["exp"], tz=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        ttl = int((token_expire_date - now).total_seconds())
        if ttl < 0:
            ttl = 1

        await add_to_blacklist(jti, ttl)
        await redis_client.srem(f"user_active_refresh_jtis:{user_id}", jti)
        logger.info("Пользователь вышел из системы", jti=jti, user_id=user_id)

    async def refresh_tokens(self, refresh_token: str) -> dict | None:
        try:
            payload = await decode_jwt(refresh_token, refresh=True)
            user_id = UUID(payload["sub"])
            jti = payload["jti"]

            if await is_token_blacklisted(jti):
                logger.warning("Попытка использовать refresh токен из черного списка", jti=jti)
                raise ValueError("Refresh token is blacklisted")

            if not await redis_client.sismember(f"user_active_refresh_jtis:{user_id}", jti):
                logger.warning("Неактивный refresh токен", user_id=user_id, jti=jti)
                raise ValueError("Refresh token is not active")

            new_access_token = create_access_token(subject=user_id, payload={"login": payload.get("login")})
            new_refresh_token = create_refresh_token(subject=user_id)

            token_expire_date = datetime.datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)
            now = datetime.datetime.now(datetime.timezone.utc)
            ttl = int((token_expire_date - now).total_seconds())
            if ttl < 0: ttl = 1
            await add_to_blacklist(jti, ttl)

            await redis_client.srem(f"user_active_refresh_jtis:{user_id}", jti)
            new_refresh_payload = await decode_jwt(new_refresh_token, refresh=True)
            await redis_client.sadd(f"user_active_refresh_jtis:{user_id}", new_refresh_payload["jti"])
            await redis_client.expire(f"user_active_refresh_jtis:{user_id}", settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)

            logger.info("Токены успешно обновлены", user_id=user_id)
            return {"access_token": new_access_token, "refresh_token": new_refresh_token}

        except (ExpiredSignatureError, JWTError, ValueError) as e:
            logger.warning("Ошибка при обновлении токенов", error=str(e))
            return None

    async def logout_all_other_sessions(
        self, user_id: UUID, current_refresh_token: str
    ):
        current_payload = await decode_jwt(current_refresh_token, refresh=True)
        current_jti = current_payload["jti"]

        active_jtis = await redis_client.smembers(f"user_active_refresh_jtis:{user_id}")

        for jti_to_blacklist in active_jtis:
            if jti_to_blacklist != current_jti:
                await add_to_blacklist(jti_to_blacklist, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)
                logger.info("Токен добавлен в черный список (logout_all_other_sessions)", user_id=user_id, jti=jti_to_blacklist)

        await redis_client.delete(f"user_active_refresh_jtis:{user_id}")
        await redis_client.sadd(f"user_active_refresh_jtis:{user_id}", current_jti)
        await redis_client.expire(f"user_active_refresh_jtis:{user_id}", settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)

        logger.info(
            "Все остальные сессии пользователя завершены",
            user_id=user_id,
            current_jti=current_jti,
        )