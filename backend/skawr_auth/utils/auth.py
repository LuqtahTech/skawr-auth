import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings - can be overridden
DEFAULT_SECRET_KEY = "your-secret-key-here-change-in-production"
DEFAULT_ALGORITHM = "HS256"
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
        secret_key or os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY),
        algorithm or os.getenv("ALGORITHM", DEFAULT_ALGORITHM),
    )


def _access_minutes() -> int:
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES))


def _refresh_days() -> int:
    return int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS))


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


def create_get_current_user_dependency(user_model: Any, db_dependency: Any):
    """
    Factory function to create a get_current_user dependency.
    Validates that the bearer token is an access token (not refresh).
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


# Default implementation - will be overridden by consuming apps
get_current_user = None
