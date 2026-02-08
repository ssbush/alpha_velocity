"""
Metrics API Endpoints (v1)

Endpoints for accessing performance metrics and statistics.
"""

from fastapi import APIRouter, Request, Query
from typing import Optional
import logging

from ...middleware.performance_middleware import (
    get_performance_stats,
    reset_performance_stats
)
from ...config.rate_limit_config import limiter, RateLimits

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/performance")
@limiter.limit(RateLimits.PUBLIC_API)
async def get_performance_metrics(
    request: Request,
    endpoint: Optional[str] = Query(None, description="Specific endpoint to query")
):
    """
    Get performance metrics for API endpoints.

    Returns statistics including:
    - Request count
    - Average response time
    - Min/max response time
    - Percentiles (p50, p95, p99)
    - Status code distribution
    - Error rate

    **Query Parameters:**
    - endpoint: Optional endpoint path to filter (e.g., "/api/v1/momentum/{ticker}")

    **Returns:**
    - Performance statistics for requested endpoint(s)

    **Rate Limit:** 100 requests/minute

    **Example:**
    ```bash
    GET /api/v1/metrics/performance
    GET /api/v1/metrics/performance?endpoint=/api/v1/momentum/{ticker}
    ```
    """
    try:
        stats = get_performance_stats(endpoint)

        return {
            'success': True,
            'data': stats,
            'message': f"Performance metrics retrieved for {endpoint or 'all endpoints'}"
        }

    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': "Failed to retrieve performance metrics"
        }


@router.delete("/performance/reset")
@limiter.limit(RateLimits.ADMIN)
async def reset_performance_metrics(
    request: Request,
    endpoint: Optional[str] = Query(None, description="Specific endpoint to reset")
):
    """
    Reset performance metrics.

    **⚠️ Administrative Operation**

    Clears performance statistics for specified endpoint or all endpoints.

    **Query Parameters:**
    - endpoint: Optional endpoint path to reset, or omit for all

    **Returns:**
    - Success confirmation

    **Rate Limit:** 5 requests/minute (admin)

    **Example:**
    ```bash
    DELETE /api/v1/metrics/performance/reset
    DELETE /api/v1/metrics/performance/reset?endpoint=/api/v1/momentum/{ticker}
    ```
    """
    try:
        reset_performance_stats(endpoint)

        logger.info(
            f"Performance metrics reset: {endpoint or 'all endpoints'}",
            extra={'request_id': getattr(request.state, 'request_id', 'unknown')}
        )

        return {
            'success': True,
            'message': f"Performance metrics reset for {endpoint or 'all endpoints'}"
        }

    except Exception as e:
        logger.error(f"Error resetting performance metrics: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': "Failed to reset performance metrics"
        }


@router.get("/endpoints")
@limiter.limit(RateLimits.PUBLIC_API)
async def get_endpoint_summary(request: Request):
    """
    Get summary of all tracked endpoints.

    Returns high-level overview of API usage across all endpoints.

    **Returns:**
    - List of endpoints with basic statistics
    - Total request count
    - Average response time across all endpoints

    **Rate Limit:** 100 requests/minute

    **Example:**
    ```bash
    GET /api/v1/metrics/endpoints
    ```
    """
    try:
        all_stats = get_performance_stats()
        endpoints = all_stats.get('endpoints', [])

        # Calculate overall statistics
        total_requests = sum(e.get('count', 0) for e in endpoints)
        avg_duration = (
            sum(e.get('avg_duration_ms', 0) * e.get('count', 0) for e in endpoints) / total_requests
            if total_requests > 0 else 0
        )

        # Sort by request count
        endpoints_sorted = sorted(
            endpoints,
            key=lambda x: x.get('count', 0),
            reverse=True
        )

        return {
            'success': True,
            'summary': {
                'total_endpoints': len(endpoints),
                'total_requests': total_requests,
                'avg_duration_ms': round(avg_duration, 2)
            },
            'endpoints': endpoints_sorted,
            'message': "Endpoint summary retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error retrieving endpoint summary: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': "Failed to retrieve endpoint summary"
        }


@router.get("/slow")
@limiter.limit(RateLimits.PUBLIC_API)
async def get_slow_endpoints(
    request: Request,
    threshold_ms: float = Query(1000.0, ge=100, le=60000, description="Threshold in milliseconds")
):
    """
    Get endpoints with slow average response times.

    **Query Parameters:**
    - threshold_ms: Response time threshold in milliseconds (default: 1000)

    **Returns:**
    - List of endpoints exceeding threshold
    - Sorted by average response time (slowest first)

    **Rate Limit:** 100 requests/minute

    **Example:**
    ```bash
    GET /api/v1/metrics/slow
    GET /api/v1/metrics/slow?threshold_ms=500
    ```
    """
    try:
        all_stats = get_performance_stats()
        endpoints = all_stats.get('endpoints', [])

        # Filter slow endpoints
        slow_endpoints = [
            e for e in endpoints
            if e.get('avg_duration_ms', 0) > threshold_ms
        ]

        # Sort by average duration (slowest first)
        slow_endpoints_sorted = sorted(
            slow_endpoints,
            key=lambda x: x.get('avg_duration_ms', 0),
            reverse=True
        )

        return {
            'success': True,
            'threshold_ms': threshold_ms,
            'count': len(slow_endpoints_sorted),
            'endpoints': slow_endpoints_sorted,
            'message': f"Found {len(slow_endpoints_sorted)} slow endpoints"
        }

    except Exception as e:
        logger.error(f"Error retrieving slow endpoints: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': "Failed to retrieve slow endpoints"
        }
