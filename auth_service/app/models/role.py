from __future__ import annotations

from datetime import datetime
from uuid import UUID as PyUUID
from uuid import uuid4

from app.models.base import Base
from sqlalchemy import ARRAY, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    permissions: Mapped[list[str]] = mapped_column(
        ARRAY(String(255)), nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    users: Mapped[list["UserRole"]] = relationship(
        "UserRole", 
        back_populates="role", 
        cascade="all, delete-orphan", 
        passive_deletes=True
    )
