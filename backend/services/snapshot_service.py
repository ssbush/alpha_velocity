"""
SnapshotService — daily portfolio value snapshots.

Writes one row to performance_snapshots per portfolio per day by replaying
transactions against price_history. Used for the Dashboard value chart and
future rotation-signal engine.

Transaction conventions (from user_portfolio_service.py):
  BUY    — shares > 0, adds to position
  SELL   — shares < 0 (stored negative), reduces position
  SPLIT  — shares = split ratio (e.g. 4.0 for 4:1), multiplies position
  REINVEST — shares > 0, treated like BUY
  DIVIDEND — no share change, ignored
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SnapshotService:
    """Compute and persist daily portfolio value snapshots."""

    def __init__(self, db_config):
        self.db_config = db_config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def backfill_portfolio(self, portfolio_id: int) -> int:
        """
        Populate performance_snapshots for every date in price_history that
        has data for this portfolio's securities.  Skips dates that already
        have a snapshot.  Returns the number of new snapshots written.
        """
        from ..models.database import (
            Transaction, PriceHistory, SecurityMaster,
            Portfolio, PerformanceSnapshot,
        )
        from sqlalchemy import func

        with self.db_config.get_session_context() as session:
            # Verify portfolio exists
            portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")

            # All transactions for this portfolio, ordered by date
            transactions = (
                session.query(Transaction)
                .filter(Transaction.portfolio_id == portfolio_id)
                .order_by(Transaction.transaction_date, Transaction.id)
                .all()
            )
            if not transactions:
                logger.info("Portfolio %d has no transactions — nothing to backfill", portfolio_id)
                return 0

            # Security IDs involved in this portfolio
            security_ids = list({t.security_id for t in transactions})

            # All price_history dates for these securities
            price_dates = (
                session.query(PriceHistory.price_date)
                .filter(PriceHistory.security_id.in_(security_ids))
                .distinct()
                .order_by(PriceHistory.price_date)
                .all()
            )
            price_dates = [r[0] for r in price_dates]

            if not price_dates:
                logger.info("No price history found for portfolio %d", portfolio_id)
                return 0

            # Existing snapshot dates — skip these
            existing = {
                r[0] for r in session.query(PerformanceSnapshot.snapshot_date)
                .filter(PerformanceSnapshot.portfolio_id == portfolio_id)
                .all()
            }

            # Bulk-load all price history for relevant securities to avoid N+1
            all_prices = (
                session.query(
                    PriceHistory.security_id,
                    PriceHistory.price_date,
                    PriceHistory.close_price,
                )
                .filter(PriceHistory.security_id.in_(security_ids))
                .order_by(PriceHistory.security_id, PriceHistory.price_date)
                .all()
            )
            # Build lookup: {security_id: [(date, price), ...]} sorted by date
            prices_by_security: Dict[int, List[Tuple]] = {}
            for row in all_prices:
                prices_by_security.setdefault(row.security_id, []).append(
                    (row.price_date, float(row.close_price))
                )

            written = 0
            for snap_date in price_dates:
                if snap_date in existing:
                    continue

                shares_map, cost_map = self._shares_at_date(transactions, snap_date)
                total_value, total_cost, n_positions = self._compute_value(
                    shares_map, cost_map, prices_by_security, snap_date
                )

                if total_value <= 0:
                    continue  # no priced positions on this date

                session.merge(PerformanceSnapshot(
                    portfolio_id=portfolio_id,
                    snapshot_date=snap_date,
                    total_value=round(total_value, 2),
                    total_cost_basis=round(total_cost, 2),
                    unrealized_gain_loss=round(total_value - total_cost, 2),
                    number_of_positions=n_positions,
                ))
                written += 1

            session.commit()
            logger.info("Backfilled %d snapshots for portfolio %d", written, portfolio_id)
            return written

    def record_daily_snapshot(self, portfolio_id: int, snap_date: Optional[date] = None) -> bool:
        """
        Write today's snapshot using current holdings (shares already maintained
        by the DB) × most recent price_history close.  No transaction replay needed.
        """
        from ..models.database import (
            Holding, PriceHistory, PerformanceSnapshot, Portfolio,
        )
        from sqlalchemy import func

        snap_date = snap_date or date.today()

        with self.db_config.get_session_context() as session:
            portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio or not portfolio.is_active:
                return False

            holdings = (
                session.query(Holding)
                .filter(Holding.portfolio_id == portfolio_id)
                .all()
            )
            if not holdings:
                return False

            total_value = 0.0
            total_cost = 0.0
            n_positions = 0

            for holding in holdings:
                # Most recent price on or before snap_date
                price_row = (
                    session.query(PriceHistory.close_price)
                    .filter(
                        PriceHistory.security_id == holding.security_id,
                        PriceHistory.price_date <= snap_date,
                    )
                    .order_by(PriceHistory.price_date.desc())
                    .first()
                )
                if price_row is None:
                    continue
                total_value += float(holding.shares) * float(price_row.close_price)
                total_cost += float(holding.total_cost_basis or 0)
                n_positions += 1

            if total_value <= 0:
                return False

            session.merge(PerformanceSnapshot(
                portfolio_id=portfolio_id,
                snapshot_date=snap_date,
                total_value=round(total_value, 2),
                total_cost_basis=round(total_cost, 2),
                unrealized_gain_loss=round(total_value - total_cost, 2),
                number_of_positions=n_positions,
            ))
            session.commit()
            return True

    def record_all_daily(self, snap_date: Optional[date] = None) -> int:
        """
        Write today's snapshot for every active portfolio.
        Called by daily_scheduler.run_daily_update().
        """
        from ..models.database import Portfolio

        snap_date = snap_date or date.today()
        written = 0

        with self.db_config.get_session_context() as session:
            portfolios = session.query(Portfolio.id).filter(Portfolio.is_active == True).all()
            portfolio_ids = [r[0] for r in portfolios]

        for pid in portfolio_ids:
            try:
                if self.record_daily_snapshot(pid, snap_date):
                    written += 1
            except Exception as e:
                logger.error("Failed to snapshot portfolio %d: %s", pid, e)

        logger.info("Recorded daily snapshots for %d/%d portfolios", written, len(portfolio_ids))
        return written

    def get_value_history(self, portfolio_id: int, days: int = 365):
        """
        Read value history from performance_snapshots.
        Returns {labels, values} for Chart.js.
        """
        from ..models.database import PerformanceSnapshot
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=days)

        with self.db_config.get_session_context() as session:
            rows = (
                session.query(
                    PerformanceSnapshot.snapshot_date,
                    PerformanceSnapshot.total_value,
                )
                .filter(
                    PerformanceSnapshot.portfolio_id == portfolio_id,
                    PerformanceSnapshot.snapshot_date >= cutoff,
                )
                .order_by(PerformanceSnapshot.snapshot_date)
                .all()
            )

        return {
            "labels": [r.snapshot_date.strftime("%m/%d") for r in rows],
            "values": [float(r.total_value) for r in rows],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _shares_at_date(
        self, transactions, as_of: date
    ) -> Tuple[Dict[int, float], Dict[int, float]]:
        """
        Replay transactions up to and including `as_of` to produce
        {security_id: shares} and {security_id: cost_basis}.
        """
        shares: Dict[int, float] = {}
        cost: Dict[int, float] = {}

        for txn in transactions:
            if txn.transaction_date > as_of:
                break

            sid = txn.security_id
            txn_shares = float(txn.shares)
            txn_price = float(txn.price_per_share) if txn.price_per_share else 0.0

            if txn.transaction_type in ('BUY', 'REINVEST'):
                shares[sid] = shares.get(sid, 0.0) + txn_shares
                cost[sid] = cost.get(sid, 0.0) + txn_shares * txn_price

            elif txn.transaction_type == 'SELL':
                # shares are stored negative
                sold = abs(txn_shares)
                prev = shares.get(sid, 0.0)
                if prev > 0:
                    avg = cost.get(sid, 0.0) / prev
                    shares[sid] = max(0.0, prev - sold)
                    cost[sid] = max(0.0, cost.get(sid, 0.0) - sold * avg)

            elif txn.transaction_type == 'SPLIT':
                # txn_shares is the split ratio
                if sid in shares:
                    shares[sid] = shares[sid] * txn_shares
                    # cost basis per share drops proportionally; total unchanged

        return shares, cost

    def _get_price_at_or_before(
        self, security_id: int, as_of: date,
        prices_by_security: Dict[int, List[Tuple]]
    ) -> Optional[float]:
        """Return the most recent price on or before `as_of`, or None."""
        entries = prices_by_security.get(security_id, [])
        # entries are sorted by date ascending
        result = None
        for price_date, price in entries:
            if price_date <= as_of:
                result = price
            else:
                break
        return result

    def _compute_value(
        self,
        shares_map: Dict[int, float],
        cost_map: Dict[int, float],
        prices_by_security: Dict[int, List[Tuple]],
        snap_date: date,
    ) -> Tuple[float, float, int]:
        """Return (total_value, total_cost_basis, n_positions)."""
        total_value = 0.0
        total_cost = 0.0
        n_positions = 0

        for security_id, shares in shares_map.items():
            if shares <= 0:
                continue
            price = self._get_price_at_or_before(security_id, snap_date, prices_by_security)
            if price is None:
                continue
            total_value += shares * price
            total_cost += cost_map.get(security_id, 0.0)
            n_positions += 1

        return total_value, total_cost, n_positions
