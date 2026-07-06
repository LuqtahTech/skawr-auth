import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import get_base


def create_enrollment_models(base_class=None):
    """Factory function to create ProductEnrollment model with custom base"""
    Base = get_base(base_class)

    class ProductEnrollment(Base):
        __tablename__ = "product_enrollments"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
        product = Column(String(50), nullable=False)  # analytics, search_saas, client_dashboard, admin_dashboard, marketplace
        role = Column(String(20), nullable=False, default="member")  # admin, member, viewer
        is_active = Column(Boolean, default=True, nullable=False)
        enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
        revoked_at = Column(DateTime(timezone=True), nullable=True)

        __table_args__ = (
            UniqueConstraint("user_id", "product", name="uq_user_product"),
        )

        user = relationship("User", back_populates="enrollments")

    return ProductEnrollment


# Module-level default
ProductEnrollment = create_enrollment_models()
