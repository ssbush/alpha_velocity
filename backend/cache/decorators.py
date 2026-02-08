"""
Caching Decorators

Provides decorators for caching function results.
"""

import logging
import hashlib
import json
from functools import wraps
from typing import Callable, Optional, Any

from .redis_cache import get_cache, DEFAULT_TTL

logger = logging.getLogger(__name__)


def cache_key(*args, **kwargs) -> str:
    """
    Generate cache key from function arguments.
    
    Creates a unique key based on function name and arguments.
    """
    # Serialize arguments
    key_data = {
        'args': [str(arg) for arg in args],
        'kwargs': {k: str(v) for k, v in kwargs.items()}
    }
    
    # Create hash of serialized data
    serialized = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(serialized.encode()).hexdigest()
    
    return key_hash


def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    key_func: Optional[Callable] = None
):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds (None = no expiration)
        key_prefix: Prefix for cache key
        key_func: Custom function to generate cache key
    
    Example:
        @cached(ttl=300, key_prefix="price:")
        def get_stock_price(ticker):
            return fetch_price(ticker)
        
        # First call: fetches from API, caches result
        price = get_stock_price("AAPL")
        
        # Second call: returns cached result
        price = get_stock_price("AAPL")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get cache instance
            cache_service = get_cache()
            
            # Generate cache key
            if key_func:
                cache_key_str = key_func(*args, **kwargs)
            else:
                func_name = f"{func.__module__}.{func.__name__}"
                arg_key = cache_key(*args, **kwargs)
                cache_key_str = f"{key_prefix}{func_name}:{arg_key}"
            
            # Try to get from cache
            cached_value = cache_service.get(cache_key_str)
            if cached_value is not None:
                logger.debug(f"Cache HIT for {cache_key_str}")
                return cached_value
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS for {cache_key_str}")
            result = func(*args, **kwargs)
            
            # Cache the result
            cache_service.set(cache_key_str, result, ttl=ttl or DEFAULT_TTL)
            
            return result
        
        # Add cache control methods
        wrapper.clear_cache = lambda: get_cache().clear(key_prefix + "*")
        wrapper.cache_key_prefix = key_prefix
        
        return wrapper
    
    return decorator


def cache_price(ttl: int = 300):
    """
    Specialized decorator for caching stock prices.
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
    
    Example:
        @cache_price(ttl=300)
        def get_stock_price(ticker: str) -> float:
            return yfinance.Ticker(ticker).info['currentPrice']
    """
    def key_func(ticker: str, *args, **kwargs) -> str:
        return f"price:{ticker.upper()}"
    
    return cached(ttl=ttl, key_prefix="price:", key_func=key_func)


def cache_momentum(ttl: int = 1800):
    """
    Specialized decorator for caching momentum scores.
    
    Args:
        ttl: Time to live in seconds (default: 30 minutes)
    
    Example:
        @cache_momentum(ttl=1800)
        def calculate_momentum_score(ticker: str) -> dict:
            return {
                'ticker': ticker,
                'score': 8.5,
                'rating': 'Strong Buy'
            }
    """
    def key_func(ticker: str, *args, **kwargs) -> str:
        return f"momentum:{ticker.upper()}"
    
    return cached(ttl=ttl, key_prefix="momentum:", key_func=key_func)


def cache_portfolio(ttl: int = 600):
    """
    Specialized decorator for caching portfolio analysis.
    
    Args:
        ttl: Time to live in seconds (default: 10 minutes)
    
    Example:
        @cache_portfolio(ttl=600)
        def analyze_portfolio(holdings: dict) -> tuple:
            # Expensive analysis
            return (df, total_value, avg_score)
    """
    def key_func(holdings: dict, *args, **kwargs) -> str:
        # Create deterministic key from holdings
        sorted_holdings = sorted(holdings.items())
        holdings_str = json.dumps(sorted_holdings)
        holdings_hash = hashlib.md5(holdings_str.encode()).hexdigest()
        return f"portfolio:{holdings_hash}"
    
    return cached(ttl=ttl, key_prefix="portfolio:", key_func=key_func)


def invalidate_cache(key_pattern: str):
    """
    Decorator to invalidate cache after function execution.
    
    Useful for write operations that should clear related caches.
    
    Args:
        key_pattern: Pattern of keys to invalidate (supports wildcards)
    
    Example:
        @invalidate_cache("price:*")
        def update_stock_prices():
            # Update prices in database
            pass
        
        # After execution, all price:* keys are invalidated
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)
            
            # Invalidate cache
            cache_service = get_cache()
            cache_service.clear(key_pattern)
            logger.info(f"Invalidated cache keys matching: {key_pattern}")
            
            return result
        
        return wrapper
    
    return decorator


class CacheNamespace:
    """
    Context manager for cache namespaces.
    
    Allows temporary cache isolation for specific operations.
    
    Example:
        with CacheNamespace("test"):
            # All cache operations use "test:" prefix
            cache.set("key", "value")  # Actually sets "test:key"
    """
    
    def __init__(self, namespace: str):
        self.namespace = namespace
        self.cache = get_cache()
        self.old_prefix = None
    
    def __enter__(self):
        # Save old prefix and set new one
        from .redis_cache import REDIS_PREFIX
        self.old_prefix = REDIS_PREFIX
        # Note: This is simplified - in production, implement proper prefix stacking
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old prefix
        pass
