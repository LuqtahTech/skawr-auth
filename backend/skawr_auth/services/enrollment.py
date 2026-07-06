"""
Enrollment service for managing user product enrollments.

Provides async functions for creating, querying, revoking, restoring,
and assigning roles on ProductEnrollment records.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.enrollment import ProductEnrollment


async def get_or_create_enrollment(
    db: AsyncSession, user_id: UUID, product: str, default_role: str = "member"
) -> ProductEnrollment:
    """Ensures an enrollment exists for user+product. Creates with default_role if missing.

    Uses SELECT then INSERT pattern with conflict handling.

    Args:
        db: Async database session.
        user_id: The user's UUID.
        product: Product identifier (e.g. "analytics", "search_saas").
        default_role: Role to assign if creating a new enrollment.

    Returns:
        The existing or newly created ProductEnrollment.
    """
    stmt = select(ProductEnrollment).where(
        ProductEnrollment.user_id == user_id,
        ProductEnrollment.product == product,
    )
    result = await db.execute(stmt)
    enrollment = result.scalar_one_or_none()

    if enrollment is not None:
        return enrollment

    enrollment = ProductEnrollment(
        user_id=user_id,
        product=product,
        role=default_role,
        is_active=True,
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def get_user_enrollments(db: AsyncSession, user_id: UUID) -> list[ProductEnrollment]:
    """Returns all active enrollments for a user (is_active=True).

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        List of active ProductEnrollment records.
    """
    stmt = select(ProductEnrollment).where(
        ProductEnrollment.user_id == user_id,
        ProductEnrollment.is_active == True,  # noqa: E712
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def revoke_all_enrollments(db: AsyncSession, user_id: UUID) -> int:
    """Marks all active enrollments as revoked (is_active=False, revoked_at=now()).

    Called when a user is deactivated. Returns count of revoked enrollments.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Number of enrollments revoked.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        update(ProductEnrollment)
        .where(
            ProductEnrollment.user_id == user_id,
            ProductEnrollment.is_active == True,  # noqa: E712
        )
        .values(is_active=False, revoked_at=now)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def restore_all_enrollments(db: AsyncSession, user_id: UUID) -> int:
    """Restores previously revoked enrollments (is_active=True, revoked_at=None).

    Only restores enrollments where revoked_at is NOT null (i.e., they were
    revoked via revoke_all_enrollments, not manually deactivated).
    Returns count of restored enrollments.

    Args:
        db: Async database session.
        user_id: The user's UUID.

    Returns:
        Number of enrollments restored.
    """
    stmt = (
        update(ProductEnrollment)
        .where(
            ProductEnrollment.user_id == user_id,
            ProductEnrollment.is_active == False,  # noqa: E712
            ProductEnrollment.revoked_at != None,  # noqa: E711
        )
        .values(is_active=True, revoked_at=None)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


async def assign_role(
    db: AsyncSession, user_id: UUID, product: str, role: str, actor_role: str
) -> ProductEnrollment:
    """Assigns a role to a user for a product.

    Raises PermissionError if actor_role is not "admin".
    Creates enrollment if it doesn't exist.

    Args:
        db: Async database session.
        user_id: The target user's UUID.
        product: Product identifier.
        role: The role to assign (e.g. "admin", "member", "viewer").
        actor_role: The role of the user performing the assignment.

    Returns:
        The updated ProductEnrollment.

    Raises:
        PermissionError: If actor_role is not "admin".
    """
    if actor_role != "admin":
        raise PermissionError("Only admins can assign roles")

    enrollment = await get_or_create_enrollment(db, user_id, product, default_role=role)

    if enrollment.role != role:
        enrollment.role = role
        await db.commit()
        await db.refresh(enrollment)

    return enrollment
