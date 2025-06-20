from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from auth_service.app.models.base import Base


class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    login_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(50))
    user_agent = Column(String(255))

    user = relationship("User", back_populates="history")
