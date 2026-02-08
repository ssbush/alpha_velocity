"""
Concurrent Operations Utilities

Provides utilities for concurrent/parallel API calls and batch processing.
Dramatically speeds up operations that fetch data for multiple tickers.
"""

import asyncio
import logging
from typing import List, Callable, Any, Optional, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MAX_WORKERS = 10
DEFAULT_BATCH_SIZE = 20
DEFAULT_TIMEOUT = 30


class ConcurrentProcessor:
    """
    Concurrent processor for batch operations.
    
    Handles parallel execution with error handling, rate limiting,
    and progress tracking.
    """
    
    def __init__(
        self,
        max_workers: int = DEFAULT_MAX_WORKERS,
        timeout: Optional[int] = DEFAULT_TIMEOUT,
        rate_limit: Optional[int] = None
    ):
        """
        Initialize concurrent processor.
        
        Args:
            max_workers: Maximum number of concurrent workers
            timeout: Timeout per operation in seconds
            rate_limit: Maximum operations per second (None = no limit)
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.rate_limit = rate_limit
        self._last_call_time = 0
    
    def _rate_limit_delay(self):
        """Apply rate limiting delay if configured"""
        if self.rate_limit is None:
            return
        
        min_interval = 1.0 / self.rate_limit
        elapsed = time.time() - self._last_call_time
        
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        
        self._last_call_time = time.time()
    
    def process_batch(
        self,
        items: List[Any],
        func: Callable,
        *args,
        **kwargs
    ) -> Dict[Any, Any]:
        """
        Process items concurrently using ThreadPoolExecutor.
        
        Args:
            items: List of items to process
            func: Function to apply to each item
            *args, **kwargs: Additional arguments to pass to func
        
        Returns:
            Dictionary mapping item -> result
        
        Example:
            processor = ConcurrentProcessor(max_workers=10)
            tickers = ['AAPL', 'NVDA', 'MSFT']
            results = processor.process_batch(tickers, get_stock_price)
        """
        results = {}
        errors = {}
        
        logger.info(f"Processing {len(items)} items with {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(func, item, *args, **kwargs): item
                for item in items
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_item, timeout=self.timeout):
                item = future_to_item[future]
                
                try:
                    self._rate_limit_delay()
                    result = future.result()
                    results[item] = result
                    
                except Exception as e:
                    logger.error(f"Error processing {item}: {e}")
                    errors[item] = str(e)
        
        logger.info(
            f"Completed batch processing: "
            f"{len(results)} successful, {len(errors)} failed"
        )
        
        return results, errors
    
    def process_batch_with_retries(
        self,
        items: List[Any],
        func: Callable,
        max_retries: int = 3,
        *args,
        **kwargs
    ) -> Dict[Any, Any]:
        """
        Process items with automatic retries on failure.
        
        Args:
            items: List of items to process
            func: Function to apply to each item
            max_retries: Maximum retry attempts per item
            *args, **kwargs: Additional arguments
        
        Returns:
            Dictionary mapping item -> result
        """
        results = {}
        errors = {}
        remaining_items = list(items)
        
        for retry in range(max_retries + 1):
            if not remaining_items:
                break
            
            logger.info(
                f"Processing batch (attempt {retry + 1}/{max_retries + 1}): "
                f"{len(remaining_items)} items"
            )
            
            batch_results, batch_errors = self.process_batch(
                remaining_items, func, *args, **kwargs
            )
            
            results.update(batch_results)
            
            if retry < max_retries:
                # Retry failed items
                remaining_items = list(batch_errors.keys())
                if remaining_items:
                    logger.info(f"Retrying {len(remaining_items)} failed items")
                    time.sleep(1)  # Brief delay before retry
            else:
                # Final attempt, record errors
                errors.update(batch_errors)
        
        return results, errors


async def run_concurrent_async(
    tasks: List[Callable],
    max_concurrent: int = 10
) -> List[Any]:
    """
    Run async tasks concurrently with concurrency limit.
    
    Args:
        tasks: List of async functions to execute
        max_concurrent: Maximum concurrent tasks
    
    Returns:
        List of results
    
    Example:
        async def fetch_data(ticker):
            return await api.get(ticker)
        
        tasks = [fetch_data(t) for t in tickers]
        results = await run_concurrent_async(tasks, max_concurrent=10)
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def bounded_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*[bounded_task(task) for task in tasks])


