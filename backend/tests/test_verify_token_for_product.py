"""Tests for verify_token_for_product() function."""

import os
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from skawr_auth.utils.auth import (
    create_access_token,
    verify_token_for_product,
)


# Use a fixed secret key for testing
TEST_SECRET = "test-secret-key-for-unit-tests"


class TestVerifyTokenForProductUnified:
    """Tests for unified token format (has product_enrollments)."""

    def test_returns_role_when_enrolled(self):
        """Unified token with matching product enrollment returns the role."""
        token = create_access_token(
            data={
                "sub": "user-123",
                "email": "user@example.com",
                "product_enrollments": [
                    {"product": "analytics", "role": "admin"},
                    {"product": "search_saas", "role": "member"},
                ],
            },
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result == "admin"

    def test_returns_correct_role_for_second_product(self):
        """Returns the correct role for a different enrolled product."""
        token = create_access_token(
            data={
                "sub": "user-123",
                "email": "user@example.com",
                "product_enrollments": [
                    {"product": "analytics", "role": "admin"},
                    {"product": "search_saas", "role": "viewer"},
                ],
            },
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "search_saas", secret_key=TEST_SECRET)
        assert result == "viewer"

    def test_returns_none_when_not_enrolled(self):
        """Unified token without enrollment for requested product returns None."""
        token = create_access_token(
            data={
                "sub": "user-123",
                "email": "user@example.com",
                "product_enrollments": [
                    {"product": "analytics", "role": "admin"},
                ],
            },
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "marketplace", secret_key=TEST_SECRET)
        assert result is None

    def test_returns_none_when_enrollments_empty(self):
        """Unified token with empty product_enrollments returns None."""
        token = create_access_token(
            data={
                "sub": "user-123",
                "email": "user@example.com",
                "product_enrollments": [],
            },
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result is None


class TestVerifyTokenForProductLegacyAnalytics:
    """Tests for legacy analytics format (sub only, no product_enrollments)."""

    def test_returns_member_role(self):
        """Legacy analytics token returns 'member' for any product."""
        token = create_access_token(
            data={
                "sub": "user-456",
                "email": "legacy@example.com",
            },
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result == "member"

    def test_returns_member_for_any_product(self):
        """Legacy analytics token returns 'member' regardless of product requested."""
        token = create_access_token(
            data={
                "sub": "user-456",
                "email": "legacy@example.com",
            },
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "search_saas", secret_key=TEST_SECRET)
        assert result == "member"

    def test_rejected_past_deadline(self):
        """Legacy analytics token is rejected when past the deadline."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        token = create_access_token(
            data={
                "sub": "user-456",
                "email": "legacy@example.com",
            },
            secret_key=TEST_SECRET,
        )
        with patch.dict(os.environ, {"SKAWR_AUTH_LEGACY_TOKEN_DEADLINE": yesterday}):
            result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result is None

    def test_accepted_before_deadline(self):
        """Legacy analytics token is accepted when before the deadline."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        token = create_access_token(
            data={
                "sub": "user-456",
                "email": "legacy@example.com",
            },
            secret_key=TEST_SECRET,
        )
        with patch.dict(os.environ, {"SKAWR_AUTH_LEGACY_TOKEN_DEADLINE": tomorrow}):
            result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result == "member"


class TestVerifyTokenForProductLegacyIndexer:
    """Tests for legacy indexer format (has client_id, no product_enrollments)."""

    def test_returns_admin_role(self):
        """Legacy indexer token returns 'admin'."""
        token = create_access_token(
            data={
                "sub": "user-789",
                "client_id": "client-abc-123",
            },
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "search_saas", secret_key=TEST_SECRET)
        assert result == "admin"

    def test_returns_admin_for_any_product(self):
        """Legacy indexer token returns 'admin' regardless of product requested."""
        token = create_access_token(
            data={
                "sub": "user-789",
                "client_id": "client-abc-123",
            },
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result == "admin"

    def test_rejected_past_deadline(self):
        """Legacy indexer token is rejected when past the deadline."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        token = create_access_token(
            data={
                "sub": "user-789",
                "client_id": "client-abc-123",
            },
            secret_key=TEST_SECRET,
        )
        with patch.dict(os.environ, {"SKAWR_AUTH_LEGACY_TOKEN_DEADLINE": yesterday}):
            result = verify_token_for_product(token, "search_saas", secret_key=TEST_SECRET)
        assert result is None

    def test_accepted_before_deadline(self):
        """Legacy indexer token is accepted when before the deadline."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        token = create_access_token(
            data={
                "sub": "user-789",
                "client_id": "client-abc-123",
            },
            secret_key=TEST_SECRET,
        )
        with patch.dict(os.environ, {"SKAWR_AUTH_LEGACY_TOKEN_DEADLINE": tomorrow}):
            result = verify_token_for_product(token, "search_saas", secret_key=TEST_SECRET)
        assert result == "admin"


class TestVerifyTokenForProductInvalidTokens:
    """Tests for invalid/malformed tokens."""

    def test_returns_none_for_invalid_token(self):
        """Garbage token string returns None."""
        result = verify_token_for_product("not-a-valid-jwt", "analytics", secret_key=TEST_SECRET)
        assert result is None

    def test_returns_none_for_wrong_secret(self):
        """Token signed with different secret returns None."""
        token = create_access_token(
            data={"sub": "user-123", "email": "test@example.com"},
            secret_key="different-secret",
        )
        result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result is None

    def test_returns_none_for_expired_token(self):
        """Expired token returns None."""
        from datetime import timedelta

        token = create_access_token(
            data={"sub": "user-123", "email": "test@example.com"},
            expires_delta=timedelta(seconds=-1),
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result is None

    def test_returns_none_for_unrecognizable_payload(self):
        """Token with no sub, client_id, or product_enrollments returns None."""
        # Manually create a token with a weird payload
        token = create_access_token(
            data={"random_field": "value"},
            secret_key=TEST_SECRET,
        )
        result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result is None


class TestVerifyTokenForProductDeadlineEdgeCases:
    """Tests for deadline edge cases."""

    def test_no_deadline_set_allows_legacy(self):
        """When SKAWR_AUTH_LEGACY_TOKEN_DEADLINE is not set, legacy tokens are accepted."""
        token = create_access_token(
            data={"sub": "user-123", "email": "test@example.com"},
            secret_key=TEST_SECRET,
        )
        with patch.dict(os.environ, {}, clear=False):
            # Ensure the env var is not set
            os.environ.pop("SKAWR_AUTH_LEGACY_TOKEN_DEADLINE", None)
            result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result == "member"

    def test_today_as_deadline_rejects_legacy(self):
        """When deadline is today, legacy tokens are NOT rejected (deadline < today is the check)."""
        today = date.today().isoformat()
        token = create_access_token(
            data={"sub": "user-123", "email": "test@example.com"},
            secret_key=TEST_SECRET,
        )
        with patch.dict(os.environ, {"SKAWR_AUTH_LEGACY_TOKEN_DEADLINE": today}):
            result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        # deadline < today — today is NOT < today, so it's still accepted
        assert result == "member"

    def test_invalid_deadline_format_allows_legacy(self):
        """Invalid deadline format in env var doesn't reject the token."""
        token = create_access_token(
            data={"sub": "user-123", "email": "test@example.com"},
            secret_key=TEST_SECRET,
        )
        with patch.dict(os.environ, {"SKAWR_AUTH_LEGACY_TOKEN_DEADLINE": "not-a-date"}):
            result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result == "member"

    def test_unified_token_ignores_deadline(self):
        """Unified tokens are NOT affected by the legacy deadline."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        token = create_access_token(
            data={
                "sub": "user-123",
                "email": "user@example.com",
                "product_enrollments": [
                    {"product": "analytics", "role": "admin"},
                ],
            },
            secret_key=TEST_SECRET,
        )
        with patch.dict(os.environ, {"SKAWR_AUTH_LEGACY_TOKEN_DEADLINE": yesterday}):
            result = verify_token_for_product(token, "analytics", secret_key=TEST_SECRET)
        assert result == "admin"
