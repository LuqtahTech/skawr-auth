"""
Migrate SaaS APIClients to unified auth.

Reads from the `api_clients` table and creates:
1. Unified user records (if email is non-null and not already in users table)
2. ProductEnrollment (product=search_saas, role=admin)
3. ConnectedStore records (for Salla/Shopify OAuth data)

Guest clients (is_guest=true, null email) are SKIPPED.
Email conflicts are resolved by MERGE (add enrollment to existing user).

The script is idempotent — if records already exist they are skipped.

Usage:
    SKAWR_AUTH_DATABASE_URL=postgresql://... python -m skawr_auth.migrations.migrate_saas_apiclients
"""

import logging
import os
import sys
import uuid
from datetime import datetime

from sqlalchemy import text

from skawr_auth.migrations.utils import (
    MigrationReport,
    enrollment_exists,
    get_db_session,
    user_exists_by_email,
)
from skawr_auth.models.connected_store import ConnectedStore
from skawr_auth.models.enrollment import ProductEnrollment
from skawr_auth.models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PRODUCT = "search_saas"
DEFAULT_ROLE = "admin"

# Raw SQL to read api_clients (since we can't import indexer models directly)
API_CLIENTS_QUERY = text(
    "SELECT id, name, email, hashed_password, is_active, is_guest, "
    "salla_store_id, salla_store_url, salla_store_email, "
    "salla_access_token, salla_refresh_token, salla_token_expires_at, "
    "salla_subscription_status, salla_subscription_tier, salla_settings, "
    "shopify_shop_id, shopify_shop_domain, shopify_shop_email, "
    "shopify_access_token, shopify_scope, shopify_settings, "
    "created_at, updated_at FROM api_clients"
)


def run_migration(database_url: str) -> MigrationReport:
    """Run the SaaS APIClient migration.

    Creates unified user records, enrollments, and connected_store records
    from the legacy api_clients table.
    """
    report = MigrationReport(source="saas_apiclients")
    session = get_db_session(database_url)

    try:
        # Read all api_clients using raw SQL
        result = session.execute(API_CLIENTS_QUERY)
        rows = result.fetchall()

        logger.info(f"Found {len(rows)} API clients in the database")

        for idx, row in enumerate(rows):
            report.total_processed += 1

            client_id = row.id
            client_email = row.email
            client_name = row.name
            client_password_hash = row.hashed_password
            is_guest = row.is_guest

            # Skip guest clients (null email or is_guest=true)
            if is_guest or not client_email:
                report.total_skipped_null_email += 1
                report.skipped_ids.append(str(client_id))
                logger.debug(f"Skipping guest/null-email client {client_id}")
                continue

            # Check if email already exists in users table
            existing_user = user_exists_by_email(session, client_email)

            if existing_user:
                # MERGE: add search_saas enrollment to existing user
                user_id = existing_user.id
                report.conflicts.append(
                    f"Email conflict: {client_email} (client {client_id}) → merged into user {user_id}"
                )
                logger.info(f"Merging client {client_id} into existing user {user_id} ({client_email})")
            else:
                # Create new user
                user_id = uuid.uuid4()
                new_user = User(
                    id=user_id,
                    email=client_email,
                    password_hash=client_password_hash,
                    name=client_name,
                    is_active=row.is_active if row.is_active is not None else True,
                )
                session.add(new_user)
                report.total_migrated += 1

            # Create ProductEnrollment if not exists
            if not enrollment_exists(session, user_id, PRODUCT):
                enrollment = ProductEnrollment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    product=PRODUCT,
                    role=DEFAULT_ROLE,
                    is_active=True,
                )
                session.add(enrollment)
                report.total_enrollments_created += 1

            # Create ConnectedStore for Salla if salla_store_id is set
            if row.salla_store_id:
                _create_salla_store(session, report, user_id, client_id, row)

            # Create ConnectedStore for Shopify if shopify_shop_id is set
            if row.shopify_shop_id:
                _create_shopify_store(session, report, user_id, client_id, row)

            # Commit in batches of 100 for performance
            if (idx + 1) % 100 == 0:
                session.commit()
                logger.info(f"Committed batch {(idx + 1) // 100} — {report.total_migrated} users created so far")

        # Final commit
        session.commit()
        logger.info("Migration complete")

    except Exception as e:
        session.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        session.close()

    return report


def _create_salla_store(session, report: MigrationReport, user_id, client_id, row):
    """Create a ConnectedStore record for Salla platform data."""
    from sqlalchemy import select

    # Check if this connected store already exists (by legacy_client_id or platform+store_id)
    existing = session.execute(
        select(ConnectedStore).where(
            ConnectedStore.legacy_client_id == client_id
        )
    ).scalar_one_or_none()

    if existing:
        logger.debug(f"Connected store already exists for client {client_id} (Salla)")
        return

    # Also check by platform + store_id uniqueness
    existing_by_platform = session.execute(
        select(ConnectedStore).where(
            ConnectedStore.platform == "salla",
            ConnectedStore.platform_store_id == str(row.salla_store_id),
        )
    ).scalar_one_or_none()

    if existing_by_platform:
        logger.debug(f"Connected store already exists for Salla store {row.salla_store_id}")
        return

    store = ConnectedStore(
        id=uuid.uuid4(),
        user_id=user_id,
        platform="salla",
        platform_store_id=str(row.salla_store_id),
        platform_store_url=row.salla_store_url,
        platform_email=row.salla_store_email,
        access_token=row.salla_access_token,
        refresh_token=row.salla_refresh_token,
        token_expires_at=row.salla_token_expires_at,
        subscription_status=row.salla_subscription_status,
        subscription_tier=row.salla_subscription_tier,
        settings=row.salla_settings,
        legacy_client_id=client_id,
    )
    session.add(store)
    report.total_connected_stores_created += 1


def _create_shopify_store(session, report: MigrationReport, user_id, client_id, row):
    """Create a ConnectedStore record for Shopify platform data."""
    from sqlalchemy import select

    # Check if store already exists by platform + store_id
    existing = session.execute(
        select(ConnectedStore).where(
            ConnectedStore.platform == "shopify",
            ConnectedStore.platform_store_id == str(row.shopify_shop_id),
        )
    ).scalar_one_or_none()

    if existing:
        logger.debug(f"Connected store already exists for Shopify shop {row.shopify_shop_id}")
        return

    store = ConnectedStore(
        id=uuid.uuid4(),
        user_id=user_id,
        platform="shopify",
        platform_store_id=str(row.shopify_shop_id),
        platform_store_url=row.shopify_shop_domain,
        platform_email=row.shopify_shop_email,
        access_token=row.shopify_access_token,
        oauth_scope=row.shopify_scope,
        settings=row.shopify_settings,
        legacy_client_id=client_id,
    )
    session.add(store)
    report.total_connected_stores_created += 1


def main():
    database_url = os.environ.get("SKAWR_AUTH_DATABASE_URL")
    if not database_url:
        print("ERROR: SKAWR_AUTH_DATABASE_URL environment variable is required")
        sys.exit(1)

    print(f"Starting SaaS APIClient migration...")
    print(f"Database: {database_url.split('@')[-1] if '@' in database_url else '(masked)'}")

    report = run_migration(database_url)
    report.print_summary()


if __name__ == "__main__":
    main()
