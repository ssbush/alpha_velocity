from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MomentumHistoryEntry(BaseModel):
    timestamp: str
    composite_score: float
    rating: str
    price_momentum: float
    technical_momentum: float
    fundamental_momentum: float
    relative_momentum: float

class PortfolioValueEntry(BaseModel):
    timestamp: str
    total_value: float
    average_momentum_score: float
    number_of_positions: int

class HoldingSnapshot(BaseModel):
    ticker: str
    shares: int
    market_value: str
    portfolio_percent: str
    momentum_score: float
    rating: str

class PortfolioCompositionEntry(BaseModel):
    timestamp: str
    holdings: List[HoldingSnapshot]

class PerformanceAnalytics(BaseModel):
    total_return: float
    daily_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    momentum_trend: str
    data_points: int = 0
    period_days: int = 0

class TopPerformer(BaseModel):
    ticker: str
    initial_score: float
    latest_score: float
    improvement: float
    improvement_percent: float
    latest_rating: str

class PortfolioHistory(BaseModel):
    values: List[PortfolioValueEntry]
    compositions: List[PortfolioCompositionEntry]
    analytics: Optional[PerformanceAnalytics] = None

class MomentumTrendData(BaseModel):
    ticker: str
    history: List[MomentumHistoryEntry]
    trend: str  # 'improving', 'declining', 'stable'
    current_score: float
    score_change: float