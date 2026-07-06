import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import get_base


def create_subscription_tier_audit_models(base_class=None):
    """Factory function to create SubscriptionTierAudit model with custom base.

    This table is append-only — records are never updated or deleted.
    It tracks changes to a user's subscription_tier field for audit purposes.
    """
    Base = get_base(base_class)

    class SubscriptionTierAudit(Base):
        __tablename__ = "subscription_tier_audit"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
        old_tier = Column(String(20), nullable=True)
        new_tier = Column(String(20), nullable=True)
        changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

        # Relationships
        user = relationship("User")

    return SubscriptionTierAudit


# Module-level default
SubscriptionTierAudit = create_subscription_tier_audit_models()
