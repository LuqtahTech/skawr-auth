"""Create subscription_tier_audit table

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2025-01-01 00:08:00.000000

Requirements: 15.5
- Create `subscription_tier_audit` table to log all subscription tier changes
- Columns: id (UUID PK, default gen_random_uuid()), user_id (UUID FK to users.id, not null, indexed),
  old_tier (String 20, nullable), new_tier (String 20, nullable),
  changed_at (DateTime with timezone, server_default now, not null)
- Add index on user_id for efficient audit queries
- This table is append-only — records are never updated or deleted
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscription_tier_audit",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("old_tier", sa.String(20), nullable=True),
        sa.Column("new_tier", sa.String(20), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Index on user_id for efficient audit queries (e.g., "show tier history for user X")
    op.create_index(
        "ix_subscription_tier_audit_user_id",
        "subscription_tier_audit",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_subscription_tier_audit_user_id",
        table_name="subscription_tier_audit",
    )
    op.drop_table("subscription_tier_audit")
