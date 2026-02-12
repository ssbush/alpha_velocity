"""
Tests for Error Handling Consistency

Verifies that:
1. metrics.py endpoints return 500 (not 200) on internal errors
2. main.py endpoints propagate HTTPException status codes (not swallow to 500)
3. momentum_batch.py handles InvalidTickerError in sequential loop
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.main import app


client = TestClient(app)


class TestMetricsErrorHandling:
    """metrics.py should raise HTTPException(500), not return error dicts with 200."""

    @patch("backend.api.v1.metrics.get_performance_stats")
    def test_performance_metrics_error_returns_500(self, mock_stats):
        mock_stats.side_effect = RuntimeError("stats unavailable")
        resp = client.get("/api/v1/metrics/performance")
        assert resp.status_code == 500

    @patch("backend.api.v1.metrics.reset_performance_stats")
    def test_reset_metrics_error_returns_500(self, mock_reset):
        mock_reset.side_effect = RuntimeError("reset failed")
        resp = client.request("DELETE", "/api/v1/metrics/performance/reset")
        assert resp.status_code == 500

    @patch("backend.api.v1.metrics.get_performance_stats")
    def test_endpoints_summary_error_returns_500(self, mock_stats):
        mock_stats.side_effect = RuntimeError("stats unavailable")
        resp = client.get("/api/v1/metrics/endpoints")
        assert resp.status_code == 500

    @patch("backend.api.v1.metrics.get_performance_stats")
    def test_slow_endpoints_error_returns_500(self, mock_stats):
        mock_stats.side_effect = RuntimeError("stats unavailable")
        resp = client.get("/api/v1/metrics/slow")
        assert resp.status_code == 500


class TestHTTPExceptionPassthrough:
    """main.py endpoints should propagate HTTPException codes, not swallow to 500."""

    @patch("backend.main.portfolio_service")
    def test_analyze_portfolio_propagates_http_exception(self, mock_service):
        mock_service.analyze_portfolio.side_effect = HTTPException(
            status_code=422, detail="Unprocessable"
        )
        resp = client.get("/portfolio/analysis")
        assert resp.status_code == 422

    @patch("backend.main.daily_scheduler")
    def test_update_daily_cache_propagates_http_exception(self, mock_scheduler):
        mock_scheduler.run_manual_update.side_effect = HTTPException(
            status_code=503, detail="Service unavailable"
        )
        resp = client.post("/cache/daily/update")
        assert resp.status_code == 503

    @patch("backend.main.momentum_engine")
    def test_cache_status_propagates_http_exception(self, mock_engine):
        mock_engine.get_cache_stats.side_effect = HTTPException(
            status_code=503, detail="Engine unavailable"
        )
        resp = client.get("/cache/status")
        assert resp.status_code == 503


class TestMomentumBatchErrorHandling:
    """momentum_batch.py sequential loop should handle InvalidTickerError gracefully."""

    @patch("backend.services.momentum_engine.MomentumEngine")
    @patch("backend.api.v1.momentum_batch.ConcurrentMomentumEngine")
    def test_sequential_loop_handles_invalid_ticker(self, mock_concurrent, mock_engine_cls):
        from backend.exceptions import InvalidTickerError

        engine_instance = MagicMock()
        mock_engine_cls.return_value = engine_instance
        # First ticker raises InvalidTickerError, remaining two succeed
        engine_instance.calculate_momentum_score.side_effect = [
            InvalidTickerError("BAD"),
            {"overall_momentum_score": 75.0},
            {"overall_momentum_score": 80.0},
        ]

        concurrent_instance = MagicMock()
        mock_concurrent.return_value = concurrent_instance
        concurrent_instance.batch_calculate_momentum.return_value = {
            "BAD": {"error": "Invalid ticker"},
            "AAPL": {"overall_momentum_score": 75.0},
            "NVDA": {"overall_momentum_score": 80.0},
        }

        resp = client.get(
            "/api/v1/momentum/concurrent/compare?tickers=BAD,AAPL,NVDA"
        )
        # Should still succeed (per-ticker errors are skipped)
        assert resp.status_code == 200
        data = resp.json()
        assert "speedup_factor" in data
