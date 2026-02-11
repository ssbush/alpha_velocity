"""
Tests for Deprecation Middleware

Verifies that legacy (unversioned) endpoints receive RFC 8594 deprecation
headers, while v1 and non-deprecated endpoints do not.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.config.deprecation_config import get_deprecated_route_info

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unit tests for get_deprecated_route_info
# ---------------------------------------------------------------------------

class TestGetDeprecatedRouteInfo:
    """Unit tests for the route-matching helper."""

    def test_momentum_ticker(self):
        assert get_deprecated_route_info("/momentum/NVDA") == "/api/v1/momentum/NVDA"

    def test_momentum_top(self):
        assert get_deprecated_route_info("/momentum/top/10") == "/api/v1/momentum/top/10"

    def test_portfolio_analysis(self):
        assert get_deprecated_route_info("/portfolio/analysis") == "/api/v1/portfolio/analysis"

    def test_portfolio_analyze(self):
        assert get_deprecated_route_info("/portfolio/analyze") == "/api/v1/portfolio/analyze"

    def test_portfolio_analysis_by_categories(self):
        assert get_deprecated_route_info("/portfolio/analysis/by-categories") == "/api/v1/portfolio/analysis/by-categories"

    def test_portfolio_analyze_by_categories(self):
        assert get_deprecated_route_info("/portfolio/analyze/by-categories") == "/api/v1/portfolio/analyze/by-categories"

    def test_categories_exact(self):
        assert get_deprecated_route_info("/categories") == "/api/v1/categories"

    def test_categories_analysis(self):
        assert get_deprecated_route_info("/categories/tech/analysis") == "/api/v1/categories/tech/analysis"

    def test_categories_tickers(self):
        assert get_deprecated_route_info("/categories/tech/tickers") == "/api/v1/categories/tech/tickers"

    def test_cache_status(self):
        assert get_deprecated_route_info("/cache/status") == "/api/v1/cache/status"

    def test_cache_clear(self):
        assert get_deprecated_route_info("/cache/clear") == "/api/v1/cache/clear"

    def test_trailing_slash_stripped(self):
        assert get_deprecated_route_info("/categories/") == "/api/v1/categories"

    def test_v1_path_not_deprecated(self):
        assert get_deprecated_route_info("/api/v1/momentum/NVDA") is None

    def test_root_not_deprecated(self):
        assert get_deprecated_route_info("/") is None

    def test_auth_not_deprecated(self):
        assert get_deprecated_route_info("/auth/login") is None

    def test_categories_management_not_deprecated(self):
        assert get_deprecated_route_info("/categories/management/something") is None

    def test_docs_not_deprecated(self):
        assert get_deprecated_route_info("/docs") is None


# ---------------------------------------------------------------------------
# Integration tests — headers on actual responses
# ---------------------------------------------------------------------------

class TestDeprecationHeaders:
    """Integration tests verifying deprecation headers on HTTP responses."""

    def test_legacy_endpoint_has_deprecation_header(self):
        """Legacy endpoint should have Deprecation: true header."""
        response = client.get("/categories")
        assert response.headers.get("Deprecation") == "true"

    def test_legacy_endpoint_has_link_header(self):
        """Legacy endpoint should have Link header pointing to v1."""
        response = client.get("/categories")
        assert response.headers.get("Link") == '</api/v1/categories>; rel="successor-version"'

    def test_legacy_endpoint_has_sunset_header(self):
        """Legacy endpoint should have Sunset header when configured."""
        response = client.get("/categories")
        assert "Sunset" in response.headers

    def test_legacy_cache_status_deprecated(self):
        """Legacy /cache/status should have deprecation headers."""
        response = client.get("/cache/status")
        assert response.headers.get("Deprecation") == "true"
        assert response.headers.get("Link") == '</api/v1/cache/status>; rel="successor-version"'

    def test_v1_endpoint_no_deprecation_header(self):
        """V1 endpoints should NOT have deprecation headers."""
        response = client.get("/api/v1/categories")
        assert "Deprecation" not in response.headers
        assert "Sunset" not in response.headers

    def test_root_no_deprecation_header(self):
        """Root health check should NOT have deprecation headers."""
        response = client.get("/")
        assert "Deprecation" not in response.headers

    def test_auth_no_deprecation_header(self):
        """Auth endpoints should NOT have deprecation headers."""
        response = client.post("/auth/login", json={"username": "x", "password": "y"})
        assert "Deprecation" not in response.headers

    def test_sunset_header_absent_when_not_configured(self):
        """Sunset header should be absent when SUNSET_DATE is None."""
        with patch("backend.middleware.deprecation_middleware.SUNSET_DATE", None):
            response = client.get("/categories")
            assert response.headers.get("Deprecation") == "true"
            assert "Sunset" not in response.headers
