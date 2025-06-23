from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LoginHistoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    login_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None

    model_config = ConfigDict(from_attributes=True)
