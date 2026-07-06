"""Add subscription_tier to users and make password_hash nullable

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2025-01-01 00:01:00.000000

Requirements: 1.5, 15.3
- Add nullable subscription_tier column (String(20)) to users table
  Allowed values: trial, starter, growth, scale, enterprise (or NULL)
- Alter password_hash column to nullable=True (for OAuth-only users)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add subscription_tier column to users table
    # Allowed values: trial, starter, growth, scale, enterprise (enforced at app level)
    op.add_column(
        "users",
        sa.Column("subscription_tier", sa.String(20), nullable=True),
    )

    # Make password_hash nullable to support OAuth-only users
    # who authenticate via Identity Providers without a local password
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    # Revert password_hash to non-nullable
    # NOTE: This will fail if any rows have NULL password_hash.
    # Ensure all users have a password before downgrading.
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(255),
        nullable=False,
    )

    # Remove subscription_tier column
    op.drop_column("users", "subscription_tier")
