"""
Tests for Paginated Transaction History API Endpoints (v1).

Covers GET /api/v1/user/portfolios/{portfolio_id}/transactions
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.auth import create_access_token
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_header():
    """Create a valid auth header for testing."""
    token = create_access_token(user_id=1, username="testuser")
    return {"Authorization": f"Bearer {token}"}


def _make_transactions(count=5):
    """Generate mock transaction records."""
    txns = []
    for i in range(count):
        txns.append({
            "id": i + 1,
            "ticker": f"T{i % 3}",
            "transaction_type": "BUY" if i % 2 == 0 else "SELL",
            "transaction_date": f"2025-01-{10 + i:02d}",
            "shares": float(10 + i),
            "price_per_share": float(100.0 + i * 5),
            "total_amount": float((10 + i) * (100.0 + i * 5)),
            "fees": float(i * 0.5),
            "notes": f"Test txn {i}" if i % 2 == 0 else None,
        })
    return txns


# ============================================================================
# GET /api/v1/user/portfolios/{portfolio_id}/transactions
# ============================================================================


class TestTransactionsPaginated:
    """Tests for GET /api/v1/user/portfolios/{id}/transactions."""

    @patch("backend.api.v1.transactions._get_portfolio_service")
    def test_basic_request(self, mock_get_svc, client, auth_header):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_transactions.return_value = _make_transactions(5)
        mock_get_svc.return_value = mock_svc

        resp = client.get(
            "/api/v1/user/portfolios/1/transactions",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio_id"] == 1
        assert "items" in data
        assert "metadata" in data
        assert data["metadata"]["total_items"] == 5

    @patch("backend.api.v1.transactions._get_portfolio_service")
    def test_pagination(self, mock_get_svc, client, auth_header):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_transactions.return_value = _make_transactions(10)
        mock_get_svc.return_value = mock_svc

        resp = client.get(
            "/api/v1/user/portfolios/1/transactions?page=2&page_size=3",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["metadata"]["page"] == 2
        assert data["metadata"]["total_pages"] == 4
        assert data["metadata"]["has_next"] is True
        assert data["metadata"]["has_previous"] is True

    @patch("backend.api.v1.transactions._get_portfolio_service")
    def test_empty_transactions(self, mock_get_svc, client, auth_header):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_transactions.return_value = []
        mock_get_svc.return_value = mock_svc

        resp = client.get(
            "/api/v1/user/portfolios/1/transactions",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["metadata"]["total_items"] == 0

    @patch("backend.api.v1.transactions._get_portfolio_service")
    def test_sort_by_ticker(self, mock_get_svc, client, auth_header):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_transactions.return_value = _make_transactions(5)
        mock_get_svc.return_value = mock_svc

        resp = client.get(
            "/api/v1/user/portfolios/1/transactions?sort_by=ticker&sort_order=asc",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data["items"]
        if len(items) >= 2:
            assert items[0]["ticker"] <= items[1]["ticker"]

    @patch("backend.api.v1.transactions._get_portfolio_service")
    def test_sort_by_total_amount_desc(self, mock_get_svc, client, auth_header):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_transactions.return_value = _make_transactions(5)
        mock_get_svc.return_value = mock_svc

        resp = client.get(
            "/api/v1/user/portfolios/1/transactions?sort_by=total_amount&sort_order=desc",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data["items"]
        if len(items) >= 2:
            assert items[0]["total_amount"] >= items[1]["total_amount"]

    @patch("backend.api.v1.transactions._get_portfolio_service")
    def test_invalid_sort_field_defaults(self, mock_get_svc, client, auth_header):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_transactions.return_value = _make_transactions(3)
        mock_get_svc.return_value = mock_svc

        resp = client.get(
            "/api/v1/user/portfolios/1/transactions?sort_by=invalid_field",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3

    @patch("backend.api.v1.transactions._get_portfolio_service")
    def test_limit_none_passed_to_service(self, mock_get_svc, client, auth_header):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_transactions.return_value = []
        mock_get_svc.return_value = mock_svc

        resp = client.get(
            "/api/v1/user/portfolios/1/transactions",
            headers=auth_header,
        )
        assert resp.status_code == 200
        # Verify limit=None was passed (not the default 100)
        mock_svc.get_portfolio_transactions.assert_called_once_with(1, 1, limit=None)

    def test_unauthenticated_request(self, client):
        resp = client.get("/api/v1/user/portfolios/1/transactions")
        assert resp.status_code in (401, 403)

    def test_invalid_token(self, client):
        resp = client.get(
            "/api/v1/user/portfolios/1/transactions",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )
        assert resp.status_code in (401, 403)

    @patch("backend.api.v1.transactions._get_portfolio_service")
    def test_page_beyond_range(self, mock_get_svc, client, auth_header):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_transactions.return_value = _make_transactions(3)
        mock_get_svc.return_value = mock_svc

        resp = client.get(
            "/api/v1/user/portfolios/1/transactions?page=100&page_size=20",
            headers=auth_header,
        )
        assert resp.status_code == 200
        data = resp.json()
        # paginate() clamps page to last page
        assert data["metadata"]["page"] == 1
        assert len(data["items"]) == 3

    def test_invalid_page_zero(self, client, auth_header):
        resp = client.get(
            "/api/v1/user/portfolios/1/transactions?page=0",
            headers=auth_header,
        )
        assert resp.status_code in (400, 422)

    def test_invalid_page_size_over_limit(self, client, auth_header):
        resp = client.get(
            "/api/v1/user/portfolios/1/transactions?page_size=200",
            headers=auth_header,
        )
        assert resp.status_code in (400, 422)
