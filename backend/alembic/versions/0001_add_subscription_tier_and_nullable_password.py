"""Add subscription_tier to users and make password_hash nullable

Revision ID: 0001
Revises: None
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add subscription_tier column to users table
    op.add_column("users", sa.Column("subscription_tier", sa.String(20), nullable=True))

    # Make password_hash nullable (for OAuth-only users)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    # Revert password_hash to non-nullable
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)

    # Remove subscription_tier column
    op.drop_column("users", "subscription_tier")
