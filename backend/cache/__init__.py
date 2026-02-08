"""
Cache Package

Provides Redis-based caching with automatic fallback to in-memory cache.

Usage:
    from backend.cache import cache, cached, cache_price
    
    # Use cache directly
    cache.set("key", "value", ttl=300)
    value = cache.get("key")
    
    # Use decorators
    @cached(ttl=300)
    def expensive_function():
        return result
    
    @cache_price(ttl=300)
    def get_price(ticker):
        return price
"""

from .redis_cache import (
    cache,
    get_cache,
    CacheService,
    RedisCache,
    InMemoryCache,
    DEFAULT_TTL,
    PRICE_TTL,
    MOMENTUM_TTL,
    PORTFOLIO_TTL
)

from .decorators import (
    cached,
    cache_price,
    cache_momentum,
    cache_portfolio,
    invalidate_cache,
    CacheNamespace
)

__all__ = [
    # Cache instances
    'cache',
    'get_cache',
    'CacheService',
    'RedisCache',
    'InMemoryCache',
    
    # TTL constants
    'DEFAULT_TTL',
    'PRICE_TTL',
    'MOMENTUM_TTL',
    'PORTFOLIO_TTL',
    
    # Decorators
    'cached',
    'cache_price',
    'cache_momentum',
    'cache_portfolio',
    'invalidate_cache',
    'CacheNamespace',
]
