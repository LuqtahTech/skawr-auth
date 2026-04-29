"""
Skawr Authentication & API Key Management Library

Shared authentication components for all Skawr projects.
Provides user authentication, project management, and API key system.
"""

__version__ = "0.1.0"

# Export main components for easy importing
from .models.user import User, UserSession
from .models.project import Project, APIKey
from .schemas.auth import (
    UserSignupRequest, UserLoginRequest, UserResponse, AuthResponse,
    RefreshTokenRequest, TokenPair,
    PasswordResetRequest, PasswordResetConfirm
)
from .schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    APIKeyCreate, APIKeyUpdate, APIKeyResponse, APIKeyCreateResponse
)
from .endpoints.auth import create_auth_router, limiter as auth_limiter
from .endpoints.projects import create_projects_router
from .middleware.api_key_auth import create_api_key_dependencies
from .utils.auth import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token, verify_token,
    validate_password_strength, get_current_user,
    TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH,
)

__all__ = [
    # Models
    "User", "UserSession", "Project", "APIKey",
    # Schemas
    "UserSignupRequest", "UserLoginRequest", "UserResponse", "AuthResponse",
    "RefreshTokenRequest", "TokenPair",
    "PasswordResetRequest", "PasswordResetConfirm",
    "ProjectCreate", "ProjectUpdate", "ProjectResponse",
    "APIKeyCreate", "APIKeyUpdate", "APIKeyResponse", "APIKeyCreateResponse",
    # Routers
    "create_auth_router", "create_projects_router", "auth_limiter",
    # Middleware
    "create_api_key_dependencies",
    # Utils
    "get_password_hash", "verify_password",
    "create_access_token", "create_refresh_token", "verify_token",
    "validate_password_strength", "get_current_user",
    "TOKEN_TYPE_ACCESS", "TOKEN_TYPE_REFRESH",
]