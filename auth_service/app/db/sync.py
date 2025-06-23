from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import settings

SyncEngine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=SyncEngine,
    autoflush=False,
    expire_on_commit=False,
)
