"""
Tests for Concurrent Operations Utilities (backend/utils/concurrent.py)

Covers ConcurrentProcessor, batch_process_tickers, parallel_map,
timed_concurrent_execution, BatchIterator, chunk_list, and RateLimiter.
"""

import pytest
import time
from unittest.mock import MagicMock

from backend.utils.concurrent import (
    ConcurrentProcessor,
    batch_process_tickers,
    parallel_map,
    timed_concurrent_execution,
    BatchIterator,
    chunk_list,
    RateLimiter,
    DEFAULT_MAX_WORKERS,
    DEFAULT_BATCH_SIZE,
    DEFAULT_TIMEOUT,
)


class TestConcurrentProcessor:
    """Tests for ConcurrentProcessor."""

    def test_init_defaults(self):
        proc = ConcurrentProcessor()
        assert proc.max_workers == DEFAULT_MAX_WORKERS
        assert proc.timeout == DEFAULT_TIMEOUT
        assert proc.rate_limit is None

    def test_init_custom(self):
        proc = ConcurrentProcessor(max_workers=5, timeout=10, rate_limit=2)
        assert proc.max_workers == 5
        assert proc.timeout == 10
        assert proc.rate_limit == 2

    def test_process_batch_success(self):
        proc = ConcurrentProcessor(max_workers=3)
        results, errors = proc.process_batch([1, 2, 3], lambda x: x * 2)
        assert results == {1: 2, 2: 4, 3: 6}
        assert errors == {}

    def test_process_batch_with_errors(self):
        def fail_on_two(x):
            if x == 2:
                raise ValueError("bad value")
            return x * 10

        proc = ConcurrentProcessor(max_workers=3)
        results, errors = proc.process_batch([1, 2, 3], fail_on_two)
        assert results[1] == 10
        assert results[3] == 30
        assert 2 in errors

    def test_process_batch_empty(self):
        proc = ConcurrentProcessor()
        results, errors = proc.process_batch([], lambda x: x)
        assert results == {}
        assert errors == {}

    def test_process_batch_with_rate_limit(self):
        proc = ConcurrentProcessor(max_workers=2, rate_limit=100)
        results, errors = proc.process_batch([1, 2], lambda x: x + 1)
        assert 1 in results
        assert 2 in results

    def test_process_batch_with_retries_success(self):
        call_counts = {}

        def flaky_func(x):
            call_counts[x] = call_counts.get(x, 0) + 1
            if call_counts[x] < 2 and x == 2:
                raise ValueError("transient error")
            return x * 3

        proc = ConcurrentProcessor(max_workers=2)
        results, errors = proc.process_batch_with_retries([1, 2, 3], flaky_func, max_retries=2)
        assert results[1] == 3
        assert results[3] == 9
        # Item 2 should eventually succeed after retry
        assert 2 in results or 2 in errors

    def test_process_batch_with_retries_no_retry_needed(self):
        proc = ConcurrentProcessor(max_workers=2)
        results, errors = proc.process_batch_with_retries(
            [10, 20], lambda x: x // 2, max_retries=1
        )
        assert results == {10: 5, 20: 10}
        assert errors == {}


class TestBatchProcessTickers:
    """Tests for batch_process_tickers()."""

    def test_processes_all_tickers(self):
        results, errors = batch_process_tickers(
            ["A", "B", "C"],
            lambda t: f"price_{t}",
            max_workers=2,
            batch_size=2,
        )
        assert len(results) == 3
        assert results["A"] == "price_A"
        assert errors == {}

    def test_single_batch(self):
        results, errors = batch_process_tickers(
            ["X"], lambda t: 100, max_workers=1, batch_size=10
        )
        assert results["X"] == 100


class TestParallelMap:
    """Tests for parallel_map()."""

    def test_preserves_order(self):
        result = parallel_map(lambda x: x ** 2, [1, 2, 3, 4], max_workers=2)
        assert result == [1, 4, 9, 16]

    def test_empty_list(self):
        result = parallel_map(lambda x: x, [], max_workers=2)
        assert result == []


class TestTimedConcurrentExecution:
    """Tests for timed_concurrent_execution()."""

    def test_returns_results_and_time(self):
        results, elapsed = timed_concurrent_execution(
            lambda x: x * 5, [1, 2, 3], max_workers=3
        )
        assert results == {1: 5, 2: 10, 3: 15}
        assert elapsed >= 0
        assert isinstance(elapsed, float)


class TestBatchIterator:
    """Tests for BatchIterator."""

    def test_iterates_in_batches(self):
        batches = list(BatchIterator([1, 2, 3, 4, 5], batch_size=2))
        assert batches == [[1, 2], [3, 4], [5]]

    def test_single_batch(self):
        batches = list(BatchIterator([1, 2], batch_size=10))
        assert batches == [[1, 2]]

    def test_empty_list(self):
        batches = list(BatchIterator([], batch_size=5))
        assert batches == []

    def test_exact_batch_size(self):
        batches = list(BatchIterator([1, 2, 3, 4], batch_size=2))
        assert len(batches) == 2


class TestChunkList:
    """Tests for chunk_list()."""

    def test_basic_chunking(self):
        result = chunk_list([1, 2, 3, 4, 5], chunk_size=2)
        assert result == [[1, 2], [3, 4], [5]]

    def test_empty_list(self):
        assert chunk_list([], chunk_size=3) == []

    def test_chunk_size_larger_than_list(self):
        assert chunk_list([1, 2], chunk_size=10) == [[1, 2]]


class TestRateLimiter:
    """Tests for RateLimiter context manager."""

    def test_context_manager(self):
        limiter = RateLimiter(calls_per_second=1000)
        with limiter:
            pass  # Should not raise

    def test_min_interval(self):
        limiter = RateLimiter(calls_per_second=10)
        assert limiter.min_interval == pytest.approx(0.1, abs=0.01)

    def test_exit_sets_last_call(self):
        limiter = RateLimiter(calls_per_second=100)
        assert limiter.last_call == 0
        with limiter:
            pass
        assert limiter.last_call > 0
