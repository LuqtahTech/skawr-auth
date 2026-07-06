import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import get_base


def create_identity_provider_models(base_class=None):
    """Factory function to create UserIdentityProvider model with custom base"""
    Base = get_base(base_class)

    class UserIdentityProvider(Base):
        __tablename__ = "user_identity_providers"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
        provider = Column(String(50), nullable=False)  # google, github
        provider_user_id = Column(String(255), nullable=False)
        linked_at = Column(DateTime(timezone=True), server_default=func.now())

        __table_args__ = (
            UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
        )

        # Relationships
        user = relationship("User")

    return UserIdentityProvider


# Module-level default
UserIdentityProvider = create_identity_provider_models()
