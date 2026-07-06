"""Create user_identity_providers table (dormant)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2025-01-01 00:07:00.000000

Requirements: 9.1
- Create `user_identity_providers` table for future OAuth2 social login support
- Columns: id (UUID PK, default gen_random_uuid()), user_id (UUID FK to users.id, not null, indexed),
  provider (String 50, not null — e.g., "google", "github"),
  provider_user_id (String 255, not null), linked_at (DateTime with timezone, server_default now)
- Add unique constraint on (provider, provider_user_id) — one external account links to one user
- This table is dormant — created but not used by any logic yet (future-ready for OAuth2 social login)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_identity_providers",
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
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column(
            "linked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        # Unique constraint: one external account can only be linked to one user
        sa.UniqueConstraint(
            "provider", "provider_user_id", name="uq_provider_provider_user_id"
        ),
    )

    # Index on user_id for efficient lookups of all providers linked to a user
    op.create_index(
        "ix_user_identity_providers_user_id",
        "user_identity_providers",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_identity_providers_user_id",
        table_name="user_identity_providers",
    )
    op.drop_table("user_identity_providers")
