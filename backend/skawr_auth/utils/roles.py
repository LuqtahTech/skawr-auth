"""
Product-scoped role dependency for FastAPI endpoints.

Provides enums for Products and Roles, a role hierarchy,
and a dependency factory that verifies JWT product enrollments.
"""

from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .auth import verify_token, TOKEN_TYPE_ACCESS


security = HTTPBearer()


class Product(str, Enum):
    """Skawr product identifiers matching product_enrollments claim values."""
    ANALYTICS = "analytics"
    SEARCH_SAAS = "search_saas"
    CLIENT_DASHBOARD = "client_dashboard"
    ADMIN_DASHBOARD = "admin_dashboard"
    MARKETPLACE = "marketplace"


class Role(str, Enum):
    """Per-product roles ordered by privilege level."""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# Higher number = more privilege
ROLE_HIERARCHY: dict[str, int] = {
    "admin": 3,
    "member": 2,
    "viewer": 1,
}


def role_meets_minimum(user_role: str, min_role: Role) -> bool:
    """Check if user_role meets or exceeds the minimum required role.

    Args:
        user_role: The user's actual role string (e.g. "admin", "member", "viewer").
        min_role: The minimum Role required.

    Returns:
        True if user_role is at or above min_role in the hierarchy.
        False if user_role is unknown or below min_role.
    """
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    min_level = ROLE_HIERARCHY.get(min_role.value, 0)
    return user_level >= min_level


def require_product_role(product: Product, min_role: Role = Role.VIEWER):
    """FastAPI dependency factory for product-scoped role authorization.

    Extracts the user's role from the JWT product_enrollments claim,
    verifies enrollment in the specified product, and checks the role
    meets or exceeds min_role in the hierarchy.

    Args:
        product: The Product the endpoint belongs to.
        min_role: Minimum role required (default: VIEWER).

    Returns:
        An async dependency function compatible with FastAPI's Depends().
        The dependency returns the user's role string for the product.

    Raises:
        HTTPException(401): If the token is missing or invalid.
        HTTPException(403): If the user lacks enrollment or insufficient role.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(role: str = Depends(require_product_role(Product.ANALYTICS, Role.ADMIN))):
            ...
    """

    async def _verify_product_role(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> str:
        # Validate token
        payload = verify_token(credentials.credentials, expected_type=TOKEN_TYPE_ACCESS)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract product_enrollments from claims
        enrollments = payload.get("product_enrollments")

        # Backward compat: tokens without product_enrollments are treated
        # as enrolled everywhere with member role (90-day window per Req 13.3/13.4)
        if enrollments is None:
            user_role = "member"
            if not role_meets_minimum(user_role, min_role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient role for this product",
                )
            return user_role

        # Find enrollment for the requested product
        user_role: Optional[str] = None
        for enrollment in enrollments:
            if enrollment.get("product") == product.value:
                user_role = enrollment.get("role")
                break

        if user_role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enrolled in this product",
            )

        # Check role hierarchy
        if not role_meets_minimum(user_role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this product",
            )

        return user_role

    return _verify_product_role
