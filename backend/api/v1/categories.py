"""
Categories API Endpoints (v1)

Endpoints for portfolio category management and analysis.
"""

from fastapi import APIRouter, HTTPException, Request, Response
from typing import List
import logging

from ...services.portfolio_service import get_portfolio_service
from ...models.portfolio import CategoryInfo, CategoryAnalysis
from ...validators.validators import sanitize_string
from ...config.rate_limit_config import limiter, RateLimits
from .error_responses import STANDARD_ERRORS, RESOURCE_ERRORS

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[CategoryInfo], responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_categories(request: Request, response: Response):
    """
    Get all portfolio categories with metadata.
    
    **Returns:**
    - List of categories with:
      - Category name
      - Tickers in category
      - Target allocation percentage
      - Benchmark index
    
    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)
    """
    try:
        logger.info("Fetching all categories")
        categories = get_portfolio_service().get_all_categories()
        
        result = []
        for name, info in categories.items():
            result.append(CategoryInfo(
                name=name,
                tickers=info['tickers'],
                target_allocation=info['target_allocation'],
                benchmark=info['benchmark']
            ))
        
        return result
        
    except Exception as e:
        logger.error("Error fetching categories", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching categories: {str(e)}"
        )


@router.get("/{category_name}/analysis", response_model=CategoryAnalysis, responses=RESOURCE_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def analyze_category(request: Request, response: Response, category_name: str):
    """
    Analyze a specific portfolio category.
    
    **Parameters:**
    - category_name: Name of the category to analyze
    
    **Returns:**
    - Category metadata
    - Momentum scores for all tickers in category
    - Average category momentum score
    
    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)
    """
    try:
        # Sanitize category name
        category_name = sanitize_string(category_name, max_length=100)
        
        logger.info(f"Analyzing category: {category_name}")
        result = get_portfolio_service().get_categories_analysis(category_name)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return CategoryAnalysis(**result)
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error analyzing category {category_name}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing category: {str(e)}"
        )


@router.get("/{category_name}/tickers", responses=RESOURCE_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_category_tickers(request: Request, response: Response, category_name: str):
    """
    Get list of tickers in a specific category.
    
    **Parameters:**
    - category_name: Name of the category
    
    **Returns:**
    - List of ticker symbols in the category
    
    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)
    """
    try:
        # Sanitize category name
        category_name = sanitize_string(category_name, max_length=100)
        
        logger.info(f"Fetching tickers for category: {category_name}")
        categories = get_portfolio_service().get_all_categories()
        
        if category_name not in categories:
            raise HTTPException(
                status_code=404,
                detail=f"Category '{category_name}' not found"
            )
        
        return {
            'category': category_name,
            'tickers': categories[category_name]['tickers'],
            'count': len(categories[category_name]['tickers'])
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Error fetching tickers for category {category_name}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching category tickers: {str(e)}"
        )
