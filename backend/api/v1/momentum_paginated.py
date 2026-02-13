"""
Paginated Momentum API Endpoints (v1)

Enhanced momentum endpoints with pagination support.
"""

from fastapi import APIRouter, HTTPException, Request, Response, Depends, Query
from typing import Optional
import logging

from ...services.momentum_engine import MomentumEngine
from ...services.portfolio_service import PortfolioService
from ...validators.validators import sanitize_string
from ...config.rate_limit_config import limiter, RateLimits
from ...config.portfolio_config import DEFAULT_PORTFOLIO
from ...utils.pagination import paginate, PaginationParams
from .error_responses import RESOURCE_ERRORS

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
momentum_engine = MomentumEngine()
portfolio_service = PortfolioService(momentum_engine)


@router.get("/top", responses=RESOURCE_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_top_momentum_stocks_paginated(
    request: Request,
    response: Response,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    sort_by: str = Query("momentum_score", description="Sort field (momentum_score, ticker, price)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)")
):
    """
    Get top momentum stocks with pagination support.
    
    **Query Parameters:**
    - page: Page number (default: 1)
    - page_size: Items per page, max 100 (default: 20)
    - category: Optional category filter
    - sort_by: Sort field (momentum_score, ticker, price)
    - sort_order: Sort order (asc, desc)
    
    **Returns:**
    - Paginated list of stocks with metadata
    - Total count, pages, has_next, has_previous
    
    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)
    
    **Example:**
    ```
    GET /api/v1/momentum/top?page=2&page_size=10&sort_by=momentum_score&sort_order=desc
    ```
    """
    try:
        logger.info(
            f"Getting top momentum stocks (page={page}, page_size={page_size}, "
            f"category={category}, sort={sort_by} {sort_order})"
        )
        
        # Validate sort parameters
        valid_sort_fields = ['momentum_score', 'ticker', 'price', 'market_value']
        if sort_by not in valid_sort_fields:
            sort_by = 'momentum_score'
        
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
        
        if category:
            # Get stocks from specific category
            category = sanitize_string(category, max_length=100)
            result = portfolio_service.get_categories_analysis(category)
            
            if 'error' in result:
                raise HTTPException(status_code=404, detail=result['error'])
            
            stocks = result['momentum_scores']
            
            # Sort stocks
            reverse = (sort_order == 'desc')
            stocks_sorted = sorted(
                stocks,
                key=lambda x: x.get(sort_by, 0),
                reverse=reverse
            )
            
            # Paginate
            paginated = paginate(stocks_sorted, page=page, page_size=page_size)
            
            return {
                'category': category,
                'items': paginated['items'],
                'metadata': paginated['metadata']
            }
        else:
            # Get stocks from default portfolio
            df, total_value, avg_score = portfolio_service.analyze_portfolio(DEFAULT_PORTFOLIO)
            
            # Map sort_by to DataFrame column
            column_map = {
                'momentum_score': 'Momentum_Score',
                'ticker': 'Ticker',
                'price': 'Price',
                'market_value': 'Market_Value'
            }
            sort_column = column_map.get(sort_by, 'Momentum_Score')
            
            # Sort DataFrame
            ascending = (sort_order == 'asc')
            df_sorted = df.sort_values(by=sort_column, ascending=ascending)
            
            # Convert to list
            stocks = []
            for _, row in df_sorted.iterrows():
                stocks.append({
                    'ticker': row['Ticker'],
                    'momentum_score': row['Momentum_Score'],
                    'rating': row['Rating'],
                    'price': row['Price'],
                    'market_value': row['Market_Value'],
                    'portfolio_percent': row['Portfolio_%']
                })
            
            # Paginate
            paginated = paginate(stocks, page=page, page_size=page_size)
            
            return {
                'total_portfolio_value': total_value,
                'average_momentum_score': avg_score,
                'items': paginated['items'],
                'metadata': paginated['metadata']
            }
    
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error("Error getting top momentum stocks", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting top stocks: {str(e)}"
        )
