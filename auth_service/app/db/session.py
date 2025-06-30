from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from app.settings import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)

AsyncDBSession = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

    async def dispose(self) -> None:
        await self.engine.dispose()

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncDBSession() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
