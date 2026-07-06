"""Tests for utils/roles.py — Product/Role enums, hierarchy, and require_product_role dependency."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from skawr_auth.utils.roles import (
    Product,
    Role,
    ROLE_HIERARCHY,
    role_meets_minimum,
    require_product_role,
)


class TestProductEnum:
    """Tests for Product enum."""

    def test_product_values(self):
        assert Product.ANALYTICS == "analytics"
        assert Product.SEARCH_SAAS == "search_saas"
        assert Product.CLIENT_DASHBOARD == "client_dashboard"
        assert Product.ADMIN_DASHBOARD == "admin_dashboard"
        assert Product.MARKETPLACE == "marketplace"

    def test_product_is_string(self):
        assert isinstance(Product.ANALYTICS, str)
        assert isinstance(Product.SEARCH_SAAS, str)

    def test_product_count(self):
        assert len(Product) == 5


class TestRoleEnum:
    """Tests for Role enum."""

    def test_role_values(self):
        assert Role.ADMIN == "admin"
        assert Role.MEMBER == "member"
        assert Role.VIEWER == "viewer"

    def test_role_is_string(self):
        assert isinstance(Role.ADMIN, str)

    def test_role_count(self):
        assert len(Role) == 3


class TestRoleHierarchy:
    """Tests for ROLE_HIERARCHY dict."""

    def test_admin_highest(self):
        assert ROLE_HIERARCHY["admin"] == 3

    def test_member_middle(self):
        assert ROLE_HIERARCHY["member"] == 2

    def test_viewer_lowest(self):
        assert ROLE_HIERARCHY["viewer"] == 1

    def test_admin_greater_than_member(self):
        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["member"]

    def test_member_greater_than_viewer(self):
        assert ROLE_HIERARCHY["member"] > ROLE_HIERARCHY["viewer"]


class TestRoleMeetsMinimum:
    """Tests for role_meets_minimum helper."""

    def test_admin_meets_admin(self):
        assert role_meets_minimum("admin", Role.ADMIN) is True

    def test_admin_meets_member(self):
        assert role_meets_minimum("admin", Role.MEMBER) is True

    def test_admin_meets_viewer(self):
        assert role_meets_minimum("admin", Role.VIEWER) is True

    def test_member_meets_member(self):
        assert role_meets_minimum("member", Role.MEMBER) is True

    def test_member_meets_viewer(self):
        assert role_meets_minimum("member", Role.VIEWER) is True

    def test_member_does_not_meet_admin(self):
        assert role_meets_minimum("member", Role.ADMIN) is False

    def test_viewer_meets_viewer(self):
        assert role_meets_minimum("viewer", Role.VIEWER) is True

    def test_viewer_does_not_meet_member(self):
        assert role_meets_minimum("viewer", Role.MEMBER) is False

    def test_viewer_does_not_meet_admin(self):
        assert role_meets_minimum("viewer", Role.ADMIN) is False

    def test_unknown_role_does_not_meet_viewer(self):
        assert role_meets_minimum("unknown_role", Role.VIEWER) is False

    def test_empty_string_does_not_meet_viewer(self):
        assert role_meets_minimum("", Role.VIEWER) is False


class TestRequireProductRole:
    """Tests for require_product_role dependency factory."""

    @pytest.mark.asyncio
    async def test_valid_token_with_sufficient_role(self):
        """User enrolled with admin role passes admin check."""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "type": "access",
            "product_enrollments": [
                {"product": "analytics", "role": "admin"},
            ],
        }
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
        dep = require_product_role(Product.ANALYTICS, Role.ADMIN)

        with patch("skawr_auth.utils.roles.verify_token", return_value=payload):
            result = await dep(credentials)
            assert result == "admin"

    @pytest.mark.asyncio
    async def test_member_passes_viewer_check(self):
        """Member role meets minimum of viewer."""
        payload = {
            "sub": "user-123",
            "product_enrollments": [
                {"product": "search_saas", "role": "member"},
            ],
        }
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
        dep = require_product_role(Product.SEARCH_SAAS, Role.VIEWER)

        with patch("skawr_auth.utils.roles.verify_token", return_value=payload):
            result = await dep(credentials)
            assert result == "member"

    @pytest.mark.asyncio
    async def test_viewer_fails_admin_check(self):
        """Viewer role does not meet admin minimum."""
        payload = {
            "sub": "user-123",
            "product_enrollments": [
                {"product": "analytics", "role": "viewer"},
            ],
        }
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
        dep = require_product_role(Product.ANALYTICS, Role.ADMIN)

        with patch("skawr_auth.utils.roles.verify_token", return_value=payload):
            with pytest.raises(HTTPException) as exc_info:
                await dep(credentials)
            assert exc_info.value.status_code == 403
            assert "Insufficient role" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_not_enrolled_raises_403(self):
        """User without enrollment in the product gets 403."""
        payload = {
            "sub": "user-123",
            "product_enrollments": [
                {"product": "analytics", "role": "admin"},
            ],
        }
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
        dep = require_product_role(Product.MARKETPLACE, Role.VIEWER)

        with patch("skawr_auth.utils.roles.verify_token", return_value=payload):
            with pytest.raises(HTTPException) as exc_info:
                await dep(credentials)
            assert exc_info.value.status_code == 403
            assert "Not enrolled" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """Invalid/expired token gets 401."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
        dep = require_product_role(Product.ANALYTICS, Role.VIEWER)

        with patch("skawr_auth.utils.roles.verify_token", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await dep(credentials)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_backward_compat_no_enrollments_grants_member(self):
        """Legacy token without product_enrollments treated as member everywhere."""
        payload = {
            "sub": "user-123",
            "email": "test@example.com",
            "type": "access",
        }
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="legacy-token")
        dep = require_product_role(Product.ANALYTICS, Role.VIEWER)

        with patch("skawr_auth.utils.roles.verify_token", return_value=payload):
            result = await dep(credentials)
            assert result == "member"

    @pytest.mark.asyncio
    async def test_backward_compat_member_fails_admin_check(self):
        """Legacy token (member) does not pass admin check."""
        payload = {
            "sub": "user-123",
            "type": "access",
        }
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="legacy-token")
        dep = require_product_role(Product.ANALYTICS, Role.ADMIN)

        with patch("skawr_auth.utils.roles.verify_token", return_value=payload):
            with pytest.raises(HTTPException) as exc_info:
                await dep(credentials)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_default_min_role_is_viewer(self):
        """When min_role not specified, defaults to VIEWER."""
        payload = {
            "sub": "user-123",
            "product_enrollments": [
                {"product": "analytics", "role": "viewer"},
            ],
        }
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
        dep = require_product_role(Product.ANALYTICS)  # No min_role → VIEWER

        with patch("skawr_auth.utils.roles.verify_token", return_value=payload):
            result = await dep(credentials)
            assert result == "viewer"

    @pytest.mark.asyncio
    async def test_multiple_enrollments_selects_correct_product(self):
        """With multiple enrollments, selects the correct product's role."""
        payload = {
            "sub": "user-123",
            "product_enrollments": [
                {"product": "analytics", "role": "admin"},
                {"product": "search_saas", "role": "viewer"},
                {"product": "marketplace", "role": "member"},
            ],
        }
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")

        # Check search_saas has viewer role
        dep = require_product_role(Product.SEARCH_SAAS, Role.VIEWER)
        with patch("skawr_auth.utils.roles.verify_token", return_value=payload):
            result = await dep(credentials)
            assert result == "viewer"

        # Viewer can't pass member check
        dep2 = require_product_role(Product.SEARCH_SAAS, Role.MEMBER)
        with patch("skawr_auth.utils.roles.verify_token", return_value=payload):
            with pytest.raises(HTTPException) as exc_info:
                await dep2(credentials)
            assert exc_info.value.status_code == 403
