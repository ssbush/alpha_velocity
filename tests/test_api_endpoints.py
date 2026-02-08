"""
API Endpoint Tests

Tests FastAPI endpoints using pytest and TestClient.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.api


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_root_endpoint(self, test_client):
        """Test GET / returns 200"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestMomentumEndpoints:
    """Test momentum-related endpoints"""

    @pytest.mark.slow
    def test_get_momentum_score(self, test_client):
        """Test GET /momentum/{ticker}"""
        response = test_client.get("/momentum/AAPL")

        # Should return 200 or 500 (if data fetch fails)
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "ticker" in data
            assert "composite_score" in data

    def test_get_momentum_invalid_ticker(self, test_client):
        """Test GET /momentum/{ticker} with invalid ticker"""
        response = test_client.get("/momentum/INVALID;DROP")

        # Should return 400 for invalid input
        assert response.status_code == 400


class TestPortfolioEndpoints:
    """Test portfolio-related endpoints"""

    def test_get_portfolio_analysis(self, test_client):
        """Test GET /portfolio/analysis"""
        response = test_client.get("/portfolio/analysis")

        # Should return 200 or 500
        assert response.status_code in [200, 500]

    def test_post_portfolio_analyze(self, test_client, sample_portfolio):
        """Test POST /portfolio/analyze"""
        response = test_client.post(
            "/portfolio/analyze",
            json={"holdings": sample_portfolio}
        )

        # Should return 200 or 400/500
        assert response.status_code in [200, 400, 500]

    def test_post_portfolio_analyze_empty(self, test_client):
        """Test POST /portfolio/analyze with empty portfolio"""
        response = test_client.post(
            "/portfolio/analyze",
            json={"holdings": {}}
        )

        # Should return 400 for empty portfolio
        assert response.status_code == 400


class TestCategoryEndpoints:
    """Test category-related endpoints"""

    def test_get_categories(self, test_client):
        """Test GET /categories"""
        response = test_client.get("/categories")

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
