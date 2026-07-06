"""Create connected_stores table

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2025-01-01 00:03:00.000000

Requirements: 11.3
- Create connected_stores table for Salla/Shopify OAuth data
- One user can own multiple stores across platforms
- Migrated from APIClient columns to a dedicated table
- Unique constraint on (platform, platform_store_id) named "uq_platform_store"
- legacy_client_id is unique and indexed for migration resolution
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "connected_stores",
        # Primary key
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # Owner reference
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        # Platform identification
        sa.Column("platform", sa.String(20), nullable=False),  # "salla" or "shopify"
        sa.Column("platform_store_id", sa.String(100), nullable=False),
        sa.Column("platform_store_url", sa.String(500), nullable=True),
        sa.Column("platform_email", sa.String(255), nullable=True),
        # OAuth tokens (encrypted at application level)
        sa.Column("access_token", sa.Text, nullable=True),
        sa.Column("refresh_token", sa.Text, nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("oauth_scope", sa.Text, nullable=True),
        # Subscription state
        sa.Column("subscription_status", sa.String(50), nullable=True),  # active, canceled, expired, trial
        sa.Column("subscription_tier", sa.String(50), nullable=True),
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True),
        # Platform-specific settings
        sa.Column("settings", sa.JSON, nullable=True),
        # Back-reference for migration resolution
        sa.Column("legacy_client_id", UUID(as_uuid=True), nullable=True, unique=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Unique constraint: one store per platform
        sa.UniqueConstraint("platform", "platform_store_id", name="uq_platform_store"),
    )

    # Indexes for common query patterns
    op.create_index("idx_connected_stores_user_id", "connected_stores", ["user_id"])
    op.create_index("idx_connected_stores_platform_store_id", "connected_stores", ["platform_store_id"])
    op.create_index("idx_connected_stores_legacy_client_id", "connected_stores", ["legacy_client_id"])


def downgrade() -> None:
    op.drop_table("connected_stores")
