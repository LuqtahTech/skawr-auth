"""
Resource resolver: bridges unified auth (user UUID in token) with product-specific resources.

After the unified auth migration, tokens carry `sub` = user UUID rather than
the legacy `client_id`. This module resolves a user's product-specific resources
(connected stores, API keys, projects) for a given product context.

Requirements: 6.2, 13.3
"""

from dataclasses import dataclass, field
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from skawr_auth.models.connected_store import ConnectedStore
from skawr_auth.models.project import Project, APIKey


@dataclass
class UserResources:
    """Resolved resources for a user within a specific product."""

    user_id: UUID
    product: str
    connected_stores: list = field(default_factory=list)  # ConnectedStore rows (search_saas)
    search_indices: list = field(default_factory=list)  # SearchIndex rows (search_saas) - resolved by consumer
    projects: list = field(default_factory=list)  # Project rows (analytics) - resolved by consumer
    api_keys: list = field(default_factory=list)  # APIKey rows scoped to this product


async def get_current_user_resources_async(
    db: AsyncSession,
    user_id: UUID,
    product: str,
) -> UserResources:
    """
    Resolve a user's resources for a specific product (async variant).

    For search_saas:
        - Queries connected_stores WHERE user_id matches
        - Queries api_keys WHERE user_id matches AND product = "search_saas"

    For analytics:
        - Queries projects WHERE user_id matches
        - Queries api_keys WHERE user_id matches AND product = "analytics"

    For other products:
        - Queries api_keys only

    Args:
        db: An async SQLAlchemy session.
        user_id: The unified user UUID from the JWT `sub` claim.
        product: The product identifier (e.g., "search_saas", "analytics").

    Returns:
        A UserResources dataclass populated with the user's resources for the product.
    """
    resources = UserResources(user_id=user_id, product=product)

    if product == "search_saas":
        # Resolve connected stores
        stores_result = await db.execute(
            select(ConnectedStore).where(ConnectedStore.user_id == user_id)
        )
        resources.connected_stores = list(stores_result.scalars().all())

    elif product == "analytics":
        # Resolve projects
        projects_result = await db.execute(
            select(Project).where(Project.user_id == user_id)
        )
        resources.projects = list(projects_result.scalars().all())

    # Always resolve API keys scoped to this product
    api_keys_result = await db.execute(
        select(APIKey).where(
            APIKey.user_id == user_id,
            APIKey.product == product,
        )
    )
    resources.api_keys = list(api_keys_result.scalars().all())

    return resources


def get_current_user_resources_sync(
    db: Session,
    user_id: UUID,
    product: str,
) -> UserResources:
    """
    Resolve a user's resources for a specific product (sync variant for the indexer).

    For search_saas:
        - Queries connected_stores WHERE user_id matches
        - Queries api_keys WHERE user_id matches AND product = "search_saas"

    For analytics:
        - Queries projects WHERE user_id matches
        - Queries api_keys WHERE user_id matches AND product = "analytics"

    For other products:
        - Queries api_keys only

    Args:
        db: A sync SQLAlchemy session.
        user_id: The unified user UUID from the JWT `sub` claim.
        product: The product identifier (e.g., "search_saas", "analytics").

    Returns:
        A UserResources dataclass populated with the user's resources for the product.
    """
    resources = UserResources(user_id=user_id, product=product)

    if product == "search_saas":
        # Resolve connected stores
        stores_result = db.execute(
            select(ConnectedStore).where(ConnectedStore.user_id == user_id)
        )
        resources.connected_stores = list(stores_result.scalars().all())

    elif product == "analytics":
        # Resolve projects
        projects_result = db.execute(
            select(Project).where(Project.user_id == user_id)
        )
        resources.projects = list(projects_result.scalars().all())

    # Always resolve API keys scoped to this product
    api_keys_result = db.execute(
        select(APIKey).where(
            APIKey.user_id == user_id,
            APIKey.product == product,
        )
    )
    resources.api_keys = list(api_keys_result.scalars().all())

    return resources


async def resolve_legacy_client_to_user_async(
    db: AsyncSession,
    client_id: UUID,
) -> Optional[UUID]:
    """
    Resolve a legacy APIClient UUID to a unified user UUID (async variant).

    During the transition period, legacy indexer tokens carry a `client_id` claim.
    This function looks up the connected_stores table to find the user who owns
    the store previously associated with that APIClient.

    Args:
        db: An async SQLAlchemy session.
        client_id: The legacy APIClient UUID from the JWT `client_id` claim.

    Returns:
        The unified user UUID if a matching connected_store is found, None otherwise.
    """
    result = await db.execute(
        select(ConnectedStore.user_id).where(
            ConnectedStore.legacy_client_id == client_id
        )
    )
    user_id = result.scalar_one_or_none()
    return user_id


def resolve_legacy_client_to_user_sync(
    db: Session,
    client_id: UUID,
) -> Optional[UUID]:
    """
    Resolve a legacy APIClient UUID to a unified user UUID (sync variant).

    During the transition period, legacy indexer tokens carry a `client_id` claim.
    This function looks up the connected_stores table to find the user who owns
    the store previously associated with that APIClient.

    Args:
        db: A sync SQLAlchemy session.
        client_id: The legacy APIClient UUID from the JWT `client_id` claim.

    Returns:
        The unified user UUID if a matching connected_store is found, None otherwise.
    """
    result = db.execute(
        select(ConnectedStore.user_id).where(
            ConnectedStore.legacy_client_id == client_id
        )
    )
    user_id = result.scalar_one_or_none()
    return user_id
