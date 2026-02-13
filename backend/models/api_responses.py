"""
Pydantic response models for v1 API endpoints.

Provides typed responses for OpenAPI documentation and response validation.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# --- Metrics responses ---

class PerformanceMetricsResponse(BaseModel):
    data: Dict[str, Any]


class MetricsResetResponse(BaseModel):
    message: str


class EndpointSummaryResponse(BaseModel):
    summary: Dict[str, Any]
    endpoints: List[Dict[str, Any]]


class SlowEndpointsResponse(BaseModel):
    threshold_ms: float
    count: int
    endpoints: List[Dict[str, Any]]


# --- Cache responses ---

class CacheStatusResponse(BaseModel):
    status: str
    type: str
    cached_prices: int = 0


class CacheClearResponse(BaseModel):
    message: str
    items_cleared: int = 0


class CacheInfoResponse(BaseModel):
    cache_type: str
    total_keys: int = 0
    memory_usage: Optional[str] = None
    is_redis: bool = False
    is_memory: bool = True


class CacheKeysResponse(BaseModel):
    pattern: str
    count: int
    keys: List[str]


class CacheClearPatternResponse(BaseModel):
    message: str
    pattern: str
    keys_cleared: int


class CacheWarmupResponse(BaseModel):
    message: str
    tickers_processed: int
    successfully_cached: int
    tickers: List[str]


# --- Momentum responses ---

class TopMomentumResponse(BaseModel):
    limit: int
    stocks: List[Dict[str, Any]]
    total_portfolio_stocks: Optional[int] = None
    category: Optional[str] = None


class BatchTopResponse(BaseModel):
    total_analyzed: int
    top_count: int
    execution_time_seconds: float
    top_stocks: List[Dict[str, Any]]


class ConcurrentCompareResponse(BaseModel):
    tickers_processed: int
    sequential_time_seconds: float
    concurrent_time_seconds: float
    speedup_factor: float
    improvement_percent: float
    max_workers_used: int
    recommendation: str
