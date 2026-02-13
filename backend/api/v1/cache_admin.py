"""
Cache Administration API Endpoints (v1)

Advanced cache management endpoints for monitoring and control.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional
import logging

from ...cache import cache, get_cache
from ...config.rate_limit_config import limiter, RateLimits
from ...config.portfolio_config import DEFAULT_PORTFOLIO
from .error_responses import STANDARD_ERRORS

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/info", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_cache_info(request: Request):
    """
    Get cache system information and statistics.
    
    **Returns:**
    - Cache type (redis or in-memory)
    - Total number of keys
    - Memory usage (if Redis)
    - Connection status
    
    **Rate Limit:** 100 requests/minute
    """
    try:
        cache_service = get_cache()
        
        info = cache_service.info()
        info['is_redis'] = cache_service.is_redis()
        info['is_memory'] = cache_service.is_memory()
        
        return info
        
    except Exception as e:
        logger.error("Error getting cache info", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting cache info: {str(e)}"
        )


@router.get("/keys", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def list_cache_keys(
    request: Request,
    pattern: str = Query("*", description="Key pattern (supports wildcards)")
):
    """
    List cache keys matching a pattern.
    
    **Query Parameters:**
    - pattern: Key pattern with wildcard support (default: "*")
    
    **Returns:**
    - List of cache keys
    
    **Examples:**
    - `GET /cache/keys?pattern=price:*` - All price keys
    - `GET /cache/keys?pattern=momentum:*` - All momentum keys
    - `GET /cache/keys?pattern=*` - All keys
    
    **Rate Limit:** 100 requests/minute
    """
    try:
        cache_service = get_cache()
        keys = cache_service.keys(pattern)
        
        return {
            'pattern': pattern,
            'count': len(keys),
            'keys': keys[:100]  # Limit to first 100 keys
        }
        
    except Exception as e:
        logger.error(f"Error listing cache keys with pattern {pattern}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing cache keys: {str(e)}"
        )


@router.delete("/clear", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.BULK)
async def clear_cache_pattern(
    request: Request,
    pattern: str = Query("*", description="Pattern of keys to clear")
):
    """
    Clear cache keys matching a pattern.
    
    **Query Parameters:**
    - pattern: Key pattern to clear (default: "*" - clears all)
    
    **Warning:** This is a destructive operation. Use carefully.
    
    **Examples:**
    - `DELETE /cache/clear?pattern=price:*` - Clear all price caches
    - `DELETE /cache/clear?pattern=momentum:*` - Clear momentum caches
    - `DELETE /cache/clear?pattern=*` - Clear entire cache
    
    **Returns:**
    - Success message
    
    **Rate Limit:** 5 requests/minute (administrative operation)
    """
    try:
        cache_service = get_cache()
        
        # Get count before clearing
        keys_before = cache_service.keys(pattern)
        count = len(keys_before)
        
        # Clear cache
        cache_service.clear(pattern)
        
        logger.warning(f"Cleared {count} cache keys matching pattern: {pattern}")
        
        return {
            'message': f'Cache cleared successfully',
            'pattern': pattern,
            'keys_cleared': count
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache with pattern {pattern}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing cache: {str(e)}"
        )


@router.get("/stats", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_cache_stats(request: Request):
    """
    Get detailed cache statistics by key prefix.
    
    **Returns:**
    - Breakdown of cache keys by type (price, momentum, portfolio)
    - Count for each category
    
    **Rate Limit:** 100 requests/minute
    """
    try:
        cache_service = get_cache()
        
        # Get keys by prefix
        prefixes = ['price:', 'momentum:', 'portfolio:']
        stats = {}
        
        for prefix in prefixes:
            keys = cache_service.keys(f"{prefix}*")
            category = prefix.rstrip(':')
            stats[category] = {
                'count': len(keys),
                'sample_keys': keys[:5]  # First 5 keys as sample
            }
        
        # Get total
        all_keys = cache_service.keys("*")
        stats['total'] = {
            'count': len(all_keys)
        }
        
        return stats
        
    except Exception as e:
        logger.error("Error getting cache stats", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting cache stats: {str(e)}"
        )


@router.post("/warmup", responses=STANDARD_ERRORS)
@limiter.limit(RateLimits.BULK)
async def warmup_cache(
    request: Request,
    tickers: Optional[str] = Query(None, description="Comma-separated tickers to warm up")
):
    """
    Warm up cache by pre-fetching data for specified tickers.
    
    **Query Parameters:**
    - tickers: Comma-separated list of tickers (e.g., "AAPL,NVDA,MSFT")
    
    **Returns:**
    - Number of items cached
    - List of tickers processed
    
    **Rate Limit:** 5 requests/minute (resource-intensive operation)
    """
    try:
        from ...services.momentum_engine import MomentumEngine
        
        if not tickers:
            # Use default portfolio tickers
            ticker_list = list(DEFAULT_PORTFOLIO.keys())
        else:
            ticker_list = [t.strip().upper() for t in tickers.split(',')]
        
        logger.info(f"Warming up cache for {len(ticker_list)} tickers")
        
        engine = MomentumEngine()
        cached_count = 0
        
        for ticker in ticker_list:
            try:
                # This will cache the result
                engine.calculate_momentum_score(ticker)
                cached_count += 1
            except Exception as e:
                logger.warning(f"Failed to cache {ticker}: {e}")
        
        return {
            'message': 'Cache warmup completed',
            'tickers_processed': len(ticker_list),
            'successfully_cached': cached_count,
            'tickers': ticker_list
        }
        
    except Exception as e:
        logger.error("Error warming up cache", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error warming up cache: {str(e)}"
        )
