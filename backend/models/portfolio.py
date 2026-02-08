from pydantic import BaseModel, validator, Field
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

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
    holdings: Dict[str, int] = Field(..., description="Portfolio holdings: ticker -> shares")

    @validator('holdings')
    def validate_holdings(cls, v):
        """Validate portfolio holdings"""
        from ..validators.validators import validate_ticker, validate_shares

        if not v:
            raise ValueError("Portfolio cannot be empty")

        if not isinstance(v, dict):
            raise ValueError("Holdings must be a dictionary")

        # Limit number of holdings
        if len(v) > 1000:
            raise ValueError("Portfolio cannot exceed 1000 holdings")

        validated_holdings = {}

        for ticker, shares in v.items():
            # Validate ticker symbol
            try:
                validated_ticker = validate_ticker(ticker)
            except ValueError as e:
                logger.warning(f"Invalid ticker in portfolio: {ticker}")
                raise ValueError(f"Invalid ticker '{ticker}': {str(e)}")

            # Validate shares
            try:
                validated_shares = validate_shares(shares, allow_fractional=True)
                # Convert back to int/float for the model
                validated_holdings[validated_ticker] = float(validated_shares)
            except ValueError as e:
                logger.warning(f"Invalid shares for {ticker}: {shares}")
                raise ValueError(f"Invalid shares for '{ticker}': {str(e)}")

        return validated_holdings