import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, Index, func
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

        # Direct owner reference (nullable — existing keys use project_id → project → user)
        user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

        # Product scope (which product this key is scoped to)
        product = Column(String(50), nullable=True)  # analytics, search_saas, etc.

        # Key storage - hash the full key, store prefix for display
        key_hash = Column(String(256), nullable=False, unique=True)
        key_prefix = Column(String(8), unique=True, nullable=False)

        # Permissions and settings
        permissions = Column(JSON, default=["track", "query"], nullable=False)
        rate_limit = Column(Integer, default=1000, nullable=False)  # requests per hour

        # Status and timestamps
        is_active = Column(Boolean, default=True, nullable=False)
        last_used_at = Column(DateTime(timezone=True), nullable=True)
        expires_at = Column(DateTime(timezone=True), nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

        # Polymorphic resource binding
        # For analytics: resource_id = project UUID, resource_type = "project"
        # For search_saas: resource_id = search_index UUID, resource_type = "search_index"
        # For unscoped keys: both are NULL (key works on all resources the user owns in that product)
        resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
        resource_type = Column(String(50), nullable=True)  # "project", "search_index", etc.

        __table_args__ = (
            Index("idx_api_keys_user_product", "user_id", "product"),
        )

        # Relationships
        project = relationship("Project", back_populates="api_keys")
        user = relationship("User")

    return Project, APIKey


# Default models with default base
Project, APIKey = create_project_models()