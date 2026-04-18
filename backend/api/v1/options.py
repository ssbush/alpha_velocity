"""
Options API Endpoints (v1)

Endpoints for options data including implied volatility and IVR.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from typing import List, Optional

from ...services.iv_service import get_iv_service
from ...validators.validators import validate_ticker
from ...config.rate_limit_config import limiter, RateLimits

logger = logging.getLogger(__name__)

router = APIRouter()


class TermStructurePoint(BaseModel):
    expiry: str        # YYYY-MM-DD
    dte: int           # Days to expiry
    iv: float          # Annualized IV (e.g. 0.35 = 35%)


class TermStructureResponse(BaseModel):
    ticker: str
    spot: Optional[float] = None
    points: List[TermStructurePoint]   # Sorted by DTE ascending


class IVResponse(BaseModel):
    ticker: str
    iv: Optional[float]              # Current annualized IV (e.g. 0.65 = 65%)
    ivr: Optional[float]             # IV Rank 0–100
    signal: str                      # "Sell Premium" | "Neutral" | "Cheap Hedge" | "Earnings Soon — Skip" | "Insufficient data"
    iv_52w_low: Optional[float]
    iv_52w_high: Optional[float]
    data_points: int                 # Number of historical snapshots in DB
    last_updated: Optional[str]
    earnings_dte: Optional[int]      # Days until next earnings (None = unknown)
    earnings_warning: bool           # True when earnings within 7 days


@router.get("/iv/{ticker}", response_model=IVResponse)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_iv(request: Request, response: Response, ticker: str):
    """
    Get current implied volatility and IV Rank (IVR) for a ticker.

    **IVR interpretation:**
    - IVR >= 50: Premium is elevated — good time to sell puts/calls
    - IVR 30–49: Neutral — IV is near average
    - IVR < 30: Premium is cheap — good time to buy protective puts

    **Note:** IVR accuracy improves as the iv_history table accumulates
    snapshots over time. Early calls will show `ivr: null` until enough
    history is recorded.

    **Rate Limit:** 100 requests/minute
    """
    ticker = validate_ticker(ticker)

    try:
        iv_svc = get_iv_service()
        data = iv_svc.get_iv_data(ticker)
        return IVResponse(**data)
    except Exception as e:
        logger.error("Error fetching IV for %s: %s", ticker, e)
        raise HTTPException(status_code=502, detail="Options data unavailable")


@router.get("/term-structure/{ticker}", response_model=TermStructureResponse)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_term_structure(request: Request, response: Response, ticker: str):
    """
    Return ATM implied volatility for every available expiry between 7 and 365 DTE.

    Useful for visualising the volatility term structure (contango / backwardation).

    **Rate Limit:** 100 requests/minute
    """
    ticker = validate_ticker(ticker)

    try:
        iv_svc = get_iv_service()
        points = iv_svc.get_term_structure(ticker)
        return TermStructureResponse(ticker=ticker, points=points)
    except Exception as e:
        logger.error("Error fetching term structure for %s: %s", ticker, e)
        raise HTTPException(status_code=502, detail="Options data unavailable")
