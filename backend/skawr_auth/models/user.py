import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import get_base


def create_user_models(base_class=None):
    """Factory function to create User models with custom base"""
    Base = get_base(base_class)

    class User(Base):
        __tablename__ = "users"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        email = Column(String(255), unique=True, index=True, nullable=False)
        password_hash = Column(String(255), nullable=True)  # nullable for OAuth-only users
        name = Column(String(255), nullable=True)
        company = Column(String(255), nullable=True)
        email_verified = Column(Boolean, default=False, nullable=False)
        is_active = Column(Boolean, default=True, nullable=False)
        created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
        # Subscription tier: trial, starter, growth, scale, enterprise
        subscription_tier = Column(String(20), nullable=True)

        # Relationships
        projects = relationship("Project", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
        enrollments = relationship("ProductEnrollment", back_populates="user", lazy="selectin")
        connected_stores = relationship("ConnectedStore", back_populates="user", lazy="selectin")
        sessions = relationship("UserSession", back_populates="user", lazy="dynamic")

    class UserSession(Base):
        __tablename__ = "user_sessions"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
        token_hash = Column(String(255), nullable=False, unique=True)
        device = Column(String(512), nullable=True)
        ip_address = Column(String(45), nullable=True)
        product = Column(String(50), nullable=True)
        expires_at = Column(DateTime(timezone=True), nullable=False)
        created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

        user = relationship("User", back_populates="sessions")

    return User, UserSession


# Default models with default base
User, UserSession = create_user_models()
