"""Extend api_keys table with user_id, product, resource_id, resource_type

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2025-01-01 00:05:00.000000

Requirements: 7.1
- Add user_id column (UUID, nullable, indexed) — FK to users.id
  Nullable because existing keys reference project_id, not user_id directly.
- Add product column (String 50, nullable) — which product this key is scoped to
- Add resource_id column (UUID, nullable, indexed) — polymorphic binding
- Add resource_type column (String 50, nullable) — "project", "search_index", etc.
- Add composite index on (user_id, product) named "idx_api_keys_user_product"
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column — FK to users.id
    # Nullable initially because existing keys reference project_id → project → user path
    op.add_column(
        "api_keys",
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_api_keys_user_id_users",
        "api_keys",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])

    # Add product column — scopes the key to a specific product
    # e.g., analytics, search_saas, client_dashboard, admin_dashboard, marketplace
    op.add_column(
        "api_keys",
        sa.Column("product", sa.String(50), nullable=True),
    )

    # Add resource_id column — polymorphic binding to a specific resource
    # For analytics: project UUID; for search_saas: search_index UUID
    op.add_column(
        "api_keys",
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_api_keys_resource_id", "api_keys", ["resource_id"])

    # Add resource_type column — identifies the type of bound resource
    # e.g., "project", "search_index"
    op.add_column(
        "api_keys",
        sa.Column("resource_type", sa.String(50), nullable=True),
    )

    # Composite index for efficient lookups of all keys for a user within a product
    op.create_index(
        "idx_api_keys_user_product",
        "api_keys",
        ["user_id", "product"],
    )


def downgrade() -> None:
    # Remove composite index
    op.drop_index("idx_api_keys_user_product", table_name="api_keys")

    # Remove resource_type column
    op.drop_column("api_keys", "resource_type")

    # Remove resource_id column and its index
    op.drop_index("ix_api_keys_resource_id", table_name="api_keys")
    op.drop_column("api_keys", "resource_id")

    # Remove product column
    op.drop_column("api_keys", "product")

    # Remove user_id column, its index, and FK constraint
    op.drop_constraint("fk_api_keys_user_id_users", "api_keys", type_="foreignkey")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_column("api_keys", "user_id")
