"""
Tests for Paginated Historical Data API Endpoints (v1).

Covers /api/v1/historical/momentum/{ticker},
       /api/v1/historical/portfolio/{portfolio_id},
       /api/v1/historical/top-performers
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_momentum_entries(count=5, base_score=70.0, trend=2.0):
    """Generate mock momentum history entries."""
    entries = []
    base_time = datetime.now() - timedelta(days=count)
    for i in range(count):
        entries.append({
            "timestamp": (base_time + timedelta(days=i)).isoformat(),
            "composite_score": base_score + (i * trend),
            "rating": "Buy" if base_score + (i * trend) >= 70 else "Hold",
            "price_momentum": 65.0 + i,
            "technical_momentum": 60.0 + i,
            "fundamental_momentum": 55.0 + i,
            "relative_momentum": 50.0 + i,
        })
    return entries


def _make_portfolio_values(count=5, base_value=100000):
    """Generate mock portfolio value entries."""
    entries = []
    base_time = datetime.now() - timedelta(days=count)
    for i in range(count):
        entries.append({
            "timestamp": (base_time + timedelta(days=i)).isoformat(),
            "total_value": base_value + (i * 1000),
            "average_momentum_score": 70.0 + i,
            "number_of_positions": 10,
        })
    return entries


# ============================================================================
# GET /api/v1/historical/momentum/{ticker}
# ============================================================================


class TestMomentumHistoryPaginated:
    """Tests for GET /api/v1/historical/momentum/{ticker}."""

    @patch("backend.api.v1.historical.historical_service")
    def test_basic_request(self, mock_service, client):
        entries = _make_momentum_entries(5)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "NVDA"
        assert "items" in data
        assert "metadata" in data
        assert data["metadata"]["total_items"] == 5

    @patch("backend.api.v1.historical.historical_service")
    def test_empty_history(self, mock_service, client):
        mock_service.get_momentum_history.return_value = []

        resp = client.get("/api/v1/historical/momentum/FAKE")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["trend"] == "neutral"
        assert data["current_score"] == 0
        assert data["metadata"]["total_items"] == 0

    @patch("backend.api.v1.historical.historical_service")
    def test_pagination_page_size(self, mock_service, client):
        entries = _make_momentum_entries(10)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA?page=1&page_size=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["metadata"]["total_items"] == 10
        assert data["metadata"]["total_pages"] == 4
        assert data["metadata"]["has_next"] is True
        assert data["metadata"]["has_previous"] is False

    @patch("backend.api.v1.historical.historical_service")
    def test_pagination_page_2(self, mock_service, client):
        entries = _make_momentum_entries(10)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA?page=2&page_size=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["metadata"]["page"] == 2
        assert data["metadata"]["has_previous"] is True
        assert data["metadata"]["has_next"] is True

    @patch("backend.api.v1.historical.historical_service")
    def test_sort_order_desc(self, mock_service, client):
        entries = _make_momentum_entries(5)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA?sort_order=desc")
        assert resp.status_code == 200
        data = resp.json()
        items = data["items"]
        if len(items) >= 2:
            assert items[0]["timestamp"] >= items[1]["timestamp"]

    @patch("backend.api.v1.historical.historical_service")
    def test_sort_order_asc(self, mock_service, client):
        entries = _make_momentum_entries(5)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA?sort_order=asc")
        assert resp.status_code == 200
        data = resp.json()
        items = data["items"]
        if len(items) >= 2:
            assert items[0]["timestamp"] <= items[1]["timestamp"]

    @patch("backend.api.v1.historical.historical_service")
    def test_trend_improving(self, mock_service, client):
        entries = _make_momentum_entries(5, base_score=60, trend=5)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trend"] == "improving"
        assert data["score_change"] > 5

    @patch("backend.api.v1.historical.historical_service")
    def test_trend_declining(self, mock_service, client):
        entries = _make_momentum_entries(5, base_score=80, trend=-5)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trend"] == "declining"
        assert data["score_change"] < -5

    @patch("backend.api.v1.historical.historical_service")
    def test_trend_stable(self, mock_service, client):
        entries = _make_momentum_entries(5, base_score=70, trend=0.5)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trend"] == "stable"

    @patch("backend.api.v1.historical.historical_service")
    def test_single_entry(self, mock_service, client):
        entries = _make_momentum_entries(1)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["trend"] == "neutral"
        assert data["score_change"] == 0

    @patch("backend.api.v1.historical.historical_service")
    def test_page_beyond_range(self, mock_service, client):
        entries = _make_momentum_entries(3)
        mock_service.get_momentum_history.return_value = entries

        resp = client.get("/api/v1/historical/momentum/NVDA?page=100&page_size=20")
        assert resp.status_code == 200
        data = resp.json()
        # paginate() clamps page to last page
        assert data["metadata"]["page"] == 1
        assert len(data["items"]) == 3

    @patch("backend.api.v1.historical.historical_service")
    def test_days_param_passed(self, mock_service, client):
        mock_service.get_momentum_history.return_value = []

        resp = client.get("/api/v1/historical/momentum/NVDA?days=60")
        assert resp.status_code == 200
        mock_service.get_momentum_history.assert_called_once_with("NVDA", 60)

    def test_invalid_page_zero(self, client):
        resp = client.get("/api/v1/historical/momentum/NVDA?page=0")
        assert resp.status_code in (400, 422)

    def test_invalid_page_size_over_limit(self, client):
        resp = client.get("/api/v1/historical/momentum/NVDA?page_size=200")
        assert resp.status_code in (400, 422)


# ============================================================================
# GET /api/v1/historical/portfolio/{portfolio_id}
# ============================================================================


class TestPortfolioHistoryPaginated:
    """Tests for GET /api/v1/historical/portfolio/{portfolio_id}."""

    @patch("backend.api.v1.historical.historical_service")
    def test_basic_request(self, mock_service, client):
        values = _make_portfolio_values(5)
        mock_service.get_portfolio_history.return_value = {"values": values, "compositions": []}
        mock_service.get_performance_analytics.return_value = {"total_return": 5.0}

        resp = client.get("/api/v1/historical/portfolio/default")
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio_id"] == "default"
        assert "items" in data
        assert "metadata" in data
        assert "analytics" in data
        assert data["metadata"]["total_items"] == 5

    @patch("backend.api.v1.historical.historical_service")
    def test_empty_portfolio_history(self, mock_service, client):
        mock_service.get_portfolio_history.return_value = {"values": [], "compositions": []}
        mock_service.get_performance_analytics.return_value = {}

        resp = client.get("/api/v1/historical/portfolio/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["metadata"]["total_items"] == 0

    @patch("backend.api.v1.historical.historical_service")
    def test_pagination(self, mock_service, client):
        values = _make_portfolio_values(10)
        mock_service.get_portfolio_history.return_value = {"values": values, "compositions": []}
        mock_service.get_performance_analytics.return_value = {}

        resp = client.get("/api/v1/historical/portfolio/default?page=2&page_size=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["metadata"]["page"] == 2
        assert data["metadata"]["total_pages"] == 4

    @patch("backend.api.v1.historical.historical_service")
    def test_analytics_included(self, mock_service, client):
        values = _make_portfolio_values(3)
        analytics = {
            "total_return": 5.0,
            "volatility": 2.1,
            "sharpe_ratio": 1.5,
            "momentum_trend": "improving",
        }
        mock_service.get_portfolio_history.return_value = {"values": values, "compositions": []}
        mock_service.get_performance_analytics.return_value = analytics

        resp = client.get("/api/v1/historical/portfolio/default")
        assert resp.status_code == 200
        data = resp.json()
        assert data["analytics"]["total_return"] == 5.0
        assert data["analytics"]["momentum_trend"] == "improving"

    @patch("backend.api.v1.historical.historical_service")
    def test_days_param(self, mock_service, client):
        mock_service.get_portfolio_history.return_value = {"values": [], "compositions": []}
        mock_service.get_performance_analytics.return_value = {}

        resp = client.get("/api/v1/historical/portfolio/default?days=90")
        assert resp.status_code == 200
        mock_service.get_portfolio_history.assert_called_once_with("default", 90)
        mock_service.get_performance_analytics.assert_called_once_with("default", 90)


# ============================================================================
# GET /api/v1/historical/top-performers
# ============================================================================


class TestTopPerformersPaginated:
    """Tests for GET /api/v1/historical/top-performers."""

    @patch("backend.api.v1.historical._get_all_performers")
    def test_basic_request(self, mock_performers, client):
        performers = [
            {"ticker": "NVDA", "improvement": 10.0, "latest_score": 85},
            {"ticker": "MSFT", "improvement": 5.0, "latest_score": 75},
        ]
        mock_performers.return_value = performers

        resp = client.get("/api/v1/historical/top-performers")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "metadata" in data
        assert data["period_days"] == 7
        assert len(data["items"]) == 2

    @patch("backend.api.v1.historical._get_all_performers")
    def test_empty_performers(self, mock_performers, client):
        mock_performers.return_value = []

        resp = client.get("/api/v1/historical/top-performers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["metadata"]["total_items"] == 0

    @patch("backend.api.v1.historical._get_all_performers")
    def test_pagination(self, mock_performers, client):
        performers = [{"ticker": f"T{i}", "improvement": 10 - i} for i in range(15)]
        mock_performers.return_value = performers

        resp = client.get("/api/v1/historical/top-performers?page=2&page_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 5
        assert data["metadata"]["page"] == 2
        assert data["metadata"]["total_pages"] == 3

    @patch("backend.api.v1.historical._get_all_performers")
    def test_custom_days(self, mock_performers, client):
        mock_performers.return_value = []

        resp = client.get("/api/v1/historical/top-performers?days=30")
        assert resp.status_code == 200
        mock_performers.assert_called_once_with(30)

    @patch("backend.api.v1.historical._get_all_performers")
    def test_page_beyond_range(self, mock_performers, client):
        performers = [{"ticker": "NVDA", "improvement": 5.0}]
        mock_performers.return_value = performers

        resp = client.get("/api/v1/historical/top-performers?page=100&page_size=20")
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadata"]["page"] == 1
        assert len(data["items"]) == 1
