from sqlalchemy.orm import DeclarativeBase

from app.db.session import engine

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    pass

