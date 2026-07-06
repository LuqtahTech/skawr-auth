"""Tests for services/sessions.py — session management service."""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import relationship, declarative_base

from skawr_auth.services.sessions import (
    create_session,
    list_user_sessions,
    revoke_session,
    revoke_all_sessions,
    cleanup_expired_sessions,
    is_session_valid,
)


# --- Test fixtures using in-memory SQLite with async ---

Base = declarative_base()


class TestUser(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    subscription_tier = Column(String(20), nullable=True)


class TestUserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)
    device = Column(String(512), nullable=True)
    ip_address = Column(String(45), nullable=True)
    product = Column(String(50), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("TestUser")


# Monkey-patch the model used in the service for testing
import skawr_auth.services.sessions as sessions_module

sessions_module.UserSession = TestUserSession


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def user_id(db):
    """Create a test user and return their UUID."""
    uid = uuid.uuid4()
    user = TestUser(id=uid, email=f"test-{uid}@example.com")
    db.add(user)
    await db.commit()
    return uid


@pytest_asyncio.fixture
async def other_user_id(db):
    """Create another test user and return their UUID."""
    uid = uuid.uuid4()
    user = TestUser(id=uid, email=f"other-{uid}@example.com")
    db.add(user)
    await db.commit()
    return uid


class TestCreateSession:
    """Tests for create_session."""

    @pytest.mark.asyncio
    async def test_creates_session_with_all_fields(self, db, user_id):
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        session = await create_session(
            db, user_id=user_id, token_hash="hash123",
            device="Mozilla/5.0", ip="192.168.1.1",
            product="analytics", expires_at=expires,
        )
        await db.commit()

        assert session.id is not None
        assert session.user_id == user_id
        assert session.token_hash == "hash123"
        assert session.device == "Mozilla/5.0"
        assert session.ip_address == "192.168.1.1"
        assert session.product == "analytics"
        # SQLite strips timezone info, so compare without tz
        assert session.expires_at.replace(tzinfo=None) == expires.replace(tzinfo=None)

    @pytest.mark.asyncio
    async def test_creates_session_with_minimal_fields(self, db, user_id):
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        session = await create_session(
            db, user_id=user_id, token_hash="hash_minimal",
            expires_at=expires,
        )
        await db.commit()

        assert session.id is not None
        assert session.device is None
        assert session.ip_address is None
        assert session.product is None

    @pytest.mark.asyncio
    async def test_truncates_long_device_string(self, db, user_id):
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        long_device = "A" * 1000
        session = await create_session(
            db, user_id=user_id, token_hash="hash_long_device",
            device=long_device, expires_at=expires,
        )
        await db.commit()

        assert len(session.device) == 512

    @pytest.mark.asyncio
    async def test_truncates_long_ip_string(self, db, user_id):
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        long_ip = "f" * 100
        session = await create_session(
            db, user_id=user_id, token_hash="hash_long_ip",
            ip=long_ip, expires_at=expires,
        )
        await db.commit()

        assert len(session.ip_address) == 45


class TestListUserSessions:
    """Tests for list_user_sessions."""

    @pytest.mark.asyncio
    async def test_returns_non_expired_sessions(self, db, user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        await create_session(db, user_id=user_id, token_hash="h1",
                            device="Chrome", ip="10.0.0.1",
                            product="analytics", expires_at=future)
        await create_session(db, user_id=user_id, token_hash="h2",
                            device="Firefox", ip="10.0.0.2",
                            product="search_saas", expires_at=future)
        await db.commit()

        sessions = await list_user_sessions(db, user_id)
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_excludes_expired_sessions(self, db, user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        past = datetime.now(timezone.utc) - timedelta(days=1)

        await create_session(db, user_id=user_id, token_hash="valid",
                            expires_at=future)
        await create_session(db, user_id=user_id, token_hash="expired",
                            expires_at=past)
        await db.commit()

        sessions = await list_user_sessions(db, user_id)
        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_excludes_token_hash_from_results(self, db, user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        await create_session(db, user_id=user_id, token_hash="secret_hash",
                            expires_at=future)
        await db.commit()

        sessions = await list_user_sessions(db, user_id)
        assert len(sessions) == 1
        assert "token_hash" not in sessions[0]
        assert "id" in sessions[0]
        assert "device" in sessions[0]
        assert "ip_address" in sessions[0]
        assert "product" in sessions[0]
        assert "created_at" in sessions[0]
        assert "expires_at" in sessions[0]

    @pytest.mark.asyncio
    async def test_does_not_return_other_users_sessions(self, db, user_id, other_user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        await create_session(db, user_id=user_id, token_hash="mine",
                            expires_at=future)
        await create_session(db, user_id=other_user_id, token_hash="theirs",
                            expires_at=future)
        await db.commit()

        sessions = await list_user_sessions(db, user_id)
        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_user_with_no_sessions(self, db, user_id):
        sessions = await list_user_sessions(db, user_id)
        assert sessions == []


class TestRevokeSession:
    """Tests for revoke_session."""

    @pytest.mark.asyncio
    async def test_revokes_own_session(self, db, user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        session = await create_session(db, user_id=user_id, token_hash="to_revoke",
                                      expires_at=future)
        await db.commit()

        result = await revoke_session(db, user_id, session.id)
        await db.commit()

        assert result is True
        sessions = await list_user_sessions(db, user_id)
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_returns_false_for_nonexistent_session(self, db, user_id):
        result = await revoke_session(db, user_id, uuid.uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_other_users_session(self, db, user_id, other_user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        session = await create_session(db, user_id=other_user_id,
                                      token_hash="other_session", expires_at=future)
        await db.commit()

        result = await revoke_session(db, user_id, session.id)
        assert result is False

        # Verify session still exists for the other user
        sessions = await list_user_sessions(db, other_user_id)
        assert len(sessions) == 1


class TestRevokeAllSessions:
    """Tests for revoke_all_sessions."""

    @pytest.mark.asyncio
    async def test_revokes_all_user_sessions(self, db, user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        await create_session(db, user_id=user_id, token_hash="s1", expires_at=future)
        await create_session(db, user_id=user_id, token_hash="s2", expires_at=future)
        await create_session(db, user_id=user_id, token_hash="s3", expires_at=future)
        await db.commit()

        count = await revoke_all_sessions(db, user_id)
        await db.commit()

        assert count == 3
        sessions = await list_user_sessions(db, user_id)
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_does_not_affect_other_users(self, db, user_id, other_user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        await create_session(db, user_id=user_id, token_hash="mine1", expires_at=future)
        await create_session(db, user_id=other_user_id, token_hash="theirs1",
                            expires_at=future)
        await db.commit()

        count = await revoke_all_sessions(db, user_id)
        await db.commit()

        assert count == 1
        other_sessions = await list_user_sessions(db, other_user_id)
        assert len(other_sessions) == 1

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_sessions(self, db, user_id):
        count = await revoke_all_sessions(db, user_id)
        assert count == 0


class TestCleanupExpiredSessions:
    """Tests for cleanup_expired_sessions."""

    @pytest.mark.asyncio
    async def test_removes_expired_sessions(self, db, user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        past = datetime.now(timezone.utc) - timedelta(days=1)

        await create_session(db, user_id=user_id, token_hash="active", expires_at=future)
        await create_session(db, user_id=user_id, token_hash="expired1", expires_at=past)
        await create_session(db, user_id=user_id, token_hash="expired2",
                            expires_at=past - timedelta(days=5))
        await db.commit()

        count = await cleanup_expired_sessions(db, user_id)
        await db.commit()

        assert count == 2
        sessions = await list_user_sessions(db, user_id)
        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_does_not_remove_valid_sessions(self, db, user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        await create_session(db, user_id=user_id, token_hash="valid1", expires_at=future)
        await create_session(db, user_id=user_id, token_hash="valid2", expires_at=future)
        await db.commit()

        count = await cleanup_expired_sessions(db, user_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_expired(self, db, user_id):
        count = await cleanup_expired_sessions(db, user_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_only_cleans_own_user_sessions(self, db, user_id, other_user_id):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        await create_session(db, user_id=user_id, token_hash="my_expired", expires_at=past)
        await create_session(db, user_id=other_user_id, token_hash="their_expired",
                            expires_at=past)
        await db.commit()

        count = await cleanup_expired_sessions(db, user_id)
        await db.commit()

        assert count == 1


class TestIsSessionValid:
    """Tests for is_session_valid."""

    @pytest.mark.asyncio
    async def test_returns_true_for_valid_session(self, db, user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        await create_session(db, user_id=user_id, token_hash="valid_hash",
                            expires_at=future)
        await db.commit()

        result = await is_session_valid(db, "valid_hash")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_expired_session(self, db, user_id):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        await create_session(db, user_id=user_id, token_hash="expired_hash",
                            expires_at=past)
        await db.commit()

        result = await is_session_valid(db, "expired_hash")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_nonexistent_token(self, db, user_id):
        result = await is_session_valid(db, "does_not_exist")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_after_revocation(self, db, user_id):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        session = await create_session(db, user_id=user_id, token_hash="to_be_revoked",
                                      expires_at=future)
        await db.commit()

        await revoke_session(db, user_id, session.id)
        await db.commit()

        result = await is_session_valid(db, "to_be_revoked")
        assert result is False
