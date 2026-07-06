"""
Guest claim service for converting credential-less guest APIClients into unified users.

When a guest client (no email/password) later adds credentials, this service
handles converting them into a proper unified user with enrollment and connected store.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.user import User
from ..models.enrollment import ProductEnrollment
from ..models.connected_store import ConnectedStore
from ..utils.auth import get_password_hash


@dataclass
class ClaimResult:
    """Result of a guest claim operation."""

    user_id: UUID
    email: str
    is_new_user: bool  # True if user was created, False if merged into existing
    enrollment_created: bool
    connected_store_created: bool


async def claim_guest_account(
    db: AsyncSession,
    legacy_client_id: UUID,
    email: str,
    password: str,
    name: Optional[str] = None,
) -> ClaimResult:
    """
    Convert a guest APIClient into a unified user.

    Steps:
    1. Check if email already exists in users table
       - If YES: merge — add search_saas enrollment to existing user,
         create connected_store pointing to existing user
       - If NO: create new user with email/password_hash/name
    2. Create ProductEnrollment(product="search_saas", role="admin") for the user
       (skip if already exists)
    3. Create ConnectedStore record with legacy_client_id set
       (skip if legacy_client_id already exists in connected_stores)
    4. Return ClaimResult with details of what happened

    This function does NOT re-associate SearchIndex or APIKey rows —
    that's done by the consuming service (indexer) which has access to those models.
    The connected_store.legacy_client_id allows the indexer to find and re-associate.

    Args:
        db: Async database session.
        legacy_client_id: The UUID of the guest APIClient being claimed.
        email: The email to associate with the new/existing user.
        password: The plaintext password (will be hashed before storage).
        name: Optional display name for the user.

    Returns:
        ClaimResult with details of what was created or merged.
    """
    is_new_user = False
    enrollment_created = False
    connected_store_created = False

    # Step 1: Check if email already exists
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        # Create new user with hashed password
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            name=name,
            is_active=True,
        )
        db.add(user)
        await db.flush()  # Flush to get the user.id assigned
        is_new_user = True
    else:
        # Merge case: user already exists, update name if provided and not set
        if name and not user.name:
            user.name = name

    # Step 2: Create ProductEnrollment (skip if already exists)
    enrollment_stmt = select(ProductEnrollment).where(
        ProductEnrollment.user_id == user.id,
        ProductEnrollment.product == "search_saas",
    )
    enrollment_result = await db.execute(enrollment_stmt)
    existing_enrollment = enrollment_result.scalar_one_or_none()

    if existing_enrollment is None:
        enrollment = ProductEnrollment(
            user_id=user.id,
            product="search_saas",
            role="admin",
            is_active=True,
        )
        db.add(enrollment)
        enrollment_created = True

    # Step 3: Create ConnectedStore with legacy_client_id (skip if already exists)
    store_stmt = select(ConnectedStore).where(
        ConnectedStore.legacy_client_id == legacy_client_id,
    )
    store_result = await db.execute(store_stmt)
    existing_store = store_result.scalar_one_or_none()

    if existing_store is None:
        connected_store = ConnectedStore(
            user_id=user.id,
            platform="skawr_saas",
            platform_store_id=str(legacy_client_id),
            legacy_client_id=legacy_client_id,
        )
        db.add(connected_store)
        connected_store_created = True

    # Commit the entire transaction
    await db.commit()

    return ClaimResult(
        user_id=user.id,
        email=email,
        is_new_user=is_new_user,
        enrollment_created=enrollment_created,
        connected_store_created=connected_store_created,
    )
