from typing import List
from uuid import UUID

from pydantic import BaseModel


class PermissionCheckRequest(BaseModel):
    user_id: str
    required_permission: str


class PermissionCheckResponse(BaseModel):
    has_access: bool
    missing_permissions: List[str] = []


class UserPermissionsResponse(BaseModel):
    user_id: UUID
    permissions: List[str]