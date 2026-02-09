"""
Tests for Cache Decorators (backend/cache/decorators.py)

Covers cache_key(), @cached, @cache_price, @cache_momentum,
@cache_portfolio, @invalidate_cache, and CacheNamespace.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.cache.decorators import (
    cache_key,
    cached,
    cache_price,
    cache_momentum,
    cache_portfolio,
    invalidate_cache,
    CacheNamespace,
)


class TestCacheKey:
    """Tests for cache_key() hash generation."""

    def test_returns_string(self):
        result = cache_key("AAPL")
        assert isinstance(result, str)
        assert len(result) == 32  # MD5 hex digest

    def test_same_args_same_key(self):
        k1 = cache_key("AAPL", period="1y")
        k2 = cache_key("AAPL", period="1y")
        assert k1 == k2

    def test_different_args_different_key(self):
        k1 = cache_key("AAPL")
        k2 = cache_key("NVDA")
        assert k1 != k2

    def test_kwargs_order_independent(self):
        k1 = cache_key(a="1", b="2")
        k2 = cache_key(b="2", a="1")
        assert k1 == k2


class TestCachedDecorator:
    """Tests for @cached decorator."""

    def test_caches_result(self):
        call_count = 0

        @cached(ttl=300, key_prefix="test:")
        def expensive_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call — cache miss
        result1 = expensive_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call — cache hit
        result2 = expensive_func(5)
        assert result2 == 10
        assert call_count == 1  # Not called again

    def test_different_args_no_collision(self):
        @cached(ttl=300, key_prefix="test2:")
        def square(x):
            return x ** 2

        assert square(3) == 9
        assert square(4) == 16

    def test_has_clear_cache_attr(self):
        @cached(key_prefix="pfx:")
        def func():
            return 1

        assert hasattr(func, "clear_cache")
        assert callable(func.clear_cache)

    def test_has_cache_key_prefix_attr(self):
        @cached(key_prefix="pfx:")
        def func():
            return 1

        assert func.cache_key_prefix == "pfx:"

    def test_custom_key_func(self):
        @cached(key_func=lambda t: f"custom:{t}")
        def get_data(ticker):
            return {"ticker": ticker}

        result = get_data("AAPL")
        assert result["ticker"] == "AAPL"


class TestCachePriceDecorator:
    """Tests for @cache_price decorator."""

    def test_caches_price(self):
        call_count = 0

        @cache_price(ttl=60)
        def get_price(ticker):
            nonlocal call_count
            call_count += 1
            return 150.0

        assert get_price("AAPL") == 150.0
        assert get_price("AAPL") == 150.0
        assert call_count == 1

    def test_different_tickers_separate_keys(self):
        @cache_price(ttl=60)
        def get_price2(ticker):
            return {"AAPL": 150, "NVDA": 450}.get(ticker, 0)

        assert get_price2("AAPL") == 150
        assert get_price2("NVDA") == 450


class TestCacheMomentumDecorator:
    """Tests for @cache_momentum decorator."""

    def test_caches_momentum(self):
        call_count = 0

        @cache_momentum(ttl=120)
        def calc_momentum(ticker):
            nonlocal call_count
            call_count += 1
            return {"score": 8.5}

        assert calc_momentum("AAPL")["score"] == 8.5
        assert calc_momentum("AAPL")["score"] == 8.5
        assert call_count == 1


class TestCachePortfolioDecorator:
    """Tests for @cache_portfolio decorator."""

    def test_caches_portfolio(self):
        call_count = 0

        @cache_portfolio(ttl=60)
        def analyze(holdings):
            nonlocal call_count
            call_count += 1
            return {"total": 1000}

        holdings = {"AAPL": 10, "NVDA": 5}
        assert analyze(holdings)["total"] == 1000
        assert analyze(holdings)["total"] == 1000
        assert call_count == 1


class TestInvalidateCacheDecorator:
    """Tests for @invalidate_cache decorator."""

    def test_wraps_function(self):
        @invalidate_cache("test:*")
        def update_data():
            return "updated"

        assert update_data.__name__ == "update_data"

    def test_decorator_applies_without_error(self):
        # Just confirm the decorator can be applied
        @invalidate_cache("prices:*")
        def refresh():
            return {"refreshed": True}

        assert callable(refresh)


class TestCacheNamespace:
    """Tests for CacheNamespace context manager."""

    def test_enters_and_exits(self):
        with CacheNamespace("test") as ns:
            assert ns.namespace == "test"

    def test_has_cache_attr(self):
        with CacheNamespace("ns") as ns:
            assert ns.cache is not None
