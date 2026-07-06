"""Tests for detect_token_format() function."""

import pytest
from skawr_auth.utils.auth import detect_token_format


class TestDetectTokenFormat:
    """Tests for JWT token format detection logic."""

    def test_unified_format_with_product_enrollments(self):
        """Token with product_enrollments key is classified as unified."""
        payload = {
            "sub": "user-uuid-123",
            "email": "user@example.com",
            "product_enrollments": [
                {"product": "analytics", "role": "admin"},
                {"product": "search_saas", "role": "member"},
            ],
            "type": "access",
        }
        assert detect_token_format(payload) == "unified"

    def test_unified_format_with_empty_enrollments(self):
        """Token with product_enrollments (even empty list) is classified as unified."""
        payload = {
            "sub": "user-uuid-123",
            "email": "user@example.com",
            "product_enrollments": [],
            "type": "access",
        }
        assert detect_token_format(payload) == "unified"

    def test_unified_takes_precedence_over_client_id(self):
        """If both product_enrollments and client_id exist, unified wins."""
        payload = {
            "sub": "user-uuid-123",
            "client_id": "legacy-client-uuid",
            "product_enrollments": [{"product": "search_saas", "role": "admin"}],
            "type": "access",
        }
        assert detect_token_format(payload) == "unified"

    def test_legacy_indexer_format_with_client_id(self):
        """Token with client_id and no product_enrollments is legacy_indexer."""
        payload = {
            "sub": "user-uuid-123",
            "client_id": "client-uuid-456",
            "email": "client@example.com",
            "type": "access",
            "jti": "some-jti",
        }
        assert detect_token_format(payload) == "legacy_indexer"

    def test_legacy_analytics_format_with_sub_only(self):
        """Token with sub and neither client_id nor product_enrollments is legacy_analytics."""
        payload = {
            "sub": "user-uuid-123",
            "type": "access",
        }
        assert detect_token_format(payload) == "legacy_analytics"

    def test_legacy_analytics_with_email(self):
        """Token with sub and email but no client_id/product_enrollments is legacy_analytics."""
        payload = {
            "sub": "user-uuid-123",
            "email": "user@example.com",
            "type": "access",
            "iat": 1700000000,
            "exp": 1700000900,
        }
        assert detect_token_format(payload) == "legacy_analytics"

    def test_unrecognizable_format_raises_value_error(self):
        """Payload without sub, client_id, or product_enrollments raises ValueError."""
        payload = {
            "type": "access",
            "iat": 1700000000,
            "exp": 1700000900,
        }
        with pytest.raises(ValueError, match="Unrecognizable token format"):
            detect_token_format(payload)

    def test_empty_payload_raises_value_error(self):
        """Empty payload raises ValueError."""
        with pytest.raises(ValueError, match="Unrecognizable token format"):
            detect_token_format({})

    def test_payload_with_only_type_raises_value_error(self):
        """Payload with only type field raises ValueError."""
        payload = {"type": "access"}
        with pytest.raises(ValueError, match="Unrecognizable token format"):
            detect_token_format(payload)
