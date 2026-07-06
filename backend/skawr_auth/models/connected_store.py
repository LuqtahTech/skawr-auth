import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from .base import get_base


def create_connected_store_models(base_class=None):
    """Factory function to create ConnectedStore model with custom base"""
    Base = get_base(base_class)

    class ConnectedStore(Base):
        __tablename__ = "connected_stores"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
        platform = Column(String(20), nullable=False)  # "salla" or "shopify"
        platform_store_id = Column(String(100), nullable=False, index=True)
        platform_store_url = Column(String(500), nullable=True)
        platform_email = Column(String(255), nullable=True)

        # OAuth tokens (encrypted at application level)
        access_token = Column(Text, nullable=True)
        refresh_token = Column(Text, nullable=True)
        token_expires_at = Column(DateTime(timezone=True), nullable=True)
        oauth_scope = Column(Text, nullable=True)  # Shopify granted scopes

        # Subscription state
        subscription_status = Column(String(50), nullable=True)  # active, canceled, expired, trial
        subscription_tier = Column(String(50), nullable=True)  # pro, enterprise, etc.
        trial_started_at = Column(DateTime(timezone=True), nullable=True)
        trial_expires_at = Column(DateTime(timezone=True), nullable=True)

        # Platform-specific settings
        settings = Column(JSON, nullable=True)

        # Back-reference to legacy APIClient UUID (for migration resolution)
        legacy_client_id = Column(UUID(as_uuid=True), nullable=True, unique=True, index=True)

        # Timestamps
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

        __table_args__ = (
            UniqueConstraint("platform", "platform_store_id", name="uq_platform_store"),
        )

        # Relationships
        user = relationship("User", back_populates="connected_stores")

    return ConnectedStore


# Module-level default
ConnectedStore = create_connected_store_models()