def batch_process_tickers(
    tickers: List[str],
    func: Callable,
    max_workers: int = DEFAULT_MAX_WORKERS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    show_progress: bool = True
) -> Dict[str, Any]:
    """
    Process tickers in batches with progress tracking.
    
    Args:
        tickers: List of ticker symbols
        func: Function to apply to each ticker
        max_workers: Maximum concurrent workers
        batch_size: Number of tickers per batch
        show_progress: Whether to log progress
    
    Returns:
        Dictionary mapping ticker -> result
    
    Example:
        def get_price(ticker):
            return yfinance.Ticker(ticker).info['currentPrice']
        
        prices = batch_process_tickers(
            ['AAPL', 'NVDA', 'MSFT'],
            get_price,
            max_workers=10
        )
    """
    processor = ConcurrentProcessor(max_workers=max_workers)
    all_results = {}
    all_errors = {}
    
    # Split into batches
    batches = [
        tickers[i:i + batch_size]
        for i in range(0, len(tickers), batch_size)
    ]
    
    logger.info(
        f"Processing {len(tickers)} tickers in {len(batches)} batches "
        f"(batch_size={batch_size}, workers={max_workers})"
    )
    
    for batch_num, batch in enumerate(batches, 1):
        if show_progress:
            logger.info(f"Processing batch {batch_num}/{len(batches)} ({len(batch)} tickers)")
        
        results, errors = processor.process_batch(batch, func)
        all_results.update(results)
        all_errors.update(errors)
        
        if show_progress:
            success_rate = len(results) / len(batch) * 100
            logger.info(
                f"Batch {batch_num} complete: "
                f"{len(results)}/{len(batch)} successful ({success_rate:.1f}%)"
            )
    
    total_success = len(all_results)
    total_failed = len(all_errors)
    success_rate = total_success / len(tickers) * 100
    
    logger.info(
        f"Processing complete: {total_success}/{len(tickers)} successful "
        f"({success_rate:.1f}%), {total_failed} failed"
    )
    
    return all_results, all_errors


def parallel_map(
    func: Callable,
    items: List[Any],
    max_workers: int = DEFAULT_MAX_WORKERS
) -> List[Any]:
    """
    Parallel map function using ThreadPoolExecutor.
    
    Args:
        func: Function to apply to each item
        items: List of items
        max_workers: Maximum concurrent workers
    
    Returns:
        List of results in same order as items
    
    Example:
        prices = parallel_map(get_stock_price, tickers, max_workers=10)
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(func, items))


def timed_concurrent_execution(
    func: Callable,
    items: List[Any],
    max_workers: int = DEFAULT_MAX_WORKERS
) -> Tuple[Dict[Any, Any], float]:
    """
    Execute function concurrently and measure time.
    
    Args:
        func: Function to execute
        items: List of items to process
        max_workers: Maximum concurrent workers
    
    Returns:
        Tuple of (results, execution_time_seconds)
    
    Example:
        results, elapsed = timed_concurrent_execution(
            calculate_momentum,
            tickers,
            max_workers=10
        )
        print(f"Processed {len(tickers)} in {elapsed:.2f}s")
    """
    start_time = time.time()
    
    processor = ConcurrentProcessor(max_workers=max_workers)
    results, errors = processor.process_batch(items, func)
    
    elapsed = time.time() - start_time
    
    return results, elapsed


class BatchIterator:
    """
    Iterator for processing items in batches.
    
    Useful for streaming large datasets without loading everything into memory.
    
    Example:
        for batch in BatchIterator(all_tickers, batch_size=20):
            results = process_batch(batch)
            save_results(results)
    """
    
    def __init__(self, items: List[Any], batch_size: int = DEFAULT_BATCH_SIZE):
        self.items = items
        self.batch_size = batch_size
        self.current_index = 0
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.current_index >= len(self.items):
            raise StopIteration
        
        batch = self.items[self.current_index:self.current_index + self.batch_size]
        self.current_index += self.batch_size
        
        return batch


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks of specified size.
    
    Args:
        items: List to split
        chunk_size: Size of each chunk
    
    Returns:
        List of chunks
    
    Example:
        chunks = chunk_list([1, 2, 3, 4, 5], chunk_size=2)
        # Returns: [[1, 2], [3, 4], [5]]
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


class RateLimiter:
    """
    Rate limiter for controlling API call frequency.
    
    Example:
        limiter = RateLimiter(calls_per_second=10)
        
        for ticker in tickers:
            with limiter:
                data = fetch_data(ticker)
    """
    
    def __init__(self, calls_per_second: float):
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
    
    def __enter__(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.last_call = time.time()
    
    async def __aenter__(self):
        return self.__enter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)
