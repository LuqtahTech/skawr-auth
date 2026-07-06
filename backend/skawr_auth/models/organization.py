import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import get_base


def create_organization_models(base_class=None):
    """Factory function to create Organization and OrganizationMember models with custom base"""
    Base = get_base(base_class)

    class Organization(Base):
        __tablename__ = "organizations"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        name = Column(String(255), nullable=False)
        owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

        # Relationships
        members = relationship("OrganizationMember", back_populates="organization")

    class OrganizationMember(Base):
        __tablename__ = "organization_members"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
        role = Column(String(20), nullable=False, default="member")  # owner, admin, member
        joined_at = Column(DateTime(timezone=True), server_default=func.now())

        __table_args__ = (
            UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        )

        # Relationships
        organization = relationship("Organization", back_populates="members")
        user = relationship("User")

    return Organization, OrganizationMember


# Module-level defaults
Organization, OrganizationMember = create_organization_models()
