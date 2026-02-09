"""
Tests for Cache Service (backend/cache/redis_cache.py)

Covers InMemoryCache operations and cache service factory.
"""

import time
import pytest

from backend.cache.redis_cache import InMemoryCache, CacheService, get_cache


class TestInMemoryCache:
    """Tests for InMemoryCache fallback."""

    def test_set_and_get(self):
        cache = InMemoryCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None

    def test_delete_existing_key(self):
        cache = InMemoryCache()
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_nonexistent_key(self):
        cache = InMemoryCache()
        assert cache.delete("nothing") is False

    def test_exists_true(self):
        cache = InMemoryCache()
        cache.set("key1", "value1")
        assert cache.exists("key1") is True

    def test_exists_false(self):
        cache = InMemoryCache()
        assert cache.exists("nothing") is False

    def test_clear(self):
        cache = InMemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.clear() is True
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_keys_all(self):
        cache = InMemoryCache()
        cache.set("price:AAPL", 150)
        cache.set("price:NVDA", 450)
        cache.set("momentum:AAPL", 8.5)
        keys = cache.keys("*")
        assert len(keys) == 3

    def test_keys_pattern(self):
        cache = InMemoryCache()
        cache.set("price:AAPL", 150)
        cache.set("price:NVDA", 450)
        cache.set("momentum:AAPL", 8.5)
        keys = cache.keys("price:*")
        assert len(keys) == 2

    def test_info(self):
        cache = InMemoryCache()
        cache.set("a", 1)
        info = cache.info()
        assert info["cache_type"] == "in-memory"
        assert info["total_keys"] == 1

    def test_ttl_expiration(self):
        cache = InMemoryCache()
        cache.set("temp", "data", ttl=1)
        assert cache.get("temp") == "data"
        time.sleep(1.1)
        assert cache.get("temp") is None

    def test_set_without_ttl(self):
        cache = InMemoryCache()
        cache.set("persistent", "value")
        assert cache.get("persistent") == "value"

    def test_delete_removes_ttl(self):
        cache = InMemoryCache()
        cache.set("key", "val", ttl=300)
        cache.delete("key")
        assert cache.get("key") is None

    def test_stores_complex_types(self):
        cache = InMemoryCache()
        cache.set("dict_key", {"a": 1, "b": [2, 3]})
        result = cache.get("dict_key")
        assert result["a"] == 1
        assert result["b"] == [2, 3]


class TestCacheService:
    """Tests for CacheService wrapper."""

    def test_singleton(self):
        cs1 = CacheService()
        cs2 = CacheService()
        assert cs1 is cs2

    def test_uses_memory_backend(self):
        cs = CacheService()
        assert cs.is_memory() is True
        assert cs.is_redis() is False

    def test_get_set_via_service(self):
        cs = CacheService()
        cs.set("svc_key", "svc_val")
        assert cs.get("svc_key") == "svc_val"
        cs.delete("svc_key")

    def test_delete_via_service(self):
        cs = CacheService()
        cs.set("del_me", 123)
        assert cs.delete("del_me") is True
        assert cs.get("del_me") is None

    def test_exists_via_service(self):
        cs = CacheService()
        cs.set("exists_key", "yes")
        assert cs.exists("exists_key") is True
        assert cs.exists("nope_key") is False
        cs.delete("exists_key")

    def test_keys_via_service(self):
        cs = CacheService()
        cs.set("svc_a", 1)
        keys = cs.keys("*")
        assert isinstance(keys, list)
        cs.delete("svc_a")

    def test_info_via_service(self):
        cs = CacheService()
        info = cs.info()
        assert "cache_type" in info
        assert "total_keys" in info


class TestGetCache:
    """Tests for get_cache() factory."""

    def test_returns_cache_instance(self):
        cache = get_cache()
        assert cache is not None
        assert hasattr(cache, "get")
        assert hasattr(cache, "set")
        assert hasattr(cache, "delete")

    def test_returns_same_instance(self):
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2
