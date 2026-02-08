"""
Redis Cache Service

Provides Redis-based caching for expensive operations:
- Price data from yfinance
- Momentum score calculations
- Portfolio analysis results
- Category data

Supports both Redis and in-memory fallback.
"""

import os
import json
import logging
import pickle
from typing import Any, Optional, Union, Callable
from functools import wraps
from datetime import timedelta

logger = logging.getLogger(__name__)

# Cache configuration from environment
REDIS_ENABLED = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_PREFIX = os.getenv('REDIS_PREFIX', 'alphavelocity:')

# Default TTL values (in seconds)
DEFAULT_TTL = int(os.getenv('CACHE_DEFAULT_TTL', '3600'))  # 1 hour
PRICE_TTL = int(os.getenv('CACHE_PRICE_TTL', '300'))  # 5 minutes
MOMENTUM_TTL = int(os.getenv('CACHE_MOMENTUM_TTL', '1800'))  # 30 minutes
PORTFOLIO_TTL = int(os.getenv('CACHE_PORTFOLIO_TTL', '600'))  # 10 minutes


class InMemoryCache:
    """
    Fallback in-memory cache when Redis is not available.
    
    Simple dict-based cache with basic TTL support.
    Not suitable for production with multiple workers.
    """
    
    def __init__(self):
        self._cache = {}
        self._ttls = {}
        logger.info("Initialized in-memory cache (fallback mode)")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        import time
        
        if key not in self._cache:
            return None
        
        # Check TTL
        if key in self._ttls:
            if time.time() > self._ttls[key]:
                # Expired
                del self._cache[key]
                del self._ttls[key]
                return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        import time
        
        self._cache[key] = value
        
        if ttl:
            self._ttls[key] = time.time() + ttl
        
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
            if key in self._ttls:
                del self._ttls[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self.get(key) is not None
    
    def clear(self) -> bool:
        """Clear all cache"""
        self._cache.clear()
        self._ttls.clear()
        return True
    
    def keys(self, pattern: str = "*") -> list:
        """Get all keys matching pattern"""
        if pattern == "*":
            return list(self._cache.keys())
        
        # Simple pattern matching
        import re
        regex = pattern.replace("*", ".*")
        return [k for k in self._cache.keys() if re.match(regex, k)]
    
    def info(self) -> dict:
        """Get cache info"""
        return {
            'cache_type': 'in-memory',
            'total_keys': len(self._cache),
            'memory_usage': 'N/A'
        }


class RedisCache:
    """
    Redis cache service with connection pooling and error handling.
    
    Provides high-performance distributed caching for production.
    """
    
    def __init__(self):
        """Initialize Redis connection"""
        try:
            import redis
            
            self.redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=False,  # Handle binary data
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.redis.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key"""
        return f"{REDIS_PREFIX}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache.
        
        Automatically deserializes pickled objects.
        """
        try:
            full_key = self._make_key(key)
            value = self.redis.get(full_key)
            
            if value is None:
                return None
            
            # Try to unpickle
            try:
                return pickle.loads(value)
            except:
                # If unpickling fails, return as string
                return value.decode('utf-8') if isinstance(value, bytes) else value
                
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in Redis cache with optional TTL.
        
        Automatically pickles complex objects.
        """
        try:
            full_key = self._make_key(key)
            
            # Pickle the value
            pickled_value = pickle.dumps(value)
            
            if ttl:
                self.redis.setex(full_key, ttl, pickled_value)
            else:
                self.redis.set(full_key, pickled_value)
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            full_key = self._make_key(key)
            self.redis.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            full_key = self._make_key(key)
            return self.redis.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Error checking key {key} in Redis: {e}")
            return False
    
    def clear(self, pattern: str = "*") -> bool:
        """
        Clear keys matching pattern.
        
        Warning: Use carefully in production.
        """
        try:
            full_pattern = self._make_key(pattern)
            keys = self.redis.keys(full_pattern)
            
            if keys:
                self.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} keys matching {pattern}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def keys(self, pattern: str = "*") -> list:
        """Get all keys matching pattern"""
        try:
            full_pattern = self._make_key(pattern)
            keys = self.redis.keys(full_pattern)
            
            # Remove prefix from keys
            prefix_len = len(REDIS_PREFIX)
            return [k.decode('utf-8')[prefix_len:] if isinstance(k, bytes) else k[prefix_len:] for k in keys]
            
        except Exception as e:
            logger.error(f"Error getting keys: {e}")
            return []
    
    def info(self) -> dict:
        """Get Redis server info"""
        try:
            info = self.redis.info()
            return {
                'cache_type': 'redis',
                'redis_version': info.get('redis_version'),
                'total_keys': self.redis.dbsize(),
                'memory_usage': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients')
            }
        except Exception as e:
            logger.error(f"Error getting Redis info: {e}")
            return {'cache_type': 'redis', 'error': str(e)}
    
    def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return self.redis.ping()
        except:
            return False


class CacheService:
    """
    Unified cache service with automatic fallback.
    
    Tries Redis first, falls back to in-memory cache if Redis unavailable.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize cache service"""
        if self._initialized:
            return
        
        self.backend = None
        self.cache_type = 'none'
        
        # Try Redis first if enabled
        if REDIS_ENABLED:
            try:
                self.backend = RedisCache()
                self.cache_type = 'redis'
                logger.info("Cache service using Redis backend")
            except Exception as e:
                logger.warning(f"Redis not available, falling back to in-memory cache: {e}")
                self.backend = InMemoryCache()
                self.cache_type = 'memory'
        else:
            # Use in-memory cache
            self.backend = InMemoryCache()
            self.cache_type = 'memory'
            logger.info("Cache service using in-memory backend")
        
        self._initialized = True
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        return self.backend.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        return self.backend.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        return self.backend.delete(key)
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self.backend.exists(key)
    
    def clear(self, pattern: str = "*") -> bool:
        """Clear cache"""
        return self.backend.clear(pattern)
    
    def keys(self, pattern: str = "*") -> list:
        """Get all keys"""
        return self.backend.keys(pattern)
    
    def info(self) -> dict:
        """Get cache info"""
        return self.backend.info()
    
    def is_redis(self) -> bool:
        """Check if using Redis backend"""
        return self.cache_type == 'redis'
    
    def is_memory(self) -> bool:
        """Check if using in-memory backend"""
        return self.cache_type == 'memory'


# Global cache instance
cache = CacheService()


def get_cache() -> CacheService:
    """Get global cache instance"""
    return cache
