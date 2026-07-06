"""
Skawr Authentication & API Key Management Library

Shared authentication components for all Skawr projects.
Provides user authentication, project management, and API key system.
"""

__version__ = "0.1.0"

# Export main components for easy importing
from .models.user import User, UserSession
from .models.project import Project, APIKey
from .models.connected_store import ConnectedStore, create_connected_store_models
from .schemas.auth import (
    UserSignupRequest, UserLoginRequest, UserResponse, AuthResponse,
    RefreshTokenRequest, TokenPair,
    PasswordResetRequest, PasswordResetConfirm
)
from .schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    APIKeyCreate, APIKeyUpdate, APIKeyResponse, APIKeyCreateResponse
)
from .schemas.subscription import (
    SubscriptionTierUpdate, SubscriptionTierResponse, ALLOWED_TIERS,
)
from .endpoints.auth import create_auth_router, limiter as auth_limiter
from .endpoints.projects import create_projects_router
from .endpoints.subscription import create_subscription_router
from .middleware.api_key_auth import create_api_key_dependencies
from .utils.auth import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token, verify_token,
    validate_password_strength, get_current_user,
    detect_token_format, verify_token_for_product,
    create_get_current_user_dependency,
    create_get_current_user_dependency_async,
    create_get_current_user_dependency_sync,
    TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH,
)
from .utils.config import (
    _get_secret_key, _get_algorithm, get_auth_config, AuthConfig,
)
from .utils.roles import (
    Product, Role, ROLE_HIERARCHY,
    require_product_role, role_meets_minimum,
)

__all__ = [
    # Models
    "User", "UserSession", "Project", "APIKey",
    "ConnectedStore", "create_connected_store_models",
    # Schemas
    "UserSignupRequest", "UserLoginRequest", "UserResponse", "AuthResponse",
    "RefreshTokenRequest", "TokenPair",
    "PasswordResetRequest", "PasswordResetConfirm",
    "ProjectCreate", "ProjectUpdate", "ProjectResponse",
    "APIKeyCreate", "APIKeyUpdate", "APIKeyResponse", "APIKeyCreateResponse",
    "SubscriptionTierUpdate", "SubscriptionTierResponse", "ALLOWED_TIERS",
    # Routers
    "create_auth_router", "create_projects_router", "create_subscription_router",
    "auth_limiter",
    # Middleware
    "create_api_key_dependencies",
    # Utils
    "get_password_hash", "verify_password",
    "create_access_token", "create_refresh_token", "verify_token",
    "validate_password_strength", "get_current_user",
    "detect_token_format", "verify_token_for_product",
    "create_get_current_user_dependency",
    "create_get_current_user_dependency_async",
    "create_get_current_user_dependency_sync",
    "TOKEN_TYPE_ACCESS", "TOKEN_TYPE_REFRESH",
    # Config
    "_get_secret_key", "_get_algorithm", "get_auth_config", "AuthConfig",
    # Roles
    "Product", "Role", "ROLE_HIERARCHY",
    "require_product_role", "role_meets_minimum",
]