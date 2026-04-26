"""
Analytics API Endpoints (v1)

Portfolio analytics: correlation matrix, volatility term structure aggregates.
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel

from ...auth import get_current_user_id
from ...config.rate_limit_config import limiter, RateLimits

logger = logging.getLogger(__name__)

router = APIRouter()

# Minimum fraction of the requested window a ticker must have data for.
# Below this threshold we supplement with yfinance.
_MIN_COVERAGE = 0.6


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class CorrelationMatrixResponse(BaseModel):
    tickers: List[str]
    matrix: List[List[Optional[float]]]   # row-major, same order as tickers
    period_days: int
    start_date: str
    end_date: str
    data_points: int                       # trading days of overlapping returns used
    source: str                            # "db" | "yfinance" | "mixed"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db_config():
    from ...services.price_service import get_price_service
    svc = get_price_service()
    return getattr(svc, "db_config", None)


def _fetch_from_db(tickers: List[str], start: date, end: date, db_config) -> pd.DataFrame:
    """Query price_history for the given tickers. Returns close_price pivot."""
    from ...models.database import PriceHistory, SecurityMaster

    with db_config.get_session_context() as session:
        rows = (
            session.query(
                SecurityMaster.ticker,
                PriceHistory.price_date,
                PriceHistory.close_price,
            )
            .join(PriceHistory, PriceHistory.security_id == SecurityMaster.id)
            .filter(
                SecurityMaster.ticker.in_(tickers),
                PriceHistory.price_date >= start,
                PriceHistory.price_date <= end,
            )
            .order_by(PriceHistory.price_date)
            .all()
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["ticker", "price_date", "close_price"])
    df["close_price"] = df["close_price"].astype(float)
    return df.pivot(index="price_date", columns="ticker", values="close_price")


def _fetch_from_yfinance(tickers: List[str], start: date, end: date) -> pd.DataFrame:
    """Download adjusted close prices from yfinance."""
    import yfinance as yf
    raw = yf.download(
        tickers,
        start=start.isoformat(),
        end=end.isoformat(),
        auto_adjust=True,
        progress=False,
    )
    if raw.empty:
        return pd.DataFrame()

    # yfinance returns MultiIndex columns when len(tickers) > 1
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]].rename(columns={"Close": tickers[0]})

    closes.index = closes.index.date
    closes.index.name = "price_date"
    return closes


def _build_price_df(
    tickers: List[str], start: date, end: date, db_config
) -> tuple[pd.DataFrame, str]:
    """
    Return (prices_df, source).

    Strategy:
    1. Query DB for all tickers.
    2. Estimate expected trading days in the window (~70% of calendar days).
    3. For any ticker with coverage below _MIN_COVERAGE, supplement with yfinance.
    4. Return merged DataFrame and a source label.
    """
    expected_trading_days = max(10, int((end - start).days * 0.7))

    db_df = _fetch_from_db(tickers, start, end, db_config) if db_config else pd.DataFrame()

    # Identify which tickers need yfinance
    needs_yf = []
    for t in tickers:
        count = db_df[t].notna().sum() if (not db_df.empty and t in db_df.columns) else 0
        if count < expected_trading_days * _MIN_COVERAGE:
            needs_yf.append(t)

    if not needs_yf:
        return db_df, "db"

    logger.info(
        "Supplementing %d ticker(s) with yfinance for correlation: %s",
        len(needs_yf), needs_yf,
    )

    try:
        yf_df = _fetch_from_yfinance(needs_yf, start, end)
    except Exception as e:
        logger.warning("yfinance fallback failed: %s", e)
        yf_df = pd.DataFrame()

    if db_df.empty and yf_df.empty:
        return pd.DataFrame(), "none"

    if db_df.empty:
        return yf_df, "yfinance"

    if yf_df.empty:
        return db_df, "db"

    # Merge: yfinance fills in where DB is thin
    merged = db_df.copy()
    for t in needs_yf:
        if t in yf_df.columns:
            if t not in merged.columns:
                merged[t] = yf_df[t]
            else:
                # Prefer DB rows; fill gaps with yfinance
                merged[t] = merged[t].combine_first(yf_df[t])

    source = "mixed" if len(needs_yf) < len(tickers) else "yfinance"
    return merged, source


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/portfolios/{portfolio_id}/correlation-matrix",
    response_model=CorrelationMatrixResponse,
)
@limiter.limit(RateLimits.PUBLIC_API)
async def get_correlation_matrix(
    request: Request,
    response: Response,
    portfolio_id: int,
    days: int = Query(default=90, ge=30, le=365, description="Lookback period in calendar days"),
    user_id: int = Depends(get_current_user_id),
):
    """
    Return the pairwise Pearson correlation matrix for all portfolio holdings
    based on daily returns over the given lookback period.

    Prefers `price_history` in the database. Falls back to yfinance for any
    ticker whose DB coverage is below 60% of the expected trading days, then
    merges the two sources.

    Pairs with fewer than 20 overlapping return observations are set to null.

    **Rate Limit:** 100 requests/minute
    """
    db_config = _get_db_config()

    # 1. Resolve portfolio holdings
    try:
        from ...models.database import Holding, SecurityMaster, Portfolio
        if db_config is None:
            raise HTTPException(status_code=503, detail="Database not available")

        with db_config.get_session_context() as session:
            portfolio = session.query(Portfolio).filter_by(
                id=portfolio_id, user_id=user_id, is_active=True
            ).first()
            if portfolio is None:
                raise HTTPException(status_code=404, detail="Portfolio not found")

            holding_rows = (
                session.query(SecurityMaster.ticker)
                .join(Holding, Holding.security_id == SecurityMaster.id)
                .filter(Holding.portfolio_id == portfolio_id, Holding.shares > 0)
                .distinct()
                .all()
            )
            tickers = [r[0] for r in holding_rows]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching holdings for portfolio %d: %s", portfolio_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio holdings")

    if len(tickers) < 2:
        raise HTTPException(
            status_code=422,
            detail="Portfolio needs at least 2 holdings to compute correlations",
        )

    # 2. Fetch prices (DB + yfinance fallback)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    try:
        prices, source = _build_price_df(tickers, start_date, end_date, db_config)
    except Exception as e:
        logger.error("Error building price DataFrame: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch price history")

    if prices.empty:
        raise HTTPException(status_code=422, detail="No price history available for this portfolio")

    # 3. Require at least 20 data points per ticker (raise from 10 — 10 is too noisy)
    min_points = 20
    prices = prices.dropna(axis=1, thresh=min_points)
    if prices.shape[1] < 2:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient price history — need at least {min_points} trading days per ticker",
        )

    returns = prices.pct_change().dropna(how="all")

    # 4. Pearson correlation; require 20 overlapping observations per pair
    corr = returns.corr(method="pearson", min_periods=min_points)

    sorted_tickers = sorted(corr.columns.tolist())
    corr = corr.loc[sorted_tickers, sorted_tickers]

    matrix = []
    for ticker in sorted_tickers:
        row = []
        for other in sorted_tickers:
            val = corr.loc[ticker, other]
            row.append(None if pd.isna(val) else round(float(val), 4))
        matrix.append(row)

    actual_start = prices.index.min().isoformat() if not prices.empty else start_date.isoformat()
    actual_end = prices.index.max().isoformat() if not prices.empty else end_date.isoformat()

    return CorrelationMatrixResponse(
        tickers=sorted_tickers,
        matrix=matrix,
        period_days=days,
        start_date=actual_start,
        end_date=actual_end,
        data_points=len(returns.dropna(how="all")),
        source=source,
    )
