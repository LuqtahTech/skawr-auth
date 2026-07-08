"""Common utilities for data migration scripts."""

import logging
import sys
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


@dataclass
class MigrationReport:
    """Summary report output by each migration script."""

    source: str
    total_processed: int = 0
    total_migrated: int = 0
    total_skipped_conflict: int = 0
    total_skipped_null_email: int = 0
    total_enrollments_created: int = 0
    total_connected_stores_created: int = 0
    conflicts: list = field(default_factory=list)
    skipped_ids: list = field(default_factory=list)

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"  Migration Summary: {self.source}")
        print(f"{'='*60}")
        print(f"  Total records processed: {self.total_processed}")
        print(f"  Total migrated:          {self.total_migrated}")
        print(f"  Skipped (email conflict): {self.total_skipped_conflict}")
        print(f"  Skipped (null email):     {self.total_skipped_null_email}")
        print(f"  Enrollments created:      {self.total_enrollments_created}")
        print(f"  Connected stores created: {self.total_connected_stores_created}")
        if self.conflicts:
            print(f"\n  Conflicts:")
            for c in self.conflicts[:20]:  # Show first 20
                print(f"    - {c}")
        if self.skipped_ids:
            print(f"\n  Skipped IDs (first 20):")
            for sid in self.skipped_ids[:20]:
                print(f"    - {sid}")
        print(f"{'='*60}\n")


def get_db_session(database_url: str) -> Session:
    """Create a sync SQLAlchemy session from a database URL."""
    # Convert async URLs to sync
    url = database_url.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "")
    engine = create_engine(url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def user_exists_by_id(session: Session, user_id: UUID) -> bool:
    """Check if a user with this UUID already exists (idempotency check)."""
    from skawr_auth.models.user import User

    result = session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none() is not None


def user_exists_by_email(session: Session, email: str):
    """Get existing user by email or return None."""
    from skawr_auth.models.user import User

    result = session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


def enrollment_exists(session: Session, user_id: UUID, product: str) -> bool:
    """Check if an enrollment already exists for this user+product."""
    from skawr_auth.models.enrollment import ProductEnrollment

    result = session.execute(
        select(ProductEnrollment).where(
            ProductEnrollment.user_id == user_id,
            ProductEnrollment.product == product,
        )
    )
    return result.scalar_one_or_none() is not None
