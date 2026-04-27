import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from .base import get_base


def create_project_models(base_class=None):
    """Factory function to create Project models with custom base"""
    Base = get_base(base_class)

    class Project(Base):
        __tablename__ = "projects"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
        name = Column(String(255), nullable=False)
        description = Column(Text, nullable=True)
        domain = Column(String(255), nullable=True)
        is_active = Column(Boolean, default=True, nullable=False)

        # Analytics settings
        settings = Column(JSON, default={}, nullable=False)

        # Timestamps
        created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

        # Relationships
        user = relationship("User", back_populates="projects")
        api_keys = relationship("APIKey", back_populates="project", cascade="all, delete-orphan")

    class APIKey(Base):
        __tablename__ = "api_keys"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
        name = Column(String(255), nullable=False)

        # Key storage - hash the full key, store prefix for display
        key_hash = Column(String(256), nullable=False, unique=True)
        key_prefix = Column(String(8), nullable=False)

        # Permissions and settings
        permissions = Column(JSON, default=["track", "query"], nullable=False)
        rate_limit = Column(Integer, default=1000, nullable=False)  # requests per hour

        # Status and timestamps
        is_active = Column(Boolean, default=True, nullable=False)
        last_used_at = Column(DateTime(timezone=True), nullable=True)
        expires_at = Column(DateTime(timezone=True), nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

        # Relationships
        project = relationship("Project", back_populates="api_keys")

    return Project, APIKey


# Default models with default base
Project, APIKey = create_project_models()