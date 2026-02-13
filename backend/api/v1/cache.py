"""
Cache API Endpoints (v1)

Endpoints for cache management and status.
"""

from fastapi import APIRouter, HTTPException, Request
import logging

from ...services.momentum_engine import MomentumEngine
from ...config.rate_limit_config import limiter, RateLimits
from .error_responses import STANDARD_ERRORS

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize momentum engine
momentum_engine = MomentumEngine()


@router.get("/status", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_cache_status(request: Request):
    """
    Get cache statistics and status.
    
    **Returns:**
    - Number of cached prices
    - Cache hit/miss statistics (if available)
    - Cache memory usage (if available)
    
    **Rate Limit:** 100 requests/minute (public), 200 requests/minute (authenticated)
    """
    try:
        logger.info("Fetching cache status")
        
        # Get cache statistics from momentum engine
        cache_info = {
            'status': 'active',
            'type': 'in-memory'
        }
        
        # Try to get cache size if available
        if hasattr(momentum_engine, '_price_cache'):
            cache_info['cached_prices'] = len(momentum_engine._price_cache)
        elif hasattr(momentum_engine, 'price_cache'):
            cache_info['cached_prices'] = len(momentum_engine.price_cache)
        else:
            cache_info['cached_prices'] = 0
        
        return cache_info
        
    except Exception as e:
        logger.error("Error fetching cache status", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching cache status: {str(e)}"
        )


@router.post("/clear", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.BULK)
async def clear_cache(request: Request):
    """
    Clear the price cache.
    
    **Warning:** This is a resource-intensive operation that will require
    re-fetching all price data on next request.
    
    **Returns:**
    - Confirmation message
    - Number of items cleared
    
    **Rate Limit:** 5 requests/minute (administrative operation)
    """
    try:
        logger.warning("Clearing price cache (administrative operation)")
        
        items_cleared = 0
        
        # Clear cache if available
        if hasattr(momentum_engine, '_price_cache'):
            items_cleared = len(momentum_engine._price_cache)
            momentum_engine._price_cache.clear()
        elif hasattr(momentum_engine, 'price_cache'):
            items_cleared = len(momentum_engine.price_cache)
            momentum_engine.price_cache.clear()
        
        logger.info(f"Cleared {items_cleared} items from cache")
        
        return {
            'message': 'Cache cleared successfully',
            'items_cleared': items_cleared
        }
        
    except Exception as e:
        logger.error("Error clearing cache", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing cache: {str(e)}"
        )
