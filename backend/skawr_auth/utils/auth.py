import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select

from skawr_auth.utils.config import (
    _get_secret_key,
    _get_algorithm,
    DEFAULT_SECRET_KEY,
    DEFAULT_ALGORITHM,
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Kept as module-level constants for backward compat (consumers may reference them)
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 30

# Token types embedded in JWTs to prevent confusion
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# Password policy
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 72  # bcrypt hard limit

# Security scheme
security = HTTPBearer()


def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> Optional[str]:
    """Return an error message if password is too weak, otherwise None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if len(password.encode("utf-8")) > MAX_PASSWORD_LENGTH:
        return f"Password must be at most {MAX_PASSWORD_LENGTH} bytes"
    if not re.search(r"[A-Za-z]", password):
        return "Password must contain at least one letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one number"
    return None


def _get_key_alg(secret_key: Optional[str], algorithm: Optional[str]):
    return (
        _get_secret_key(secret_key),
        _get_algorithm(algorithm),
    )


def _access_minutes() -> int:
    return int(
        os.getenv("SKAWR_AUTH_ACCESS_EXPIRE_MINUTES")
        or os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
        or str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def _refresh_days() -> int:
    return int(
        os.getenv("SKAWR_AUTH_REFRESH_EXPIRE_DAYS")
        or os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")
        or str(DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS)
    )


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
) -> str:
    """Create a short-lived JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=_access_minutes()))
    to_encode.update({"exp": expire, "type": TOKEN_TYPE_ACCESS})
    key, alg = _get_key_alg(secret_key, algorithm)
    return jwt.encode(to_encode, key, algorithm=alg)


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
) -> str:
    """Create a long-lived JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=_refresh_days()))
    to_encode.update({"exp": expire, "type": TOKEN_TYPE_REFRESH})
    key, alg = _get_key_alg(secret_key, algorithm)
    return jwt.encode(to_encode, key, algorithm=alg)


def verify_token(
    token: str,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
    expected_type: Optional[str] = None,
) -> Optional[dict]:
    """Verify and decode a JWT token. Returns payload or None on failure."""
    try:
        key, alg = _get_key_alg(secret_key, algorithm)
        payload = jwt.decode(token, key, algorithms=[alg])
        if expected_type and payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None


def create_get_current_user_dependency_async(
    user_model: Any,
    db_dependency: Any,
    product: Optional[str] = None,
):
    """
    Factory function to create an ASYNC get_current_user dependency.
    Uses AsyncSession (for analytics and other async services).

    Validates that the bearer token is an access token (not refresh).
    If `product` is specified, also validates product enrollment from the
    token's `product_enrollments` claim. For backward compat: if the token
    has no `product_enrollments`, the user is treated as enrolled everywhere
    with "member" role.

    Args:
        user_model: The SQLAlchemy User model class.
        db_dependency: A FastAPI dependency that yields an AsyncSession.
        product: Optional product identifier to check enrollment for.
                 If None, no enrollment check is performed (original behavior).
    """

    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(db_dependency),
    ) -> Any:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        payload = verify_token(credentials.credentials, expected_type=TOKEN_TYPE_ACCESS)
        if payload is None:
            raise credentials_exception

        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Validate product enrollment if product is specified
        if product is not None:
            enrollments = payload.get("product_enrollments")
            if enrollments is None:
                # Backward compat: no product_enrollments claim means
                # enrolled everywhere with "member" role (90-day window)
                pass
            else:
                # Check if user is enrolled in the specified product
                enrolled = any(
                    e.get("product") == product for e in enrollments
                )
                if not enrolled:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Not enrolled in product: {product}",
                    )

        result = await db.execute(select(user_model).where(user_model.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )

        return user

    return get_current_user


def create_get_current_user_dependency_sync(
    user_model: Any,
    db_dependency: Any,
    product: Optional[str] = None,
):
    """
    Factory function to create a SYNC get_current_user dependency.
    Uses Session (sync SQLAlchemy) for the indexer and other sync services.

    Validates that the bearer token is an access token (not refresh).
    If `product` is specified, also validates product enrollment from the
    token's `product_enrollments` claim. For backward compat: if the token
    has no `product_enrollments`, the user is treated as enrolled everywhere
    with "member" role.

    Args:
        user_model: The SQLAlchemy User model class.
        db_dependency: A FastAPI dependency that yields a sync Session.
        product: Optional product identifier to check enrollment for.
                 If None, no enrollment check is performed (original behavior).
    """

    def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(db_dependency),
    ) -> Any:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        payload = verify_token(credentials.credentials, expected_type=TOKEN_TYPE_ACCESS)
        if payload is None:
            raise credentials_exception

        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Validate product enrollment if product is specified
        if product is not None:
            enrollments = payload.get("product_enrollments")
            if enrollments is None:
                # Backward compat: no product_enrollments claim means
                # enrolled everywhere with "member" role (90-day window)
                pass
            else:
                # Check if user is enrolled in the specified product
                enrolled = any(
                    e.get("product") == product for e in enrollments
                )
                if not enrolled:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Not enrolled in product: {product}",
                    )

        result = db.execute(select(user_model).where(user_model.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user",
            )

        return user

    return get_current_user


# Backward-compatible alias: the original name maps to the async variant
create_get_current_user_dependency = create_get_current_user_dependency_async


def detect_token_format(payload: dict) -> str:
    """
    Classify a decoded JWT payload into one of three formats.

    This function operates on an ALREADY-DECODED payload dict (not a raw JWT string).
    It does NOT validate signatures — it only classifies the structure.

    Args:
        payload: A decoded JWT payload dictionary.

    Returns:
        "unified" — has product_enrollments claim (new format)
        "legacy_indexer" — has client_id claim, no product_enrollments
        "legacy_analytics" — has sub only, no product_enrollments, no client_id

    Raises:
        ValueError: If the token structure is unrecognizable (none of the above).
    """
    if "product_enrollments" in payload:
        return "unified"
    if "client_id" in payload:
        return "legacy_indexer"
    if "sub" in payload:
        return "legacy_analytics"
    raise ValueError("Unrecognizable token format")


def verify_token_for_product(
    token: str,
    product: str,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
) -> Optional[str]:
    """
    Verify a token and return the user's role for the specified product.

    This function operates purely on JWT claims — it does NOT query the database.

    Steps:
        1. Decode and verify the token (signature + expiration) using verify_token().
        2. If decode fails → return None.
        3. Classify the token format using detect_token_format().
        4. If legacy format and past SKAWR_AUTH_LEGACY_TOKEN_DEADLINE → return None.
        5. Based on format:
           - "unified": Look up product in product_enrollments. Return role if found, None otherwise.
           - "legacy_analytics": Return "member" (backward compat — enrolled everywhere for 90 days).
           - "legacy_indexer": Return "admin" (legacy indexer clients were always admins).
        6. If detect_token_format raises ValueError → return None.

    Args:
        token: The raw JWT string.
        product: The product identifier to check enrollment for (e.g., "analytics", "search_saas").
        secret_key: Optional override for the signing secret key.
        algorithm: Optional override for the signing algorithm.

    Returns:
        The user's role string (e.g., "admin", "member", "viewer") if the token is valid
        and the user has access to the product, or None if validation fails or the user
        lacks enrollment.
    """
    # Step 1 & 2: Decode and verify the token
    payload = verify_token(token, secret_key=secret_key, algorithm=algorithm)
    if payload is None:
        return None

    # Step 3: Classify the token format
    try:
        token_format = detect_token_format(payload)
    except ValueError:
        # Step 6: Unrecognizable format
        return None

    # Step 4: Check legacy token deadline for legacy formats
    if token_format in ("legacy_analytics", "legacy_indexer"):
        deadline_str = os.getenv("SKAWR_AUTH_LEGACY_TOKEN_DEADLINE")
        if deadline_str:
            try:
                deadline = date.fromisoformat(deadline_str)
                if deadline < date.today():
                    return None
            except ValueError:
                # Invalid date format in env var — don't reject, just skip the check
                pass

    # Step 5: Resolve role based on format
    if token_format == "unified":
        enrollments = payload.get("product_enrollments", [])
        for enrollment in enrollments:
            if isinstance(enrollment, dict) and enrollment.get("product") == product:
                return enrollment.get("role")
        # User has no enrollment for this product
        return None

    if token_format == "legacy_analytics":
        # Backward compat: treat as enrolled everywhere with member role
        return "member"

    if token_format == "legacy_indexer":
        # Legacy indexer clients were always admins of their own resources
        return "admin"

    # Should not reach here, but be safe
    return None


# Default implementation - will be overridden by consuming apps
get_current_user = None
