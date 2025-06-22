from collections.abc import AsyncGenerator

from pydantic import PostgresDsn
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from auth_service.app.settings import settings


class PostgreHelper:
    def __init__(
        self,
        url: str,
        echo: bool = True,
        future: bool = True,
        echo_pool: bool = False,
        pool_size: int = 5,  # максимум 5 постоянных подключений
        max_overflow: int = 10  # + до 10 временных подключений при пиковых нагрузках
    ) -> None:

        self.engine: AsyncEngine = create_async_engine(
            url,
            echo=echo,
            future=future,
            echo_pool=echo_pool,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )

        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False
        )

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            yield session


DATABASE_URL = PostgresDsn.build(
    scheme="postgresql+asyncpg",
    username=settings.POSTGRES_USER.get_secret_value(),
    password=settings.POSTGRES_PASSWORD.get_secret_value(),
    host="localhost",  # settings.POSTGRES_HOST.get_secret_value(), # костыль, тут нужно будет подумать
    port=settings.POSTGRES_PORT,
    path=settings.POSTGRES_DB.get_secret_value(),
)

# нужно вынести в settings
db_helper = PostgreHelper(url=str(DATABASE_URL), echo=True, echo_pool=False, pool_size=10, max_overflow=10)
