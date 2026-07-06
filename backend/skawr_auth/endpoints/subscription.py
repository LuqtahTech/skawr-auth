from typing import Any, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.subscription import (
    ALLOWED_TIERS,
    SubscriptionTierUpdate,
    SubscriptionTierResponse,
)


def create_subscription_router(
    user_model: Any,
    audit_model: Any,
    db_dependency: Callable,
    require_service_api_key: Callable,
) -> APIRouter:
    """Factory creating the internal subscription tier management router.

    This endpoint is INTERNAL only — authenticated by a service-level API key,
    NOT user JWTs. It is called by the payment system (Polar.sh) via webhook
    handler to update user subscription tiers.

    Args:
        user_model: The SQLAlchemy User model class.
        audit_model: The SQLAlchemy SubscriptionTierAudit model class.
        db_dependency: FastAPI dependency that yields a database session.
        require_service_api_key: FastAPI dependency that validates service-level API keys.
    """

    router = APIRouter(tags=["internal"])

    @router.put(
        "/internal/subscription-tier/{user_id}",
        response_model=SubscriptionTierResponse,
        status_code=status.HTTP_200_OK,
    )
    async def update_subscription_tier(
        user_id: UUID,
        body: SubscriptionTierUpdate,
        _api_key: Any = Depends(require_service_api_key),
        db: AsyncSession = Depends(db_dependency),
    ):
        """Update a user's subscription tier.

        This is an internal endpoint authenticated via service-level API key.
        It records the old tier, updates to the new tier, and logs the change
        in the subscription_tier_audit table.

        Returns 404 if user not found.
        Returns 400 if tier value is not in the allowed list.
        """
        # Validate tier value (redundant with Pydantic but explicit for clarity)
        if body.tier is not None and body.tier not in ALLOWED_TIERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier '{body.tier}'. Allowed values: {', '.join(sorted(ALLOWED_TIERS))}, or null",
            )

        # Look up user by user_id
        result = await db.execute(
            select(user_model).where(user_model.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Record old tier
        old_tier = user.subscription_tier

        # Create audit record
        audit_entry = audit_model(
            user_id=user.id,
            old_tier=old_tier,
            new_tier=body.tier,
        )
        db.add(audit_entry)

        # Update user's subscription tier
        user.subscription_tier = body.tier

        await db.commit()
        await db.refresh(audit_entry)

        return SubscriptionTierResponse(
            user_id=str(user.id),
            old_tier=old_tier,
            new_tier=body.tier,
            changed_at=audit_entry.changed_at.isoformat(),
        )

    return router
