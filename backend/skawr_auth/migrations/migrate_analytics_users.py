"""
Migrate existing analytics users to unified auth.

Since analytics already uses the shared skawr-auth User model on the same Postgres,
the users are ALREADY in the unified `users` table. This script's job is:
1. Create product_enrollment records (product=analytics, role=admin) for each existing user
2. Output summary report

The script is idempotent — if an enrollment already exists it is skipped.

Usage:
    SKAWR_AUTH_DATABASE_URL=postgresql://... python -m skawr_auth.migrations.migrate_analytics_users
"""

import logging
import os
import sys
import uuid

from sqlalchemy import select

from skawr_auth.migrations.utils import (
    MigrationReport,
    enrollment_exists,
    get_db_session,
)
from skawr_auth.models.enrollment import ProductEnrollment
from skawr_auth.models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PRODUCT = "analytics"
DEFAULT_ROLE = "admin"


def run_migration(database_url: str) -> MigrationReport:
    """Run the analytics user migration.

    Creates product_enrollment records for all existing users in the database.
    Since analytics shares the same Postgres and User model, users already exist
    in the `users` table — we just need to add enrollments.
    """
    report = MigrationReport(source="analytics_users")
    session = get_db_session(database_url)

    try:
        # Query all existing users
        result = session.execute(select(User))
        users = result.scalars().all()

        logger.info(f"Found {len(users)} users in the database")

        for user in users:
            report.total_processed += 1

            # Skip users without email (shouldn't happen but defensive)
            if not user.email:
                report.total_skipped_null_email += 1
                report.skipped_ids.append(str(user.id))
                logger.warning(f"Skipping user {user.id} — null email")
                continue

            # Check if enrollment already exists (idempotency)
            if enrollment_exists(session, user.id, PRODUCT):
                logger.debug(f"Enrollment already exists for user {user.id} / {PRODUCT}")
                report.total_skipped_conflict += 1
                continue

            # Create the enrollment
            enrollment = ProductEnrollment(
                id=uuid.uuid4(),
                user_id=user.id,
                product=PRODUCT,
                role=DEFAULT_ROLE,
                is_active=True,
            )
            session.add(enrollment)
            report.total_migrated += 1
            report.total_enrollments_created += 1

            # Commit in batches of 100 for performance
            if report.total_migrated % 100 == 0:
                session.commit()
                logger.info(f"Committed batch — {report.total_migrated} enrollments created so far")

        # Final commit for remaining records
        session.commit()
        logger.info("Migration complete")

    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        session.close()

    return report


def main():
    database_url = os.environ.get("SKAWR_AUTH_DATABASE_URL")
    if not database_url:
        print("ERROR: SKAWR_AUTH_DATABASE_URL environment variable is required")
        sys.exit(1)

    print(f"Starting analytics user migration...")
    print(f"Database: {database_url.split('@')[-1] if '@' in database_url else '(masked)'}")

    report = run_migration(database_url)
    report.print_summary()


if __name__ == "__main__":
    main()
