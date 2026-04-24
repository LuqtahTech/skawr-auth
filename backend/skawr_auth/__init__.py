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
    PasswordResetRequest, PasswordResetConfirm
)
from .schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    APIKeyCreate, APIKeyUpdate, APIKeyResponse, APIKeyCreateResponse
)
from .endpoints.auth import create_auth_router
from .endpoints.projects import create_projects_router
from .middleware.api_key_auth import require_api_key, require_api_key_with_permission
from .utils.auth import get_password_hash, verify_password, create_access_token, get_current_user
from .utils.database import create_auth_tables

__all__ = [
    # Models
    "User", "UserSession", "Project", "APIKey",
    # Schemas
    "UserSignupRequest", "UserLoginRequest", "UserResponse", "AuthResponse",
    "PasswordResetRequest", "PasswordResetConfirm",
    "ProjectCreate", "ProjectUpdate", "ProjectResponse",
    "APIKeyCreate", "APIKeyUpdate", "APIKeyResponse", "APIKeyCreateResponse",
    # Routers
    "create_auth_router", "create_projects_router",
    # Middleware
    "require_api_key", "require_api_key_with_permission",
    # Utils
    "get_password_hash", "verify_password", "create_access_token", "get_current_user",
    "create_auth_tables"
]