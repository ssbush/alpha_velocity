from pydantic import BaseModel
from typing import List, Dict, Optional
from .portfolio import PortfolioHolding
from .historical import PerformanceAnalytics

class PortfolioSummary(BaseModel):
    portfolio_id: str
    name: str
    total_value: float
    average_momentum_score: float
    number_of_positions: int
    top_holdings: List[PortfolioHolding]
    performance: Optional[PerformanceAnalytics] = None

class AllocationComparison(BaseModel):
    category: str
    portfolio_a_percent: float
    portfolio_b_percent: float
    difference: float
    target_percent: float
    portfolio_a_gap: float
    portfolio_b_gap: float

class HoldingComparison(BaseModel):
    ticker: str
    in_portfolio_a: bool
    in_portfolio_b: bool
    portfolio_a_weight: Optional[float] = None
    portfolio_b_weight: Optional[float] = None
    portfolio_a_score: Optional[float] = None
    portfolio_b_score: Optional[float] = None
    weight_difference: Optional[float] = None
    score_difference: Optional[float] = None

class PerformanceComparison(BaseModel):
    metric: str
    portfolio_a_value: float
    portfolio_b_value: float
    difference: float
    winner: str  # 'portfolio_a', 'portfolio_b', or 'tie'

class DiversificationMetrics(BaseModel):
    portfolio_id: str
    concentration_ratio: float  # Top 5 holdings weight
    sector_count: int
    average_position_size: float
    largest_position_percent: float

class PortfolioComparison(BaseModel):
    portfolio_a: PortfolioSummary
    portfolio_b: PortfolioSummary
    allocation_comparison: List[AllocationComparison]
    holding_comparison: List[HoldingComparison]
    performance_comparison: List[PerformanceComparison]
    diversification_a: DiversificationMetrics
    diversification_b: DiversificationMetrics
    recommendation: str
    key_differences: List[str]
    comparison_date: str