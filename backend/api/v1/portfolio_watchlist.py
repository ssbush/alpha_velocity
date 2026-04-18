"""
Portfolio Watchlist Endpoints (v1)

Endpoints for managing the manually curated, portfolio-scoped watchlist.
Separate from the auto-generated momentum watchlist.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from ...auth import get_current_user_id
from ...services.momentum_cache_service import MomentumCacheService
from ...services.portfolio_service import get_portfolio_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class WatchlistItem(BaseModel):
    ticker: str
    momentum_score: Optional[float] = None
    rating: Optional[str] = None
    added_at: Optional[str] = None
    category: Optional[str] = None


class WatchlistResponse(BaseModel):
    portfolio_id: int
    items: List[WatchlistItem]
    count: int


class AddTickersRequest(BaseModel):
    tickers: List[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db_config():
    from ...database.config import db_config
    return db_config


def _verify_portfolio_owner(session, portfolio_id: int, user_id: int):
    from ...models.database import Portfolio
    portfolio = session.query(Portfolio).filter_by(id=portfolio_id, user_id=user_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


def _enrich_with_scores(items: List[WatchlistItem]) -> List[WatchlistItem]:
    """Attach cached momentum scores to watchlist items."""
    try:
        portfolio_service = get_portfolio_service()
        mc = getattr(portfolio_service, 'momentum_cache_service', None)
        if mc is None:
            return items
        tickers = [i.ticker for i in items]
        found, _ = mc.get_scores_from_db(tickers)
        for item in items:
            if item.ticker in found:
                item.momentum_score = found[item.ticker].get('composite_score')
                item.rating = found[item.ticker].get('rating')
        # Sort highest score first; unscored tickers go to the bottom
        items.sort(key=lambda x: x.momentum_score or 0, reverse=True)
    except Exception as e:
        logger.warning("Could not enrich watchlist with scores: %s", e)
    return items


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{portfolio_id}/watchlist", response_model=WatchlistResponse)
async def get_watchlist(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Return the portfolio's manual watchlist with cached momentum scores and category info."""
    db = _get_db_config()
    from ...models.database import WatchlistTicker
    from sqlalchemy import text
    with db.get_session_context() as session:
        _verify_portfolio_owner(session, portfolio_id, user_id)
        rows = (
            session.query(WatchlistTicker)
            .filter_by(portfolio_id=portfolio_id)
            .order_by(WatchlistTicker.added_at)
            .all()
        )

        # Build ticker → category name map via category_securities join
        ticker_categories: dict = {}
        if rows:
            ticker_list = [r.ticker for r in rows]
            cat_rows = session.execute(
                text("""
                    SELECT cs.ticker, c.name
                    FROM category_securities cs
                    JOIN categories c ON c.id = cs.category_id
                    WHERE cs.ticker = ANY(:tickers)
                """),
                {"tickers": ticker_list},
            ).fetchall()
            for ticker, cat_name in cat_rows:
                ticker_categories[ticker] = cat_name

        items = [
            WatchlistItem(
                ticker=r.ticker,
                added_at=r.added_at.isoformat(),
                category=ticker_categories.get(r.ticker),
            )
            for r in rows
        ]

    items = _enrich_with_scores(items)
    return WatchlistResponse(portfolio_id=portfolio_id, items=items, count=len(items))


@router.post("/{portfolio_id}/watchlist", response_model=WatchlistResponse)
async def add_to_watchlist(
    portfolio_id: int,
    body: AddTickersRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Add one or more tickers to the portfolio watchlist (duplicates ignored)."""
    db = _get_db_config()
    from ...models.database import WatchlistTicker
    tickers = [t.strip().upper() for t in body.tickers if t.strip()]
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")

    with db.get_session_context() as session:
        _verify_portfolio_owner(session, portfolio_id, user_id)
        existing = {
            r.ticker for r in
            session.query(WatchlistTicker.ticker).filter_by(portfolio_id=portfolio_id).all()
        }
        for ticker in tickers:
            if ticker not in existing:
                session.add(WatchlistTicker(portfolio_id=portfolio_id, ticker=ticker))

    return await get_watchlist(portfolio_id=portfolio_id, user_id=user_id)


@router.delete("/{portfolio_id}/watchlist/{ticker}")
async def remove_from_watchlist(
    portfolio_id: int,
    ticker: str,
    user_id: int = Depends(get_current_user_id),
):
    """Remove a ticker from the portfolio watchlist."""
    db = _get_db_config()
    from ...models.database import WatchlistTicker
    ticker = ticker.upper()
    with db.get_session_context() as session:
        _verify_portfolio_owner(session, portfolio_id, user_id)
        deleted = (
            session.query(WatchlistTicker)
            .filter_by(portfolio_id=portfolio_id, ticker=ticker)
            .first()
        )
        if deleted:
            session.delete(deleted)
    return {"removed": ticker}


@router.post("/{portfolio_id}/watchlist/populate", response_model=WatchlistResponse)
async def populate_from_categories(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """
    Add all category tickers not already in the portfolio holdings to the watchlist.
    Existing watchlist entries are preserved; duplicates are ignored.
    """
    db = _get_db_config()
    from ...models.database import WatchlistTicker, Holding, SecurityMaster
    from sqlalchemy import text

    with db.get_session_context() as session:
        _verify_portfolio_owner(session, portfolio_id, user_id)

        # All tickers in any category
        category_tickers = {
            row[0] for row in
            session.execute(text("SELECT DISTINCT ticker FROM category_securities")).fetchall()
        }

        # Tickers already held in this portfolio
        held_tickers = {
            row[0] for row in
            session.query(SecurityMaster.ticker)
            .join(Holding, Holding.security_id == SecurityMaster.id)
            .filter(Holding.portfolio_id == portfolio_id)
            .all()
        }

        # Tickers already on the watchlist
        existing_watchlist = {
            r.ticker for r in
            session.query(WatchlistTicker.ticker).filter_by(portfolio_id=portfolio_id).all()
        }

        to_add = category_tickers - held_tickers - existing_watchlist
        for ticker in sorted(to_add):
            session.add(WatchlistTicker(portfolio_id=portfolio_id, ticker=ticker))

    return await get_watchlist(portfolio_id=portfolio_id, user_id=user_id)
