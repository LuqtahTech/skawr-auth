from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator

from ..utils.auth import validate_password_strength


class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        error = validate_password_strength(v)
        if error:
            raise ValueError(error)
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    email_verified: bool
    created_at: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
