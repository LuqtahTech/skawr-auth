import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, func
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
        password_hash = Column(String(255), nullable=False)
        name = Column(String(255), nullable=True)
        company = Column(String(255), nullable=True)
        email_verified = Column(Boolean, default=False, nullable=False)
        is_active = Column(Boolean, default=True, nullable=False)
        created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

        # Relationships - will be set up when projects are defined
        projects = relationship("Project", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    class UserSession(Base):
        __tablename__ = "user_sessions"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), nullable=False)
        token_hash = Column(String(255), nullable=False)
        expires_at = Column(DateTime(timezone=True), nullable=False)
        created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    return User, UserSession


# Default models with default base
User, UserSession = create_user_models()