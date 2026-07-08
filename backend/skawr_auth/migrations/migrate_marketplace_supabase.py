"""
Migrate marketplace users from Supabase to unified auth.

Reads from Supabase's auth.users table (via direct Postgres connection to the
Supabase DB) and creates unified user records with marketplace enrollment.

OAuth-only users (no password) get a null password_hash and are flagged for
password setup or identity provider linkage.

The script is idempotent — if records already exist they are skipped.

Two database connections are used:
- SUPABASE_DATABASE_URL: Source (Supabase Postgres, reads auth.users)
- SKAWR_AUTH_DATABASE_URL: Target (unified auth Postgres, writes users + enrollments)

Usage:
    SUPABASE_DATABASE_URL=postgresql://... SKAWR_AUTH_DATABASE_URL=postgresql://... \
        python -m skawr_auth.migrations.migrate_marketplace_supabase
"""

import logging
import os
import sys
import uuid

from sqlalchemy import text

from skawr_auth.migrations.utils import (
    MigrationReport,
    enrollment_exists,
    get_db_session,
    user_exists_by_email,
)
from skawr_auth.models.enrollment import ProductEnrollment
from skawr_auth.models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PRODUCT = "marketplace"
DEFAULT_ROLE = "member"

# Query Supabase's auth.users table
SUPABASE_USERS_QUERY = text(
    "SELECT id, email, encrypted_password, raw_user_meta_data, created_at "
    "FROM auth.users "
    "WHERE email IS NOT NULL"
)


def run_migration(supabase_url: str, target_url: str) -> MigrationReport:
    """Run the marketplace Supabase migration.

    Reads users from Supabase's auth.users and creates unified user records
    with marketplace enrollment in the target database.
    """
    report = MigrationReport(source="marketplace_supabase")

    # Connect to both databases
    supabase_session = get_db_session(supabase_url)
    target_session = get_db_session(target_url)

    try:
        # Read all users from Supabase auth.users
        result = supabase_session.execute(SUPABASE_USERS_QUERY)
        rows = result.fetchall()

        logger.info(f"Found {len(rows)} users in Supabase auth.users")

        for idx, row in enumerate(rows):
            report.total_processed += 1

            supabase_email = row.email
            supabase_password = row.encrypted_password
            supabase_meta = row.raw_user_meta_data or {}

            # Skip if email is somehow null (shouldn't happen due to WHERE clause)
            if not supabase_email:
                report.total_skipped_null_email += 1
                report.skipped_ids.append(str(row.id))
                continue

            # Check if email already exists in unified users table
            existing_user = user_exists_by_email(target_session, supabase_email)

            if existing_user:
                # MERGE: add marketplace enrollment to existing user
                user_id = existing_user.id
                report.conflicts.append(
                    f"Email conflict: {supabase_email} (supabase {row.id}) → merged into user {user_id}"
                )
                logger.info(f"Merging Supabase user {row.id} into existing user {user_id} ({supabase_email})")
            else:
                # Create new user
                user_id = uuid.uuid4()

                # Determine password_hash
                # Supabase uses bcrypt — same format as skawr-auth, so we can reuse directly.
                # OAuth-only users have empty or null encrypted_password.
                password_hash = None
                if supabase_password and supabase_password.strip():
                    password_hash = supabase_password

                # Extract name from metadata if available
                name = supabase_meta.get("full_name") or supabase_meta.get("name")

                new_user = User(
                    id=user_id,
                    email=supabase_email,
                    password_hash=password_hash,
                    name=name,
                    is_active=True,
                )
                target_session.add(new_user)
                report.total_migrated += 1

            # Create ProductEnrollment if not exists
            if not enrollment_exists(target_session, user_id, PRODUCT):
                enrollment = ProductEnrollment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    product=PRODUCT,
                    role=DEFAULT_ROLE,
                    is_active=True,
                )
                target_session.add(enrollment)
                report.total_enrollments_created += 1

            # Commit in batches of 100 for performance
            if (idx + 1) % 100 == 0:
                target_session.commit()
                logger.info(f"Committed batch {(idx + 1) // 100} — {report.total_migrated} users created so far")

        # Final commit
        target_session.commit()
        logger.info("Migration complete")

    except Exception as e:
        target_session.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        supabase_session.close()
        target_session.close()

    return report


def main():
    supabase_url = os.environ.get("SUPABASE_DATABASE_URL")
    target_url = os.environ.get("SKAWR_AUTH_DATABASE_URL")

    if not supabase_url:
        print("ERROR: SUPABASE_DATABASE_URL environment variable is required")
        sys.exit(1)

    if not target_url:
        print("ERROR: SKAWR_AUTH_DATABASE_URL environment variable is required")
        sys.exit(1)

    print(f"Starting marketplace Supabase migration...")
    print(f"Source (Supabase): {supabase_url.split('@')[-1] if '@' in supabase_url else '(masked)'}")
    print(f"Target (Auth):     {target_url.split('@')[-1] if '@' in target_url else '(masked)'}")

    report = run_migration(supabase_url, target_url)
    report.print_summary()


if __name__ == "__main__":
    main()
