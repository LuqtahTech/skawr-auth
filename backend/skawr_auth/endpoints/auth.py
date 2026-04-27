from typing import Any, Callable
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..schemas.auth import (
    UserSignupRequest, UserLoginRequest, UserResponse, AuthResponse,
    PasswordResetRequest, PasswordResetConfirm
)
from ..utils.auth import get_password_hash, verify_password, create_access_token


def create_auth_router(
    user_model: Any,
    db_dependency: Any,
    get_current_user_func: Callable,
    prefix: str = "",
    tags: list = None
) -> APIRouter:
    """
    Factory function to create authentication router.

    Args:
        user_model: The User model class
        db_dependency: Database dependency function
        get_current_user_func: Function to get current user from token
        prefix: Router prefix (optional)
        tags: Router tags (optional)

    Returns:
        Configured FastAPI router
    """

    router = APIRouter(prefix=prefix, tags=tags or ["authentication"])

    @router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
    async def signup(
        user_data: UserSignupRequest,
        db: AsyncSession = Depends(db_dependency)
    ):
        """Register a new user"""
        # Check if user already exists
        result = await db.execute(
            select(user_model).where(user_model.email == user_data.email.lower())
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = user_model(
            email=user_data.email.lower(),
            password_hash=hashed_password,
            name=user_data.name
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Create access token
        access_token = create_access_token(data={"sub": str(new_user.id)})

        # Return user data and token
        user_response = UserResponse(
            id=str(new_user.id),
            email=new_user.email,
            name=new_user.name,
            company=getattr(new_user, 'company', None),
            email_verified=new_user.email_verified,
            created_at=new_user.created_at.isoformat()
        )

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )

    @router.post("/login", response_model=AuthResponse)
    async def login(
        user_data: UserLoginRequest,
        db: AsyncSession = Depends(db_dependency)
    ):
        """Authenticate a user and return a token"""
        result = await db.execute(
            select(user_model).where(user_model.email == user_data.email.lower())
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(user_data.password, user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=400,
                detail="Inactive user"
            )

        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})

        # Return user data and token
        user_response = UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            company=getattr(user, 'company', None),
            email_verified=user.email_verified,
            created_at=user.created_at.isoformat()
        )

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )

    @router.get("/me", response_model=UserResponse)
    async def get_current_user_info(
        current_user: Any = Depends(get_current_user_func)
    ):
        """Get current user information"""
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            name=current_user.name,
            company=getattr(current_user, 'company', None),
            email_verified=current_user.email_verified,
            created_at=current_user.created_at.isoformat()
        )

    @router.post("/password-reset", status_code=status.HTTP_200_OK)
    async def request_password_reset(
        reset_data: PasswordResetRequest,
        db: AsyncSession = Depends(db_dependency)
    ):
        """Request password reset (placeholder implementation)"""
        # TODO: Implement password reset logic
        # This would typically:
        # 1. Check if user exists
        # 2. Generate reset token
        # 3. Send email with reset link
        return {"message": "Password reset email sent if account exists"}

    @router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
    async def confirm_password_reset(
        reset_data: PasswordResetConfirm,
        db: AsyncSession = Depends(db_dependency)
    ):
        """Confirm password reset (placeholder implementation)"""
        # TODO: Implement password reset confirmation logic
        # This would typically:
        # 1. Verify reset token
        # 2. Update user password
        # 3. Invalidate token
        return {"message": "Password reset successful"}

    return router