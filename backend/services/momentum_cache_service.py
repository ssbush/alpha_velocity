"""
Momentum Cache Service — 3-tier caching for momentum scores.

Tier 1: In-memory cache (momentum_engine._cache, 24h TTL)
Tier 2: PostgreSQL (momentum_scores + price_history tables)
Tier 3: Live yfinance via momentum_engine.calculate_momentum_score()
"""

import asyncio
import logging
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.database import MomentumScore, PriceHistory, SecurityMaster

logger = logging.getLogger(__name__)


class MomentumCacheService:
    """3-tier momentum score cache: memory → PostgreSQL → yfinance."""

    def __init__(self, momentum_engine, db_config=None):
        self.momentum_engine = momentum_engine
        self.db_config = db_config

    def get_scores_from_db(self, tickers: List[str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        """Synchronous Tier 1 + Tier 2 only lookup (no yfinance).

        Returns:
            (found, missing) where found is {ticker: score_dict} and
            missing is list of tickers not found in either tier.
        """
        data: Dict[str, Dict[str, Any]] = {}
        remaining = self._check_memory_cache(list(tickers), data)
        if not remaining:
            return data, []

        if self.db_config is not None:
            remaining = self._check_database(remaining, data)

        return data, remaining

    async def get_batch_scores(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch momentum scores for a batch of tickers using 3-tier cache."""
        data: Dict[str, Dict[str, Any]] = {}
        remaining = list(tickers)

        # --- Tier 1: In-memory cache ---
        remaining = self._check_memory_cache(remaining, data)
        if not remaining:
            return data

        # --- Tier 2: PostgreSQL ---
        if self.db_config is not None:
            remaining = self._check_database(remaining, data)
            if not remaining:
                return data

        # --- Tier 3: Live yfinance ---
        if remaining:
            await self._compute_live(remaining, data)

        return data

    def _check_memory_cache(
        self, tickers: List[str], data: Dict[str, Dict]
    ) -> List[str]:
        """Check momentum_engine._cache for each ticker. Returns still-missing tickers."""
        missing = []
        now = time.time()
        for ticker in tickers:
            cache_key = f"momentum_{ticker}"
            entry = self.momentum_engine._cache.get(cache_key)
            if entry is not None:
                cached_data, cache_time = entry
                if now - cache_time < self.momentum_engine._cache_ttl:
                    data[ticker] = dict(cached_data)
                    continue
            missing.append(ticker)
        return missing

    def _check_database(
        self, tickers: List[str], data: Dict[str, Dict]
    ) -> List[str]:
        """Query PostgreSQL for most recent momentum scores + prices."""
        missing = []
        try:
            with self.db_config.get_session_context() as session:
                scores_by_ticker = self._query_latest_scores(session, tickers)
                prices_by_ticker = self._query_latest_prices(session, tickers)

                now = time.time()
                for ticker in tickers:
                    score_row = scores_by_ticker.get(ticker)
                    if score_row is None:
                        missing.append(ticker)
                        continue

                    entry = {
                        "ticker": ticker,
                        "composite_score": float(score_row.composite_score),
                        "rating": score_row.rating or self._score_to_rating(
                            float(score_row.composite_score)
                        ),
                        "price_momentum": float(score_row.price_momentum or 0),
                        "technical_momentum": float(score_row.technical_momentum or 0),
                        "fundamental_momentum": float(
                            score_row.fundamental_momentum or 0
                        ),
                        "relative_momentum": float(score_row.relative_momentum or 0),
                        "current_price": float(prices_by_ticker[ticker])
                        if ticker in prices_by_ticker
                        else 0.0,
                    }
                    data[ticker] = entry

                    # Backfill Tier 1 so subsequent requests are instant
                    cache_key = f"momentum_{ticker}"
                    self.momentum_engine._cache[cache_key] = (entry, now)

        except Exception:
            logger.warning("Tier 2 DB lookup failed, falling back to Tier 3", exc_info=True)
            missing = [t for t in tickers if t not in data]

        return missing

    def _query_latest_scores(
        self, session: Session, tickers: List[str]
    ) -> Dict[str, MomentumScore]:
        """Get the most recent MomentumScore row per ticker."""
        # Subquery: max score_date per security_id for the requested tickers
        subq = (
            session.query(
                MomentumScore.security_id,
                func.max(MomentumScore.score_date).label("max_date"),
            )
            .join(SecurityMaster, MomentumScore.security_id == SecurityMaster.id)
            .filter(SecurityMaster.ticker.in_(tickers))
            .group_by(MomentumScore.security_id)
            .subquery()
        )

        rows = (
            session.query(MomentumScore, SecurityMaster.ticker)
            .join(SecurityMaster, MomentumScore.security_id == SecurityMaster.id)
            .join(
                subq,
                (MomentumScore.security_id == subq.c.security_id)
                & (MomentumScore.score_date == subq.c.max_date),
            )
            .all()
        )

        return {ticker: score for score, ticker in rows}

    def _query_latest_prices(
        self, session: Session, tickers: List[str]
    ) -> Dict[str, Decimal]:
        """Get the most recent close_price per ticker from price_history."""
        subq = (
            session.query(
                PriceHistory.security_id,
                func.max(PriceHistory.price_date).label("max_date"),
            )
            .join(SecurityMaster, PriceHistory.security_id == SecurityMaster.id)
            .filter(SecurityMaster.ticker.in_(tickers))
            .group_by(PriceHistory.security_id)
            .subquery()
        )

        rows = (
            session.query(SecurityMaster.ticker, PriceHistory.close_price)
            .join(PriceHistory, PriceHistory.security_id == SecurityMaster.id)
            .join(
                subq,
                (PriceHistory.security_id == subq.c.security_id)
                & (PriceHistory.price_date == subq.c.max_date),
            )
            .all()
        )

        return {ticker: price for ticker, price in rows}

    async def _compute_live(
        self, tickers: List[str], data: Dict[str, Dict]
    ) -> None:
        """Tier 3: compute live momentum scores via yfinance, write back to DB."""

        async def compute_one(ticker: str) -> Tuple[str, Optional[Dict]]:
            try:
                result = await asyncio.to_thread(
                    self.momentum_engine.calculate_momentum_score, ticker
                )
                return ticker, result
            except Exception:
                logger.warning(f"Tier 3 live compute failed for {ticker}", exc_info=True)
                return ticker, None

        results = await asyncio.gather(*(compute_one(t) for t in tickers))

        rows_to_persist = []
        for ticker, result in results:
            if result:
                data[ticker] = result
                rows_to_persist.append((ticker, result))

        # Persist to DB in background (don't block the response)
        if rows_to_persist and self.db_config is not None:
            try:
                self._persist_to_database(rows_to_persist)
            except Exception:
                logger.warning("Failed to persist Tier 3 results to DB", exc_info=True)

    def _persist_to_database(
        self, rows: List[Tuple[str, Dict[str, Any]]]
    ) -> None:
        """Write momentum scores and prices to PostgreSQL."""
        today = date.today()

        with self.db_config.get_session_context() as session:
            # Resolve or create SecurityMaster entries
            ticker_list = [ticker for ticker, _ in rows]
            existing = (
                session.query(SecurityMaster)
                .filter(SecurityMaster.ticker.in_(ticker_list))
                .all()
            )
            sec_map = {s.ticker: s for s in existing}

            for ticker, result in rows:
                security = sec_map.get(ticker)
                if security is None:
                    security = SecurityMaster(
                        ticker=ticker,
                        security_type="STOCK",
                        is_active=True,
                    )
                    session.add(security)
                    session.flush()  # get id
                    sec_map[ticker] = security

                # Upsert momentum score
                existing_score = (
                    session.query(MomentumScore)
                    .filter_by(security_id=security.id, score_date=today)
                    .first()
                )
                composite = result.get("composite_score", 0)
                if existing_score:
                    existing_score.composite_score = composite
                    existing_score.price_momentum = result.get("price_momentum")
                    existing_score.technical_momentum = result.get("technical_momentum")
                    existing_score.fundamental_momentum = result.get("fundamental_momentum")
                    existing_score.relative_momentum = result.get("relative_momentum")
                    existing_score.rating = result.get("rating")
                else:
                    session.add(
                        MomentumScore(
                            security_id=security.id,
                            score_date=today,
                            composite_score=composite,
                            price_momentum=result.get("price_momentum"),
                            technical_momentum=result.get("technical_momentum"),
                            fundamental_momentum=result.get("fundamental_momentum"),
                            relative_momentum=result.get("relative_momentum"),
                            rating=result.get("rating"),
                        )
                    )

                # Upsert price
                current_price = result.get("current_price")
                if current_price and current_price > 0:
                    existing_price = (
                        session.query(PriceHistory)
                        .filter_by(security_id=security.id, price_date=today)
                        .first()
                    )
                    if existing_price:
                        existing_price.close_price = current_price
                    else:
                        session.add(
                            PriceHistory(
                                security_id=security.id,
                                price_date=today,
                                close_price=current_price,
                            )
                        )

    @staticmethod
    def _score_to_rating(score: float) -> str:
        if score >= 80:
            return "Strong Buy"
        elif score >= 65:
            return "Buy"
        elif score >= 50:
            return "Hold"
        elif score >= 35:
            return "Weak Hold"
        return "Sell"
