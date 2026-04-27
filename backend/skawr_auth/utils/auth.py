import os
from datetime import datetime, timedelta
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
DEFAULT_ACCESS_TOKEN_EXPIRE_HOURS = 24

# Security scheme
security = HTTPBearer()


def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=DEFAULT_ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode.update({"exp": expire})

    key = secret_key or os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
    alg = algorithm or os.getenv("ALGORITHM", DEFAULT_ALGORITHM)

    return jwt.encode(to_encode, key, algorithm=alg)


def verify_token(
    token: str,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None
) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        key = secret_key or os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
        alg = algorithm or os.getenv("ALGORITHM", DEFAULT_ALGORITHM)

        payload = jwt.decode(token, key, algorithms=[alg])
        return payload
    except JWTError:
        return None


def create_get_current_user_dependency(user_model: Any, db_dependency: Any):
    """
    Factory function to create a get_current_user dependency.
    This allows the auth library to work with different database setups.

    Args:
        user_model: The User model class from the consuming application
        db_dependency: The database dependency function (e.g., get_db)

    Returns:
        A dependency function that can be used with FastAPI
    """

    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(db_dependency)
    ) -> Any:
        """Get the current authenticated user from JWT token."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = verify_token(credentials.credentials)
            if payload is None:
                raise credentials_exception

            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception

        except JWTError:
            raise credentials_exception

        # Query user from database
        result = await db.execute(select(user_model).where(user_model.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        return user

    return get_current_user


# Default implementation - will be overridden by consuming apps
get_current_user = None