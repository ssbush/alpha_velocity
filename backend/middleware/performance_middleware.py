"""
Performance Monitoring Middleware

Tracks API performance metrics and identifies bottlenecks.
"""

import logging
import time
from typing import Dict, List, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import threading

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Thread-safe performance metrics collector.

    Tracks metrics per endpoint:
    - Request count
    - Average response time
    - Min/max response time
    - Status code distribution
    - Error rate
    """

    def __init__(self, window_size: int = 1000):
        """
        Initialize metrics collector.

        Args:
            window_size: Number of recent requests to track per endpoint
        """
        self.window_size = window_size
        self.metrics: Dict[str, Dict] = defaultdict(self._create_endpoint_metrics)
        self.lock = threading.Lock()

    def _create_endpoint_metrics(self) -> Dict:
        """Create metrics structure for an endpoint."""
        return {
            'count': 0,
            'durations': deque(maxlen=self.window_size),
            'status_codes': defaultdict(int),
            'errors': 0,
            'last_reset': datetime.utcnow()
        }

    def record(self, endpoint: str, duration_ms: float, status_code: int):
        """
        Record request metrics.

        Args:
            endpoint: Endpoint path (e.g., "/api/v1/momentum/{ticker}")
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
        """
        with self.lock:
            metrics = self.metrics[endpoint]
            metrics['count'] += 1
            metrics['durations'].append(duration_ms)
            metrics['status_codes'][status_code] += 1

            if status_code >= 500:
                metrics['errors'] += 1

    def get_stats(self, endpoint: str) -> Dict:
        """
        Get statistics for an endpoint.

        Args:
            endpoint: Endpoint path

        Returns:
            Dictionary with statistics
        """
        with self.lock:
            if endpoint not in self.metrics:
                return {}

            metrics = self.metrics[endpoint]
            durations = list(metrics['durations'])

            if not durations:
                return {
                    'endpoint': endpoint,
                    'count': metrics['count'],
                    'error_rate': 0.0
                }

            # Calculate statistics
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)

            # Calculate percentiles
            sorted_durations = sorted(durations)
            p50_idx = int(len(sorted_durations) * 0.50)
            p95_idx = int(len(sorted_durations) * 0.95)
            p99_idx = int(len(sorted_durations) * 0.99)

            p50 = sorted_durations[p50_idx] if p50_idx < len(sorted_durations) else 0
            p95 = sorted_durations[p95_idx] if p95_idx < len(sorted_durations) else 0
            p99 = sorted_durations[p99_idx] if p99_idx < len(sorted_durations) else 0

            # Calculate error rate
            error_rate = (metrics['errors'] / metrics['count']) * 100 if metrics['count'] > 0 else 0

            return {
                'endpoint': endpoint,
                'count': metrics['count'],
                'avg_duration_ms': round(avg_duration, 2),
                'min_duration_ms': round(min_duration, 2),
                'max_duration_ms': round(max_duration, 2),
                'p50_ms': round(p50, 2),
                'p95_ms': round(p95, 2),
                'p99_ms': round(p99, 2),
                'status_codes': dict(metrics['status_codes']),
                'error_count': metrics['errors'],
                'error_rate_percent': round(error_rate, 2),
                'sample_size': len(durations)
            }

    def get_all_stats(self) -> List[Dict]:
        """
        Get statistics for all endpoints.

        Returns:
            List of endpoint statistics
        """
        with self.lock:
            return [
                self.get_stats(endpoint)
                for endpoint in self.metrics.keys()
            ]

    def reset(self, endpoint: Optional[str] = None):
        """
        Reset metrics.

        Args:
            endpoint: Specific endpoint to reset, or None for all
        """
        with self.lock:
            if endpoint:
                if endpoint in self.metrics:
                    self.metrics[endpoint] = self._create_endpoint_metrics()
            else:
                self.metrics.clear()

            logger.info(
                f"Performance metrics reset: {endpoint or 'all endpoints'}"
            )


# Global metrics instance
performance_metrics = PerformanceMetrics()


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking performance metrics.

    Records response times, status codes, and calculates statistics
    for each endpoint.
    """

    def __init__(
        self,
        app: ASGIApp,
        enable_logging: bool = True,
        log_threshold_ms: float = 5000.0
    ):
        """
        Initialize performance middleware.

        Args:
            app: ASGI application
            enable_logging: Enable performance logging
            log_threshold_ms: Log warning if request exceeds this threshold
        """
        super().__init__(app)
        self.enable_logging = enable_logging
        self.log_threshold_ms = log_threshold_ms

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path for metrics grouping.

        Converts:
        - /api/v1/momentum/AAPL -> /api/v1/momentum/{ticker}
        - /api/v1/portfolio/123 -> /api/v1/portfolio/{id}

        Args:
            path: Request path

        Returns:
            Normalized path
        """
        # Simple normalization - replace IDs and tickers
        # More sophisticated routing-based normalization could be added
        import re

        # Replace ticker-like patterns (2-10 uppercase letters)
        path = re.sub(r'/[A-Z]{2,10}(?:/|$)', '/{ticker}/', path)

        # Replace numeric IDs
        path = re.sub(r'/\d+(?:/|$)', '/{id}/', path)

        # Remove trailing slash
        if path.endswith('/') and len(path) > 1:
            path = path[:-1]

        return path

    async def dispatch(self, request: Request, call_next):
        """Process request and record metrics."""

        # Start timing
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Normalize path for metrics
        normalized_path = self._normalize_path(request.url.path)

        # Record metrics
        performance_metrics.record(
            endpoint=normalized_path,
            duration_ms=duration_ms,
            status_code=response.status_code
        )

        # Log extremely slow requests
        if self.enable_logging and duration_ms > self.log_threshold_ms:
            logger.warning(
                f"Very slow request: {request.method} {request.url.path} "
                f"took {duration_ms:.2f}ms (threshold: {self.log_threshold_ms}ms)",
                extra={
                    'request_id': getattr(request.state, 'request_id', 'unknown'),
                    'method': request.method,
                    'path': request.url.path,
                    'normalized_path': normalized_path,
                    'duration_ms': round(duration_ms, 2),
                    'threshold_ms': self.log_threshold_ms,
                    'status_code': response.status_code
                }
            )

        return response


def get_performance_stats(endpoint: Optional[str] = None) -> Dict:
    """
    Get performance statistics.

    Args:
        endpoint: Specific endpoint or None for all

    Returns:
        Performance statistics
    """
    if endpoint:
        return performance_metrics.get_stats(endpoint)
    else:
        return {
            'endpoints': performance_metrics.get_all_stats(),
            'total_endpoints': len(performance_metrics.metrics)
        }


def reset_performance_stats(endpoint: Optional[str] = None):
    """
    Reset performance statistics.

    Args:
        endpoint: Specific endpoint or None for all
    """
    performance_metrics.reset(endpoint)
