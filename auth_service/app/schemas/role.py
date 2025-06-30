from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional, Annotated
from annotated_types import MaxLen
from datetime import datetime
from uuid import UUID


class RoleBase(BaseModel):
    name: Annotated[str, MaxLen(50)]
    description: Optional[Annotated[str, MaxLen(255)]] = None
    permissions: List[Annotated[str, MaxLen(100)]]


class RoleCreate(RoleBase):
    pass


class RoleUpdate(RoleBase):
    pass


class RoleResponse(RoleBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
