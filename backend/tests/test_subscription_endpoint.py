"""Tests for endpoints/subscription.py — internal subscription tier management."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI, Depends
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import relationship, declarative_base

from skawr_auth.endpoints.subscription import create_subscription_router
from skawr_auth.schemas.subscription import ALLOWED_TIERS


# --- Test fixtures using in-memory SQLite with async ---

Base = declarative_base()


class FakeUser(Base):
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


class FakeSubscriptionTierAudit(Base):
    __tablename__ = "subscription_tier_audit"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    old_tier = Column(String(20), nullable=True)
    new_tier = Column(String(20), nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("FakeUser")


# --- Fixtures ---

@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db(session_factory):
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def user_id(db):
    """Create a test user with no subscription tier."""
    uid = uuid.uuid4()
    user = FakeUser(id=uid, email=f"test-{uid}@example.com", subscription_tier=None)
    db.add(user)
    await db.commit()
    return uid


@pytest_asyncio.fixture
async def user_with_tier(db):
    """Create a test user with an existing subscription tier."""
    uid = uuid.uuid4()
    user = FakeUser(id=uid, email=f"tier-{uid}@example.com", subscription_tier="starter")
    db.add(user)
    await db.commit()
    return uid


@pytest_asyncio.fixture
async def app(session_factory):
    """Create a FastAPI app with the subscription router mounted."""

    async def get_db():
        async with session_factory() as session:
            yield session

    async def fake_require_service_api_key():
        """Fake dependency that always passes (simulates valid service API key)."""
        return ("service-key", "internal")

    fastapi_app = FastAPI()
    router = create_subscription_router(
        user_model=FakeUser,
        audit_model=FakeSubscriptionTierAudit,
        db_dependency=get_db,
        require_service_api_key=fake_require_service_api_key,
    )
    fastapi_app.include_router(router)
    return fastapi_app


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# --- Tests ---


class TestUpdateSubscriptionTier:
    """Tests for PUT /internal/subscription-tier/{user_id}."""

    @pytest.mark.asyncio
    async def test_update_tier_from_null_to_growth(self, client, user_id):
        """Updating from null to a valid tier works."""
        resp = await client.put(
            f"/internal/subscription-tier/{user_id}",
            json={"tier": "growth"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == str(user_id)
        assert data["old_tier"] is None
        assert data["new_tier"] == "growth"
        assert "changed_at" in data

    @pytest.mark.asyncio
    async def test_update_tier_from_existing_to_new(self, client, user_with_tier):
        """Updating from an existing tier to another valid tier works."""
        resp = await client.put(
            f"/internal/subscription-tier/{user_with_tier}",
            json={"tier": "scale"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["old_tier"] == "starter"
        assert data["new_tier"] == "scale"

    @pytest.mark.asyncio
    async def test_update_tier_to_null(self, client, user_with_tier):
        """Setting tier to null (cancellation) works."""
        resp = await client.put(
            f"/internal/subscription-tier/{user_with_tier}",
            json={"tier": None},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["old_tier"] == "starter"
        assert data["new_tier"] is None

    @pytest.mark.asyncio
    async def test_all_valid_tiers_accepted(self, client, user_id):
        """All allowed tier values are accepted."""
        for tier in sorted(ALLOWED_TIERS):
            resp = await client.put(
                f"/internal/subscription-tier/{user_id}",
                json={"tier": tier},
            )
            assert resp.status_code == 200, f"Tier '{tier}' was rejected"

    @pytest.mark.asyncio
    async def test_invalid_tier_returns_422(self, client, user_id):
        """An invalid tier value is rejected by Pydantic validation (422)."""
        resp = await client.put(
            f"/internal/subscription-tier/{user_id}",
            json={"tier": "premium"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_404(self, client):
        """Looking up a non-existent user returns 404."""
        fake_id = uuid.uuid4()
        resp = await client.put(
            f"/internal/subscription-tier/{fake_id}",
            json={"tier": "growth"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, client):
        """An invalid UUID in the path returns 422."""
        resp = await client.put(
            "/internal/subscription-tier/not-a-uuid",
            json={"tier": "growth"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_audit_record_created(self, client, user_id, db):
        """Updating the tier creates an audit record."""
        await client.put(
            f"/internal/subscription-tier/{user_id}",
            json={"tier": "enterprise"},
        )

        from sqlalchemy import select
        result = await db.execute(
            select(FakeSubscriptionTierAudit).where(
                FakeSubscriptionTierAudit.user_id == user_id
            )
        )
        audits = result.scalars().all()
        assert len(audits) == 1
        assert audits[0].old_tier is None
        assert audits[0].new_tier == "enterprise"
        assert audits[0].changed_at is not None

    @pytest.mark.asyncio
    async def test_user_subscription_tier_actually_updated(self, client, user_id, db):
        """The user's subscription_tier column is actually updated in the DB."""
        await client.put(
            f"/internal/subscription-tier/{user_id}",
            json={"tier": "growth"},
        )

        from sqlalchemy import select
        result = await db.execute(
            select(FakeUser).where(FakeUser.id == user_id)
        )
        user = result.scalar_one()
        assert user.subscription_tier == "growth"

    @pytest.mark.asyncio
    async def test_multiple_updates_create_multiple_audit_records(self, client, user_id, db):
        """Multiple tier updates create multiple audit entries."""
        await client.put(f"/internal/subscription-tier/{user_id}", json={"tier": "trial"})
        await client.put(f"/internal/subscription-tier/{user_id}", json={"tier": "starter"})
        await client.put(f"/internal/subscription-tier/{user_id}", json={"tier": "growth"})

        from sqlalchemy import select
        result = await db.execute(
            select(FakeSubscriptionTierAudit).where(
                FakeSubscriptionTierAudit.user_id == user_id
            )
        )
        audits = result.scalars().all()
        assert len(audits) == 3

    @pytest.mark.asyncio
    async def test_empty_body_returns_422(self, client, user_id):
        """An empty request body is rejected."""
        resp = await client.put(
            f"/internal/subscription-tier/{user_id}",
            content=b"",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 422
