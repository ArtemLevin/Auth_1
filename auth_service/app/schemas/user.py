from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Annotated
from annotated_types import MaxLen, MinLen
from uuid import UUID


class UserBase(BaseModel):
    login: Annotated[str, MaxLen(50)]
    email: Annotated[str, MaxLen(100)] | None = None


class UserCreate(UserBase):
    password: Annotated[str, MinLen(6)]


class UpdateProfileRequest(BaseModel):
    login: Annotated[str, MaxLen(50)] | None = None
    password: Annotated[str, MinLen(6)] | None = None
    email: Annotated[str, MaxLen(100)] | None= None


class UserResponse(UserBase):
    id: UUID
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
