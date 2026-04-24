from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    domain: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    domain: Optional[str]
    is_active: bool
    settings: Dict[str, Any]
    created_at: str
    updated_at: str
    api_keys_count: Optional[int] = None

    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    name: str
    permissions: Optional[List[str]] = ["track", "query"]
    rate_limit: Optional[int] = 1000
    expires_at: Optional[datetime] = None


class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[List[str]] = None
    rate_limit: Optional[int] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    id: str
    project_id: str
    name: str
    key_prefix: str
    permissions: List[str]
    rate_limit: int
    is_active: bool
    last_used_at: Optional[str]
    expires_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """Response when creating new API key - includes the full key one time only"""
    id: str
    project_id: str
    name: str
    key: str  # Full API key - only shown once
    key_prefix: str
    permissions: List[str]
    rate_limit: int
    expires_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True