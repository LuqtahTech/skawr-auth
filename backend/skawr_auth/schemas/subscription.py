from typing import Optional
from pydantic import BaseModel, field_validator


ALLOWED_TIERS = {"trial", "starter", "growth", "scale", "enterprise"}


class SubscriptionTierUpdate(BaseModel):
    """Request body for updating a user's subscription tier."""

    tier: Optional[str] = None

    @field_validator("tier")
    @classmethod
    def _validate_tier(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ALLOWED_TIERS:
            raise ValueError(
                f"Invalid tier '{v}'. Allowed values: {', '.join(sorted(ALLOWED_TIERS))}, or null"
            )
        return v


class SubscriptionTierResponse(BaseModel):
    """Response after updating a user's subscription tier."""

    user_id: str
    old_tier: Optional[str] = None
    new_tier: Optional[str] = None
    changed_at: str
