from pydantic import BaseModel
from typing import Optional

class MomentumScore(BaseModel):
    """Model for momentum score response"""
    ticker: str
    composite_score: float
    rating: str
    price_momentum: float
    technical_momentum: float
    fundamental_momentum: float
    relative_momentum: float

class StockData(BaseModel):
    """Model for basic stock data"""
    ticker: str
    price: float
    change: Optional[float] = None
    change_percent: Optional[float] = None