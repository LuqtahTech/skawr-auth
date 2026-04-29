from typing import Any, Callable, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from slowapi import Limiter
from slowapi.util import get_remote_address

from ..schemas.auth import (
    UserSignupRequest,
    UserLoginRequest,
    UserResponse,
    AuthResponse,
    RefreshTokenRequest,
    TokenPair,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from ..utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    TOKEN_TYPE_REFRESH,
)


# Module-level limiter so consumers can register the exception handler.
limiter = Limiter(key_func=get_remote_address)


def _user_response(user: Any) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        company=getattr(user, "company", None),
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat(),
    )


def _issue_tokens(user_id: str) -> tuple[str, str]:
    return create_access_token({"sub": user_id}), create_refresh_token({"sub": user_id})


def create_auth_router(
    user_model: Any,
    db_dependency: Any,
    get_current_user_func: Callable,
    prefix: str = "",
    tags: Optional[list] = None,
) -> APIRouter:
    """Factory creating the authentication router with rate-limited endpoints."""

    router = APIRouter(prefix=prefix, tags=tags or ["authentication"])

    @router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
    @limiter.limit("5/minute")
    async def signup(
        request: Request,
        user_data: UserSignupRequest,
        db: AsyncSession = Depends(db_dependency),
    ):
        result = await db.execute(
            select(user_model).where(user_model.email == user_data.email.lower())
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        new_user = user_model(
            email=user_data.email.lower(),
            password_hash=get_password_hash(user_data.password),
            name=user_data.name,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        access, refresh = _issue_tokens(str(new_user.id))
        return AuthResponse(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            user=_user_response(new_user),
        )

    @router.post("/login", response_model=AuthResponse)
    @limiter.limit("10/minute")
    async def login(
        request: Request,
        user_data: UserLoginRequest,
        db: AsyncSession = Depends(db_dependency),
    ):
        result = await db.execute(
            select(user_model).where(user_model.email == user_data.email.lower())
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(user_data.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")

        access, refresh = _issue_tokens(str(user.id))
        return AuthResponse(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            user=_user_response(user),
        )

    @router.post("/refresh", response_model=TokenPair)
    @limiter.limit("60/minute")
    async def refresh(
        request: Request,
        body: RefreshTokenRequest,
        db: AsyncSession = Depends(db_dependency),
    ):
        payload = verify_token(body.refresh_token, expected_type=TOKEN_TYPE_REFRESH)
        if payload is None or "sub" not in payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        user_id = payload["sub"]
        result = await db.execute(select(user_model).where(user_model.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        access, new_refresh = _issue_tokens(str(user.id))
        return TokenPair(access_token=access, refresh_token=new_refresh, token_type="bearer")

    @router.get("/me", response_model=UserResponse)
    async def get_current_user_info(current_user: Any = Depends(get_current_user_func)):
        return _user_response(current_user)

    # Password reset stays as a placeholder for now; wire to email infra later.
    @router.post("/password-reset", status_code=status.HTTP_200_OK)
    @limiter.limit("3/minute")
    async def request_password_reset(
        request: Request,
        reset_data: PasswordResetRequest,
        db: AsyncSession = Depends(db_dependency),
    ):
        return {"message": "Password reset email sent if account exists"}

    @router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
    @limiter.limit("5/minute")
    async def confirm_password_reset(
        request: Request,
        reset_data: PasswordResetConfirm,
        db: AsyncSession = Depends(db_dependency),
    ):
        return {"message": "Password reset successful"}

    return router
