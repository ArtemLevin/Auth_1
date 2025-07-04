from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uuid import UUID as PyUUID
from uuid import uuid4


from app.models.base import Base
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(Base):
    __tablename__ = "users"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), unique=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    roles: Mapped[List["UserRole"]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    history: Mapped[List["LoginHistory"]] = relationship(

        "LoginHistory", back_populates="user", cascade="all, delete-orphan"
    )
    social_accounts: Mapped[list["UserSocialAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

        "LoginHistory", back_populates="user", cascade="all, delete-orphan")

    yandex_id: Mapped[str | None] = mapped_column(String(255), unique=True,
                                                  nullable=True)
    vk_id: Mapped[str | None] = mapped_column(String(255), unique=True,
                                              nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True,
                                                  nullable=True)

