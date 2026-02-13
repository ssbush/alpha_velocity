"""
Tests for API v1 Endpoints via TestClient.

Covers cache, cache_admin, metrics, and momentum v1 routes.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


class TestV1CacheEndpoints:
    """Tests for /api/v1/cache/ endpoints."""

    def test_cache_status(self):
        resp = client.get("/api/v1/cache/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] == "active"

    def test_cache_clear(self):
        resp = client.post("/api/v1/cache/clear")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data


class TestV1CacheAdminEndpoints:
    """Tests for /api/v1/cache/ admin endpoints."""

    def test_cache_info(self):
        resp = client.get("/api/v1/cache/info")
        assert resp.status_code == 200
        data = resp.json()
        assert "cache_type" in data
        assert "total_keys" in data

    def test_cache_keys_default(self):
        resp = client.get("/api/v1/cache/keys")
        assert resp.status_code == 200
        data = resp.json()
        assert "pattern" in data
        assert data["pattern"] == "*"
        assert "count" in data
        assert "keys" in data

    def test_cache_keys_with_pattern(self):
        resp = client.get("/api/v1/cache/keys?pattern=price:*")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pattern"] == "price:*"

    def test_cache_stats(self):
        resp = client.get("/api/v1/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "count" in data["total"]

    def test_cache_clear_delete_method(self):
        resp = client.request("DELETE", "/api/v1/cache/clear")
        assert resp.status_code == 200


class TestV1MetricsEndpoints:
    """Tests for /api/v1/metrics/ endpoints."""

    def test_performance_metrics_all(self):
        resp = client.get("/api/v1/metrics/performance")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    def test_performance_metrics_with_endpoint(self):
        resp = client.get("/api/v1/metrics/performance?endpoint=/")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data

    def test_reset_performance_with_endpoint(self):
        resp = client.request(
            "DELETE", "/api/v1/metrics/performance/reset?endpoint=/"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data


class TestV1MomentumValidation:
    """Tests for /api/v1/momentum/ validation paths."""

    def test_invalid_ticker(self):
        resp = client.get("/api/v1/momentum/TOOLONG12345")
        assert resp.status_code == 400

    def test_invalid_ticker_special(self):
        resp = client.get("/api/v1/momentum/X@Y")
        assert resp.status_code == 400

    def test_top_momentum_invalid_limit(self):
        resp = client.get("/api/v1/momentum/top/0")
        assert resp.status_code in (400, 422, 500)


class TestV1CategoriesEndpoints:
    """Tests for /api/v1/categories/ endpoints."""

    def test_list_categories(self):
        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Each category should have name and tickers
        first = data[0]
        assert "name" in first
        assert "tickers" in first

    def test_get_category_tickers(self):
        # First get a valid category name
        resp = client.get("/api/v1/categories")
        categories = resp.json()
        if categories:
            name = categories[0]["name"]
            resp2 = client.get(f"/api/v1/categories/{name}/tickers")
            assert resp2.status_code == 200
            data = resp2.json()
            assert "category" in data
            assert "tickers" in data
            assert "count" in data

    def test_get_nonexistent_category_tickers(self):
        resp = client.get("/api/v1/categories/NONEXISTENT_CATEGORY_XYZ/tickers")
        assert resp.status_code == 404


class TestV1PortfolioValidation:
    """Tests for /api/v1/portfolio/ validation paths."""

    def test_analyze_custom_empty_portfolio(self):
        resp = client.post("/api/v1/portfolio/analyze", json={"holdings": {}})
        assert resp.status_code == 400

    def test_analyze_custom_by_categories_empty(self):
        resp = client.post(
            "/api/v1/portfolio/analyze/by-categories",
            json={"holdings": {}},
        )
        assert resp.status_code == 400

    def test_analyze_custom_missing_body(self):
        resp = client.post("/api/v1/portfolio/analyze", json={})
        assert resp.status_code in (400, 422)


class TestV1MomentumBatchValidation:
    """Tests for /api/v1/momentum/batch validation paths."""

    def test_batch_empty_tickers(self):
        resp = client.post(
            "/api/v1/momentum/batch",
            json={"tickers": []},
        )
        assert resp.status_code in (400, 422)

    def test_batch_all_invalid_tickers(self):
        resp = client.post(
            "/api/v1/momentum/batch",
            json={"tickers": ["@@@", "!!!"]},
        )
        assert resp.status_code == 400

    def test_batch_top_empty_tickers(self):
        resp = client.post(
            "/api/v1/momentum/batch/top",
            json={"tickers": []},
        )
        assert resp.status_code in (400, 422)

    def test_batch_top_all_invalid(self):
        resp = client.post(
            "/api/v1/momentum/batch/top",
            json={"tickers": ["###"]},
        )
        assert resp.status_code == 400


class TestV1Init:
    """Tests for api/v1 __init__.py router inclusion."""

    def test_v1_routes_accessible(self):
        resp = client.get("/api/v1/cache/status")
        assert resp.status_code == 200

    def test_openapi_includes_v1(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        paths = data.get("paths", {})
        v1_paths = [p for p in paths if p.startswith("/api/v1/")]
        assert len(v1_paths) > 0
