"""
Backfill price_history and performance_snapshots for all portfolio tickers.

Run from repo root:
    python -m scripts.backfill_prices_and_snapshots
    python -m scripts.backfill_prices_and_snapshots --days 365
    python -m scripts.backfill_prices_and_snapshots --start 2024-01-01
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import date, timedelta

import yfinance as yf
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Backfill price history and portfolio snapshots")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, default=365,
                       help="Number of calendar days back to fetch (default: 365)")
    group.add_argument("--start", type=str,
                       help="Explicit start date in YYYY-MM-DD format")
    return parser.parse_args()


def get_all_tickers():
    """Return every ticker across all PORTFOLIO_CATEGORIES, DEFAULT_PORTFOLIO, and security_master."""
    from backend.config.portfolio_config import PORTFOLIO_CATEGORIES, DEFAULT_PORTFOLIO
    tickers = set(DEFAULT_PORTFOLIO.keys())
    for category in PORTFOLIO_CATEGORIES.values():
        tickers.update(category.get("tickers", []))

    # Also include any tickers already tracked in the DB (e.g. user watchlists/portfolios)
    try:
        from backend.database.config import db_config
        from backend.models.database import SecurityMaster
        db_config.initialize_engine()
        with db_config.get_session_context() as session:
            db_tickers = [row.ticker for row in session.query(SecurityMaster.ticker).filter(SecurityMaster.is_active == True).all()]
        tickers.update(db_tickers)
    except Exception as e:
        logger.warning("Could not load tickers from security_master: %s", e)

    return sorted(tickers)


def ensure_security_master(session, tickers):
    """Upsert SecurityMaster rows for every ticker; return {ticker: id} map."""
    from backend.models.database import SecurityMaster

    existing = {
        row.ticker: row.id
        for row in session.query(SecurityMaster.ticker, SecurityMaster.id).all()
    }
    missing = [t for t in tickers if t not in existing]
    if missing:
        logger.info("Creating %d new SecurityMaster entries: %s", len(missing), missing)
        for ticker in missing:
            sm = SecurityMaster(ticker=ticker, security_type="STOCK", is_active=True)
            session.add(sm)
        session.flush()
        new_rows = (
            session.query(SecurityMaster.ticker, SecurityMaster.id)
            .filter(SecurityMaster.ticker.in_(missing))
            .all()
        )
        for row in new_rows:
            existing[row.ticker] = row.id

    return existing


def run(days: int = None, start: str = None):
    """
    Backfill prices and snapshots.
    When called programmatically, pass days or start directly.
    When called from the CLI, arguments are read from sys.argv.
    """
    if days is None and start is None:
        args = parse_args()
        start = args.start
        days = args.days

    if start:
        start_date = start
    else:
        start_date = (date.today() - timedelta(days=days or 365)).isoformat()
    end_date = date.today().isoformat()

    logger.info("Backfilling price history from %s to %s", start_date, end_date)

    from backend.database.config import db_config
    db_config.initialize_engine()

    from backend.models.database import PriceHistory

    # 1. Collect all tickers
    tickers = get_all_tickers()
    logger.info("Found %d tickers to backfill", len(tickers))

    # 2. Ensure SecurityMaster rows exist
    with db_config.get_session_context() as session:
        ticker_to_id = ensure_security_master(session, tickers)
        session.commit()

    # 3. Download historical closes from yfinance in one batch
    logger.info("Downloading from yfinance ...")
    raw = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        auto_adjust=True,
        progress=False,
    )

    if raw.empty:
        logger.error("yfinance returned no data -- aborting")
        return

    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]].rename(columns={"Close": tickers[0]})

    closes = closes.dropna(how="all")
    logger.info("Downloaded %d trading days across %d tickers", len(closes), closes.shape[1])

    # 4. Fetch existing (security_id, price_date) pairs to skip
    with db_config.get_session_context() as session:
        existing = set(
            session.query(PriceHistory.security_id, PriceHistory.price_date).all()
        )
    logger.info("DB already has %d price rows", len(existing))

    # 5. Build rows to insert
    to_insert = []
    skipped = 0
    for price_date, row in closes.iterrows():
        pd_date = price_date.date() if hasattr(price_date, "date") else price_date
        for ticker in tickers:
            security_id = ticker_to_id.get(ticker)
            if security_id is None or ticker not in row.index:
                continue
            price = row[ticker]
            if pd.isna(price) or price <= 0:
                continue
            if (security_id, pd_date) in existing:
                skipped += 1
                continue
            to_insert.append(PriceHistory(
                security_id=security_id,
                price_date=pd_date,
                close_price=round(float(price), 4),
            ))

    logger.info(
        "Inserting %d new rows (%d already existed, skipped)",
        len(to_insert), skipped
    )

    CHUNK = 500
    inserted = 0
    with db_config.get_session_context() as session:
        for i in range(0, len(to_insert), CHUNK):
            session.bulk_save_objects(to_insert[i:i + CHUNK])
            inserted += len(to_insert[i:i + CHUNK])
            logger.info("  ... %d / %d rows committed", inserted, len(to_insert))
        session.commit()

    logger.info("Price backfill complete: %d rows inserted.", inserted)

    # 6. Re-run snapshot backfill for all active portfolios
    from backend.services.snapshot_service import SnapshotService
    from backend.models.database import Portfolio

    svc = SnapshotService(db_config)

    with db_config.get_session_context() as session:
        portfolios = (
            session.query(Portfolio.id, Portfolio.name)
            .filter(Portfolio.is_active == True)
            .all()
        )

    if not portfolios:
        logger.info("No active portfolios found -- skipping snapshot backfill")
    else:
        logger.info("Running snapshot backfill for %d portfolio(s) ...", len(portfolios))
        for pid, pname in portfolios:
            try:
                n = svc.backfill_portfolio(pid)
                logger.info("  Portfolio %d (%s): %d new snapshots", pid, pname, n)
            except Exception as e:
                logger.error("  Portfolio %d failed: %s", pid, e)

    logger.info("Done.")


if __name__ == "__main__":
    run()
