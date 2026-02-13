"""
Paginated Historical Data API Endpoints (v1)

Historical momentum scores, portfolio performance, and top performers
with pagination support.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional
import logging

from ...services.momentum_engine import MomentumEngine
from ...services.historical_service import HistoricalDataService
from ...validators.validators import sanitize_string
from ...config.rate_limit_config import limiter, RateLimits
from ...utils.pagination import paginate
from .error_responses import STANDARD_ERRORS

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
momentum_engine = MomentumEngine()
historical_service = momentum_engine.historical_service


@router.get("/momentum/{ticker}", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_momentum_history_paginated(
    request: Request,
    ticker: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    sort_order: str = Query("asc", description="Sort order by timestamp (asc, desc)")
):
    """
    Get historical momentum scores for a ticker with pagination.

    **Query Parameters:**
    - days: Number of days of history (default: 30, max: 365)
    - page: Page number (default: 1)
    - page_size: Items per page, max 100 (default: 20)
    - sort_order: Sort order by timestamp (asc, desc)

    **Returns:**
    - Paginated momentum history entries
    - Trend analysis and score change metadata
    - Pagination metadata
    """
    try:
        ticker = sanitize_string(ticker.upper(), max_length=10)

        logger.info(
            f"Getting momentum history for {ticker} "
            f"(days={days}, page={page}, page_size={page_size}, sort={sort_order})"
        )

        history = historical_service.get_momentum_history(ticker, days)

        if not history:
            return {
                "ticker": ticker,
                "trend": "neutral",
                "current_score": 0,
                "score_change": 0,
                "items": [],
                "metadata": {
                    "page": 1,
                    "page_size": page_size,
                    "total_items": 0,
                    "total_pages": 1,
                    "has_next": False,
                    "has_previous": False,
                    "next_page": None,
                    "previous_page": None
                }
            }

        # Sort by timestamp
        reverse = (sort_order == "desc")
        history_sorted = sorted(history, key=lambda x: x["timestamp"], reverse=reverse)

        # Calculate trend from chronological data (always asc for analysis)
        if len(history) >= 2:
            chronological = sorted(history, key=lambda x: x["timestamp"])
            initial_score = chronological[0]["composite_score"]
            latest_score = chronological[-1]["composite_score"]
            score_change = latest_score - initial_score

            if score_change > 5:
                trend = "improving"
            elif score_change < -5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "neutral"
            score_change = 0
            latest_score = history[0]["composite_score"]

        # Paginate
        paginated = paginate(history_sorted, page=page, page_size=page_size)

        return {
            "ticker": ticker,
            "trend": trend,
            "current_score": latest_score,
            "score_change": round(score_change, 2),
            "items": paginated["items"],
            "metadata": paginated["metadata"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting momentum history for {ticker}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching momentum history: {str(e)}"
        )


@router.get("/portfolio/{portfolio_id}", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_portfolio_history_paginated(
    request: Request,
    portfolio_id: str = "default",
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)")
):
    """
    Get historical portfolio performance with pagination.

    Paginates the portfolio value entries. Analytics summary is returned
    alongside but is not paginated (it's a single summary object).

    **Query Parameters:**
    - days: Number of days of history (default: 30, max: 365)
    - page: Page number (default: 1)
    - page_size: Items per page, max 100 (default: 20)

    **Returns:**
    - Paginated portfolio value entries
    - Performance analytics summary (non-paginated)
    - Pagination metadata
    """
    try:
        portfolio_id = sanitize_string(portfolio_id, max_length=100)

        logger.info(
            f"Getting portfolio history for {portfolio_id} "
            f"(days={days}, page={page}, page_size={page_size})"
        )

        history = historical_service.get_portfolio_history(portfolio_id, days)
        analytics = historical_service.get_performance_analytics(portfolio_id, days)

        values = history.get("values", [])

        # Paginate values
        paginated = paginate(values, page=page, page_size=page_size)

        return {
            "portfolio_id": portfolio_id,
            "analytics": analytics,
            "items": paginated["items"],
            "metadata": paginated["metadata"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio history for {portfolio_id}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching portfolio history: {str(e)}"
        )


@router.get("/top-performers", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_top_performers_paginated(
    request: Request,
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)")
):
    """
    Get top performing stocks by momentum improvement with pagination.

    Unlike the legacy endpoint which returns only top 10, this endpoint
    returns the full list with pagination support.

    **Query Parameters:**
    - days: Period to analyze (default: 7, max: 90)
    - page: Page number (default: 1)
    - page_size: Items per page, max 100 (default: 20)

    **Returns:**
    - Paginated list of performers sorted by improvement
    - Pagination metadata
    """
    try:
        logger.info(
            f"Getting top performers (days={days}, page={page}, page_size={page_size})"
        )

        # get_top_performers returns sorted list capped at 10;
        # we need the full list, so we call the underlying logic directly
        performers = _get_all_performers(days)

        # Paginate
        paginated = paginate(performers, page=page, page_size=page_size)

        return {
            "period_days": days,
            "items": paginated["items"],
            "metadata": paginated["metadata"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting top performers", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching top performers: {str(e)}"
        )


def _get_all_performers(days: int) -> list:
    """
    Get all performers sorted by improvement (not capped at 10).

    Replicates the logic from HistoricalDataService.get_top_performers()
    but without the [:10] slice.
    """
    import json
    from datetime import datetime, timedelta

    try:
        with open(historical_service.momentum_scores_file, "r") as f:
            data = json.load(f)

        performers = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for ticker, scores in data.items():
            recent_scores = [
                entry for entry in scores
                if datetime.fromisoformat(entry["timestamp"]) > cutoff_date
            ]

            if len(recent_scores) >= 2:
                recent_scores.sort(key=lambda x: x["timestamp"])

                initial_score = recent_scores[0]["composite_score"]
                latest_score = recent_scores[-1]["composite_score"]
                improvement = latest_score - initial_score

                performers.append({
                    "ticker": ticker,
                    "initial_score": initial_score,
                    "latest_score": latest_score,
                    "improvement": round(improvement, 2),
                    "improvement_percent": round(
                        (improvement / initial_score * 100) if initial_score > 0 else 0, 2
                    ),
                    "latest_rating": recent_scores[-1]["rating"]
                })

        performers.sort(key=lambda x: x["improvement"], reverse=True)
        return performers

    except (FileNotFoundError, json.JSONDecodeError):
        return []
