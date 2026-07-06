"""
Session management service.

Handles creation, listing, revocation, cleanup, and validation of user sessions.
Sessions are stored in the `user_sessions` table with Postgres as the source of truth
for refresh token revocation.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import UserSession


async def create_session(
    db: AsyncSession,
    user_id: UUID,
    token_hash: str,
    device: Optional[str] = None,
    ip: Optional[str] = None,
    product: Optional[str] = None,
    expires_at: datetime = ...,
) -> UserSession:
    """Create a new session record. Called on login.

    Args:
        db: Async database session.
        user_id: The UUID of the user logging in.
        token_hash: SHA-256 hash of the refresh token.
        device: User-agent string (max 512 chars).
        ip: Client IP address (IPv4 or IPv6).
        product: The product from which login originated.
        expires_at: When the refresh token expires.

    Returns:
        The newly created UserSession instance.
    """
    session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        device=device[:512] if device else None,
        ip_address=ip[:45] if ip else None,
        product=product,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def list_user_sessions(db: AsyncSession, user_id: UUID) -> list[dict]:
    """Returns non-expired sessions for a user, excluding token_hash.

    Each dict contains: id, device, ip_address, product, created_at, expires_at.

    Args:
        db: Async database session.
        user_id: The UUID of the user.

    Returns:
        List of session dicts without sensitive token_hash field.
    """
    now = datetime.now(timezone.utc)
    stmt = select(UserSession).where(
        and_(
            UserSession.user_id == user_id,
            UserSession.expires_at > now,
        )
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return [
        {
            "id": s.id,
            "device": s.device,
            "ip_address": s.ip_address,
            "product": s.product,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
        }
        for s in sessions
    ]


async def revoke_session(db: AsyncSession, user_id: UUID, session_id: UUID) -> bool:
    """Revokes a single session by deleting the row.

    Returns True if found and deleted, False if not found or not owned by user.

    Args:
        db: Async database session.
        user_id: The UUID of the user requesting revocation.
        session_id: The UUID of the session to revoke.

    Returns:
        True if the session was found and deleted, False otherwise.
    """
    stmt = delete(UserSession).where(
        and_(
            UserSession.id == session_id,
            UserSession.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    return result.rowcount > 0


async def revoke_all_sessions(db: AsyncSession, user_id: UUID) -> int:
    """Revokes all sessions for a user. Returns count deleted.

    Args:
        db: Async database session.
        user_id: The UUID of the user.

    Returns:
        Number of sessions deleted.
    """
    stmt = delete(UserSession).where(UserSession.user_id == user_id)
    result = await db.execute(stmt)
    return result.rowcount


async def cleanup_expired_sessions(db: AsyncSession, user_id: UUID) -> int:
    """Removes expired sessions for a user. Called during token refresh.

    Args:
        db: Async database session.
        user_id: The UUID of the user.

    Returns:
        Number of expired sessions removed.
    """
    now = datetime.now(timezone.utc)
    stmt = delete(UserSession).where(
        and_(
            UserSession.user_id == user_id,
            UserSession.expires_at <= now,
        )
    )
    result = await db.execute(stmt)
    return result.rowcount


async def is_session_valid(db: AsyncSession, token_hash: str) -> bool:
    """Check if a refresh token session exists and is not expired.

    Args:
        db: Async database session.
        token_hash: SHA-256 hash of the refresh token to validate.

    Returns:
        True if a valid (non-expired) session exists for the token_hash, False otherwise.
    """
    now = datetime.now(timezone.utc)
    stmt = select(UserSession.id).where(
        and_(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > now,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
