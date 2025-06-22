from typing import Dict, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    meta: Dict = {"status": "error"}


class SuccessResponse(BaseModel):
    data: dict
    meta: Dict = {"status": "success"}


class ErrorResponseModel(BaseModel):
    detail: dict[str, str]

    class Config:
        json_schema_extra = {
            "example": {
                "detail": {
                    "login": "User with login 'testuser' already exists."
                }
            }
        }