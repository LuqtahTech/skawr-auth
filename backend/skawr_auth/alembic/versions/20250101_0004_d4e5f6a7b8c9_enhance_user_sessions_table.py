"""Enhance user_sessions table with device, ip_address, product columns and constraints

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2025-01-01 00:04:00.000000

Requirements: 5.1
- Add device column (String 512, nullable) — user-agent string
- Add ip_address column (String 45, nullable) — IPv4 or IPv6
- Add product column (String 50, nullable) — originating product identifier
- Add user_id FK constraint to users.id
- Add unique constraint on token_hash
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add device column — stores the user-agent string (max 512 chars)
    op.add_column(
        "user_sessions",
        sa.Column("device", sa.String(512), nullable=True),
    )

    # Add ip_address column — supports both IPv4 and IPv6 (max 45 chars)
    op.add_column(
        "user_sessions",
        sa.Column("ip_address", sa.String(45), nullable=True),
    )

    # Add product column — identifies originating product (e.g., analytics, search_saas)
    op.add_column(
        "user_sessions",
        sa.Column("product", sa.String(50), nullable=True),
    )

    # Add foreign key constraint on user_id → users.id
    # The column already exists as a UUID but without FK enforcement
    op.create_foreign_key(
        "fk_user_sessions_user_id_users",
        "user_sessions",
        "users",
        ["user_id"],
        ["id"],
    )

    # Add unique constraint on token_hash to prevent duplicate sessions
    op.create_unique_constraint(
        "uq_user_sessions_token_hash",
        "user_sessions",
        ["token_hash"],
    )


def downgrade() -> None:
    # Remove unique constraint on token_hash
    op.drop_constraint(
        "uq_user_sessions_token_hash",
        "user_sessions",
        type_="unique",
    )

    # Remove foreign key constraint on user_id
    op.drop_constraint(
        "fk_user_sessions_user_id_users",
        "user_sessions",
        type_="foreignkey",
    )

    # Remove product column
    op.drop_column("user_sessions", "product")

    # Remove ip_address column
    op.drop_column("user_sessions", "ip_address")

    # Remove device column
    op.drop_column("user_sessions", "device")
