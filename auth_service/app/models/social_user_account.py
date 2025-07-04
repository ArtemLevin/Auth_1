from __future__ import annotations

from uuid import UUID as PyUUID, uuid4

from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserSocialAccount(Base):
    __tablename__ = "user_social_accounts"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[PyUUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(100), nullable=False)

    user: Mapped["User"] = relationship(back_populates="social_accounts")
