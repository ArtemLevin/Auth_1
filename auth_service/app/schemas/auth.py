from datetime import datetime
from typing import Annotated, Optional

from annotated_types import MaxLen, MinLen
from pydantic import BaseModel, EmailStr


class TokenData(BaseModel):
    user_id: str
    exp: Optional[datetime] = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class RefreshToken(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    login: Annotated[str, MinLen(3), MaxLen(50)]
    password: Annotated[str, MinLen(6)]


class RegisterRequest(BaseModel):
    login: Annotated[str, MinLen(3), MaxLen(50)]
    password: Annotated[str, MinLen(6)]
    email: Optional[Annotated[EmailStr, MaxLen(100)]] = None


class MessageResponse(BaseModel):
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Logged out"
            }
        }
