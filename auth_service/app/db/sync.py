from app.settings import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SyncEngine = create_engine(
    settings.sync_database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=SyncEngine,
    autoflush=False,
    expire_on_commit=False,
)
