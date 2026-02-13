"""
Paginated Portfolio API Endpoints (v1)

Enhanced portfolio endpoints with pagination support.
"""

from fastapi import APIRouter, HTTPException, Request, Response, Query
from typing import Optional
import logging

from ...services.momentum_engine import MomentumEngine
from ...services.portfolio_service import PortfolioService
from ...models.portfolio import Portfolio
from ...config.rate_limit_config import limiter, RateLimits
from ...config.portfolio_config import DEFAULT_PORTFOLIO, SORT_COLUMN_MAP
from ...utils.pagination import paginate_dataframe
from .error_responses import STANDARD_ERRORS, VALIDATION_ERRORS

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
momentum_engine = MomentumEngine()
portfolio_service = PortfolioService(momentum_engine)


@router.get("/analysis/paginated", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def analyze_default_portfolio_paginated(
    request: Request,
    response: Response,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Holdings per page (1-100)"),
    sort_by: str = Query("momentum_score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)")
):
    """
    Analyze default portfolio with paginated holdings.
    
    **Query Parameters:**
    - page: Page number (default: 1)
    - page_size: Holdings per page, max 100 (default: 20)
    - sort_by: Sort field (momentum_score, ticker, market_value, portfolio_percent)
    - sort_order: Sort order (asc, desc)
    
    **Returns:**
    - Paginated portfolio holdings
    - Portfolio summary (total value, avg score)
    - Pagination metadata
    
    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)
    """
    try:
        logger.info(
            f"Analyzing default portfolio with pagination "
            f"(page={page}, page_size={page_size}, sort={sort_by} {sort_order})"
        )
        
        # Analyze portfolio
        df, total_value, avg_score = portfolio_service.analyze_portfolio(DEFAULT_PORTFOLIO)
        
        sort_column = SORT_COLUMN_MAP.get(sort_by, 'Momentum_Score')

        # Sort and paginate DataFrame
        ascending = (sort_order == 'asc')
        df_sorted = df.sort_values(by=sort_column, ascending=ascending)
        paginated = paginate_dataframe(df_sorted, page=page, page_size=page_size)

        return {
            'summary': {
                'total_value': total_value,
                'average_momentum_score': avg_score,
                'total_positions': len(DEFAULT_PORTFOLIO)
            },
            'holdings': PortfolioService.dataframe_to_holdings(paginated['items']),
            'metadata': paginated['metadata']
        }
        
    except Exception as e:
        logger.error("Error analyzing default portfolio", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing portfolio: {str(e)}"
        )


@router.post("/analyze/paginated", responses=VALIDATION_ERRORS)
@limiter.limit(RateLimits.EXPENSIVE)
async def analyze_custom_portfolio_paginated(
    request: Request,
    response: Response,
    portfolio: Portfolio,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Holdings per page"),
    sort_by: str = Query("momentum_score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order")
):
    """
    Analyze custom portfolio with paginated holdings.
    
    **Request Body:**
    ```json
    {
      "holdings": {
        "AAPL": 100,
        "NVDA": 50,
        "MSFT": 75
      }
    }
    ```
    
    **Query Parameters:**
    - page: Page number (default: 1)
    - page_size: Holdings per page (default: 20)
    - sort_by: Sort field
    - sort_order: Sort order (asc, desc)
    
    **Returns:**
    - Paginated custom portfolio holdings
    - Portfolio summary
    
    **Rate Limit:** 10 requests/minute (resource-intensive)
    """
    try:
        if not portfolio.holdings:
            raise HTTPException(status_code=400, detail="Portfolio cannot be empty")
        
        logger.info(
            f"Analyzing custom portfolio ({len(portfolio.holdings)} positions) "
            f"with pagination (page={page}, page_size={page_size})"
        )
        
        # Analyze portfolio
        df, total_value, avg_score = portfolio_service.analyze_portfolio(portfolio.holdings)
        
        sort_column = SORT_COLUMN_MAP.get(sort_by, 'Momentum_Score')

        # Sort and paginate DataFrame
        ascending = (sort_order == 'asc')
        df_sorted = df.sort_values(by=sort_column, ascending=ascending)
        paginated = paginate_dataframe(df_sorted, page=page, page_size=page_size)

        return {
            'summary': {
                'total_value': total_value,
                'average_momentum_score': avg_score,
                'total_positions': len(portfolio.holdings)
            },
            'holdings': PortfolioService.dataframe_to_holdings(paginated['items']),
            'metadata': paginated['metadata']
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error("Error analyzing custom portfolio", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing custom portfolio: {str(e)}"
        )
