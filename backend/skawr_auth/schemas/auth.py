from typing import Optional
from pydantic import BaseModel, EmailStr

class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    email_verified: bool
    created_at: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str