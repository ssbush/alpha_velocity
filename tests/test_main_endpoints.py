"""
Tests for main.py API endpoints via TestClient.

Covers legacy (root-level) endpoints that don't require external
services (yfinance, PostgreSQL).
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


class TestHealthCheck:
    """Tests for GET / health endpoint."""

    def test_root_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "AlphaVelocity API is running"
        assert "version" in data


class TestCacheEndpoints:
    """Tests for cache management endpoints."""

    def test_cache_status(self):
        resp = client.get("/cache/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "cache_stats" in data
        assert "message" in data

    def test_cache_clear(self):
        resp = client.post("/cache/clear")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "cleared" in data["message"].lower() or "Cache" in data["message"]


class TestMomentumEndpoints:
    """Tests for momentum endpoints — validation error paths."""

    def test_invalid_ticker_too_long(self):
        resp = client.get("/momentum/TOOLONG12345")
        assert resp.status_code == 400

    def test_invalid_ticker_special_chars(self):
        resp = client.get("/momentum/A@BC")
        assert resp.status_code == 400

    def test_invalid_ticker_empty(self):
        resp = client.get("/momentum/ ")
        # Should redirect or return 404/400
        assert resp.status_code in (307, 400, 404, 422)


class TestPortfolioEndpoints:
    """Tests for portfolio endpoints — error paths."""

    def test_analyze_custom_empty_portfolio(self):
        resp = client.post("/portfolio/analyze", json={"holdings": {}})
        assert resp.status_code == 400

    def test_analyze_custom_missing_holdings(self):
        resp = client.post("/portfolio/analyze", json={})
        assert resp.status_code in (400, 422)


class TestCategoryEndpoints:
    """Tests for category endpoints."""

    def test_get_categories(self):
        resp = client.get("/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_category_tickers_not_found(self):
        resp = client.get("/categories/NONEXISTENT_CATEGORY_XYZ/tickers")
        assert resp.status_code == 404

    def test_get_category_analysis_not_found(self):
        resp = client.get("/categories/NONEXISTENT_CATEGORY_XYZ/analysis")
        assert resp.status_code in (404, 500)


class TestTopMomentum:
    """Tests for top momentum endpoint — error paths."""

    def test_top_momentum_invalid_limit_zero(self):
        resp = client.get("/momentum/top/0")
        assert resp.status_code == 400

    def test_top_momentum_invalid_limit_negative(self):
        resp = client.get("/momentum/top/-1")
        assert resp.status_code in (400, 422)


class TestWatchlistEndpoints:
    """Tests for watchlist endpoints — error paths."""

    def test_custom_watchlist_empty_portfolio(self):
        resp = client.post("/watchlist/custom", json={"holdings": {}})
        assert resp.status_code == 400


class TestDatabaseStatus:
    """Tests for database status endpoint."""

    def test_database_status_returns_json(self):
        resp = client.get("/database/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "available" in data


class TestHistoricalEndpoints:
    """Tests for historical endpoints."""

    def test_set_portfolio_id(self):
        resp = client.post("/historical/portfolio/test-portfolio-123/set-id")
        assert resp.status_code == 200
        data = resp.json()
        assert "test-portfolio-123" in data["message"]

    def test_cleanup_historical(self):
        resp = client.post("/historical/cleanup?days_to_keep=365")
        assert resp.status_code == 200
        data = resp.json()
        assert "365" in data["message"]


class TestDailyCacheEndpoints:
    """Tests for daily cache management endpoints."""

    def test_daily_cache_status(self):
        resp = client.get("/cache/daily/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "cache_stats" in data or "scheduler_status" in data

    def test_daily_start_scheduler(self):
        resp = client.post("/cache/daily/start")
        assert resp.status_code == 200

    def test_daily_stop_scheduler(self):
        resp = client.post("/cache/daily/stop")
        assert resp.status_code == 200


class TestDatabaseEndpointsWithoutDB:
    """Test database-dependent endpoints return 503 when DB is unavailable."""

    def test_get_portfolios_no_db(self):
        from backend.main import DATABASE_AVAILABLE
        if not DATABASE_AVAILABLE:
            resp = client.get("/database/portfolios?user_id=1")
            assert resp.status_code == 503

    def test_get_holdings_no_db(self):
        from backend.main import DATABASE_AVAILABLE
        if not DATABASE_AVAILABLE:
            resp = client.get("/database/portfolio/1/holdings")
            assert resp.status_code == 503

    def test_get_categories_db_no_db(self):
        from backend.main import DATABASE_AVAILABLE
        if not DATABASE_AVAILABLE:
            resp = client.get("/database/portfolio/1/categories")
            assert resp.status_code == 503

    def test_get_transactions_no_db(self):
        from backend.main import DATABASE_AVAILABLE
        if not DATABASE_AVAILABLE:
            resp = client.get("/database/portfolio/1/transactions")
            assert resp.status_code == 503

    def test_record_snapshot_no_db(self):
        from backend.main import DATABASE_AVAILABLE
        if not DATABASE_AVAILABLE:
            resp = client.post("/database/portfolio/1/snapshot")
            assert resp.status_code == 503

    def test_get_performance_no_db(self):
        from backend.main import DATABASE_AVAILABLE
        if not DATABASE_AVAILABLE:
            resp = client.get("/database/portfolio/1/performance")
            assert resp.status_code == 503

    def test_update_momentum_no_db(self):
        from backend.main import DATABASE_AVAILABLE
        if not DATABASE_AVAILABLE:
            resp = client.post("/database/portfolio/1/update-momentum")
            assert resp.status_code == 503

    def test_migrate_no_db(self):
        from backend.main import DATABASE_AVAILABLE
        if not DATABASE_AVAILABLE:
            resp = client.post("/database/migrate")
            assert resp.status_code == 503


class TestCategoryManagement:
    """Tests for category management endpoints — error paths."""

    def test_create_category_invalid_allocation(self):
        resp = client.post(
            "/categories/management/create",
            params={
                "name": "Test",
                "description": "Test desc",
                "target_allocation_pct": 150.0,
                "benchmark_ticker": "SPY",
            },
        )
        assert resp.status_code == 400

    def test_add_ticker_invalid(self):
        resp = client.post(
            "/categories/management/1/tickers",
            params={"ticker": ""},
        )
        assert resp.status_code == 400


class TestCompareEndpoints:
    """Tests for portfolio comparison — error paths."""

    def test_compare_model_vs_custom_invalid_json(self):
        resp = client.get("/compare/model-vs-custom?custom_portfolio=not-json")
        assert resp.status_code == 400
