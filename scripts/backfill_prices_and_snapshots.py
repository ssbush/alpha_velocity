"""
Backfill price_history and performance_snapshots for all portfolio tickers.

Run from repo root:
    python -m scripts.backfill_prices_and_snapshots
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import date, timedelta

import yfinance as yf
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

START_DATE = "2025-08-01"   # pull from here to capture any gaps
END_DATE   = date.today().isoformat()


def run():
    from backend.database.config import db_config
    db_config.initialize_engine()

    from backend.models.database import SecurityMaster, PriceHistory, Portfolio, Holding
    from sqlalchemy import tuple_

    # ── 1. Get all tickers that are held in any active portfolio ──────────
    with db_config.get_session_context() as session:
        rows = (
            session.query(SecurityMaster.id, SecurityMaster.ticker)
            .join(Holding, Holding.security_id == SecurityMaster.id)
            .join(Portfolio, Portfolio.id == Holding.portfolio_id)
            .filter(Portfolio.is_active == True)
            .distinct()
            .all()
        )
        ticker_to_id = {r.ticker: r.id for r in rows}

    tickers = sorted(ticker_to_id.keys())
    logger.info("Backfilling %d tickers: %s", len(tickers), tickers)

    # ── 2. Download historical closes from yfinance in one batch ──────────
    logger.info("Downloading price history from %s to %s …", START_DATE, END_DATE)
    raw = yf.download(
        tickers,
        start=START_DATE,
        end=END_DATE,
        auto_adjust=True,
        progress=False,
    )

    if raw.empty:
        logger.error("yfinance returned no data")
        return

    # yfinance returns MultiIndex columns (field, ticker) when >1 ticker
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]].rename(columns={"Close": tickers[0]})

    closes = closes.dropna(how="all")
    logger.info("Downloaded %d trading days", len(closes))

    # ── 3. Fetch existing (security_id, price_date) pairs to skip ─────────
    with db_config.get_session_context() as session:
        existing = set(
            session.query(PriceHistory.security_id, PriceHistory.price_date).all()
        )

    # ── 4. Build rows to insert ───────────────────────────────────────────
    to_insert = []
    for price_date, row in closes.iterrows():
        pd_date = price_date.date() if hasattr(price_date, "date") else price_date
        for ticker, security_id in ticker_to_id.items():
            if ticker not in row.index:
                continue
            price = row[ticker]
            if pd.isna(price) or price <= 0:
                continue
            if (security_id, pd_date) in existing:
                continue
            to_insert.append(PriceHistory(
                security_id=security_id,
                price_date=pd_date,
                close_price=round(float(price), 4),
            ))

    logger.info("Inserting %d new price rows …", len(to_insert))

    # Batch insert in chunks of 500
    CHUNK = 500
    with db_config.get_session_context() as session:
        for i in range(0, len(to_insert), CHUNK):
            session.bulk_save_objects(to_insert[i:i + CHUNK])
        session.commit()

    logger.info("Price backfill complete.")

    # ── 5. Re-run snapshot backfill for all active portfolios ─────────────
    from backend.services.snapshot_service import SnapshotService
    from backend.models.database import Portfolio as PortfolioModel

    svc = SnapshotService(db_config)

    with db_config.get_session_context() as session:
        portfolio_ids = [
            r[0] for r in
            session.query(PortfolioModel.id, PortfolioModel.name)
            .filter(PortfolioModel.is_active == True)
            .all()
        ]
        portfolio_names = {
            r[0]: r[1] for r in
            session.query(PortfolioModel.id, PortfolioModel.name)
            .filter(PortfolioModel.is_active == True)
            .all()
        }

    for pid in portfolio_ids:
        try:
            n = svc.backfill_portfolio(pid)
            logger.info("Portfolio %d (%s): %d new snapshots", pid, portfolio_names[pid], n)
        except Exception as e:
            logger.error("Portfolio %d failed: %s", pid, e)

    logger.info("Done.")


if __name__ == "__main__":
    run()
