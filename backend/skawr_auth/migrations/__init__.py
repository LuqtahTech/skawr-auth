"""Data migration scripts for unified auth.

These are NOT Alembic schema migrations. They are one-time data migration
scripts that move users from legacy systems into the unified auth model.

Each script is idempotent — safe to re-run without duplicating data.
"""
