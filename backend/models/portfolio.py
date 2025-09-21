from pydantic import BaseModel
from typing import Dict, List, Optional

class PortfolioHolding(BaseModel):
    """Model for individual portfolio holding"""
    ticker: str
    shares: int
    price: str
    market_value: str
    portfolio_percent: str
    momentum_score: float
    rating: str
    price_momentum: float
    technical_momentum: float

class PortfolioAnalysis(BaseModel):
    """Model for complete portfolio analysis"""
    holdings: List[PortfolioHolding]
    total_value: float
    average_momentum_score: float
    number_of_positions: int

class CategoryInfo(BaseModel):
    """Model for portfolio category information"""
    name: str
    tickers: List[str]
    target_allocation: float
    benchmark: str

class CategoryAnalysis(BaseModel):
    """Model for category analysis"""
    category: str
    target_allocation: float
    benchmark: str
    tickers: List[str]
    momentum_scores: List[Dict]
    average_score: float

class Portfolio(BaseModel):
    """Model for portfolio holdings"""
    holdings: Dict[str, int]  # ticker: shares