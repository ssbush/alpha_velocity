"""
Paginated Transaction History API Endpoints (v1)

Authenticated endpoints for viewing transaction history with pagination and sorting.
"""

from fastapi import APIRouter, HTTPException, Request, Response, Depends, Query
import logging

from ...auth import get_current_user_id
from ...config.rate_limit_config import limiter, RateLimits
from ...utils.pagination import paginate

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_portfolio_service():
    """Get user portfolio service with database session."""
    try:
        from ...database.config import get_database_session
        from ...services.user_portfolio_service import UserPortfolioService
        db = next(get_database_session())
        return UserPortfolioService(db)
    except Exception:
        raise HTTPException(status_code=503, detail="Database not available")


@router.get("/portfolios/{portfolio_id}/transactions")
@limiter.limit(RateLimits.PUBLIC_API)
async def get_portfolio_transactions_paginated(
    request: Request,
    response: Response,
    portfolio_id: int,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    sort_by: str = Query("transaction_date", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    user_id: int = Depends(get_current_user_id)
):
    """
    Get paginated transaction history for a portfolio.

    **Authentication:** Required (Bearer token)

    **Query Parameters:**
    - page: Page number (default: 1)
    - page_size: Items per page, max 100 (default: 20)
    - sort_by: Sort field (transaction_date, ticker, transaction_type, total_amount)
    - sort_order: Sort order (asc, desc)

    **Returns:**
    - Paginated list of transactions
    - Pagination metadata
    """
    try:
        service = _get_portfolio_service()

        # Validate sort field
        valid_sort_fields = ["transaction_date", "ticker", "transaction_type", "total_amount"]
        if sort_by not in valid_sort_fields:
            sort_by = "transaction_date"

        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"

        logger.info(
            f"Getting transactions for portfolio {portfolio_id} "
            f"(page={page}, page_size={page_size}, sort={sort_by} {sort_order})"
        )

        # Fetch all transactions (limit=None for full list)
        transactions = service.get_portfolio_transactions(portfolio_id, user_id, limit=None)

        # Sort
        reverse = (sort_order == "desc")
        transactions_sorted = sorted(
            transactions,
            key=lambda x: x.get(sort_by, ""),
            reverse=reverse
        )

        # Paginate
        paginated = paginate(transactions_sorted, page=page, page_size=page_size)

        return {
            "portfolio_id": portfolio_id,
            "items": paginated["items"],
            "metadata": paginated["metadata"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transactions for portfolio {portfolio_id}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching transactions: {str(e)}"
        )
