"""Create organizations and organization_members tables (dormant)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2025-01-01 00:06:00.000000

Requirements: 8.1, 8.2
- Create `organizations` table: id (UUID PK, default gen_random_uuid()), name (String 255, not null),
  owner_user_id (UUID FK to users.id, not null), created_at (DateTime with timezone, server_default now)
- Create `organization_members` table: id (UUID PK, default gen_random_uuid()),
  organization_id (UUID FK to organizations.id, not null), user_id (UUID FK to users.id, not null),
  role (String 20, not null, default "member"), joined_at (DateTime with timezone, server_default now)
- Add unique constraint on organization_members (organization_id, user_id)
- These tables are "dormant" — created but not used by any logic yet (future-ready)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        "organizations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "owner_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create organization_members table
    op.create_table(
        "organization_members",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Unique constraint: a user can only be a member of an organization once
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_org_member_org_user"
        ),
    )


def downgrade() -> None:
    op.drop_table("organization_members")
    op.drop_table("organizations")
