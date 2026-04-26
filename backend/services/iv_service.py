"""
IV Service for AlphaVelocity

Fetches implied volatility from options chains, calculates IV Rank (IVR),
and persists snapshots to iv_history for accurate 52-week IVR over time.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any

import yfinance as yf
from sqlalchemy import func

logger = logging.getLogger(__name__)

# IVR signal thresholds
IVR_SELL_THRESHOLD = 50   # IVR >= 50 → premium is worth selling
IVR_HEDGE_THRESHOLD = 30  # IVR < 30 → protection is cheap


def _ivr_signal(ivr: Optional[float]) -> str:
    if ivr is None:
        return "Insufficient data"
    if ivr >= IVR_SELL_THRESHOLD:
        return "Sell Premium"
    if ivr < IVR_HEDGE_THRESHOLD:
        return "Cheap Hedge"
    return "Neutral"


def _get_earnings_dte(ticker: str) -> Optional[int]:
    """
    Return days until the next earnings date, or None if unavailable.
    Uses yfinance calendar data.
    """
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is None:
            return None
        # calendar is a dict with an 'Earnings Date' key (list of Timestamps)
        earnings_dates = cal.get("Earnings Date") or cal.get("earnings_date")
        if not earnings_dates:
            return None
        today = date.today()
        future = []
        for ed in (earnings_dates if isinstance(earnings_dates, list) else [earnings_dates]):
            try:
                ed_date = ed.date() if hasattr(ed, "date") else date.fromisoformat(str(ed)[:10])
                if ed_date >= today:
                    future.append(ed_date)
            except Exception:
                continue
        if not future:
            return None
        return (min(future) - today).days
    except Exception as e:
        logger.debug("Could not fetch earnings date for %s: %s", ticker, e)
        return None


# How many days out to warn about upcoming earnings
EARNINGS_CAUTION_DAYS = 14  # show note
EARNINGS_WARNING_DAYS = 7   # override signal


def _get_atm_iv(ticker: str) -> Optional[tuple[float, date]]:
    """
    Fetch ATM implied volatility from the nearest options expiry >= 25 DTE.

    Returns (iv_annualized, expiry_date) or None if unavailable.
    IV is averaged across near-ATM puts and calls (within 5% of spot).
    """
    try:
        tk = yf.Ticker(ticker)
        spot_hist = tk.history(period="1d")
        if spot_hist.empty:
            return None
        spot = float(spot_hist["Close"].iloc[-1])

        # Pick nearest expiry >= 25 DTE
        expiries = tk.options
        if not expiries:
            return None

        target_expiry = None
        min_dte = 25
        for exp_str in expiries:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            dte = (exp_date - date.today()).days
            if dte >= min_dte:
                target_expiry = (exp_str, exp_date)
                break

        if target_expiry is None:
            return None

        exp_str, exp_date = target_expiry
        chain = tk.option_chain(exp_str)

        # Collect IV for options within 5% of spot
        ivs = []
        for df in (chain.calls, chain.puts):
            nearby = df[
                (df["strike"] >= spot * 0.95) &
                (df["strike"] <= spot * 1.05) &
                (df["impliedVolatility"] > 0.01)
            ]
            ivs.extend(nearby["impliedVolatility"].tolist())

        if not ivs:
            return None

        avg_iv = sum(ivs) / len(ivs)
        return (round(avg_iv, 4), exp_date)

    except Exception as e:
        logger.warning("Failed to fetch IV for %s: %s", ticker, e)
        return None


def _get_term_structure(ticker: str) -> list[dict]:
    """
    Fetch ATM IV for every available expiry between 7 and 365 DTE.

    Returns a list of dicts sorted by DTE:
        [{"expiry": "YYYY-MM-DD", "dte": int, "iv": float}, ...]
    """
    try:
        tk = yf.Ticker(ticker)
        spot_hist = tk.history(period="1d")
        if spot_hist.empty:
            return []
        spot = float(spot_hist["Close"].iloc[-1])

        expiries = tk.options
        if not expiries:
            return []

        today = date.today()
        points = []
        for exp_str in expiries:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if dte < 7 or dte > 365:
                continue
            try:
                chain = tk.option_chain(exp_str)
                ivs = []
                for df in (chain.calls, chain.puts):
                    nearby = df[
                        (df["strike"] >= spot * 0.95) &
                        (df["strike"] <= spot * 1.05) &
                        (df["impliedVolatility"] > 0.01)
                    ]
                    ivs.extend(nearby["impliedVolatility"].tolist())
                if ivs:
                    points.append({
                        "expiry": exp_str,
                        "dte": dte,
                        "iv": round(sum(ivs) / len(ivs), 4),
                    })
            except Exception:
                continue

        points.sort(key=lambda x: x["dte"])
        return points

    except Exception as e:
        logger.warning("Failed to fetch term structure for %s: %s", ticker, e)
        return []


class IVService:
    """Service for implied volatility data and IVR calculation."""

    def __init__(self, db_config=None) -> None:
        self.db_config = db_config

    def get_iv_data(self, ticker: str) -> Dict[str, Any]:
        """
        Return current IV, IVR, and trading signal for a ticker.

        Fetches fresh IV from yfinance, persists to iv_history, then
        calculates IVR from the stored 52-week history.

        Returns:
            {ticker, iv, ivr, signal, iv_52w_low, iv_52w_high,
             data_points, last_updated}
        """
        ticker = ticker.upper()
        result: Dict[str, Any] = {
            "ticker": ticker,
            "iv": None,
            "ivr": None,
            "signal": "Insufficient data",
            "iv_52w_low": None,
            "iv_52w_high": None,
            "data_points": 0,
            "last_updated": None,
            "earnings_dte": None,
            "earnings_warning": False,
        }

        # 1. If DB is available, check whether today's snapshot already exists.
        #    If it does, skip the yfinance fetch and serve entirely from DB.
        current_iv: Optional[float] = None
        if self.db_config is not None:
            current_iv = self._query_today_iv(ticker)

        if current_iv is not None:
            # Serve from DB — no yfinance call needed
            result["iv"] = current_iv
            result["last_updated"] = datetime.utcnow().isoformat()
        else:
            # 2. Today's snapshot missing — fetch from yfinance and persist
            iv_tuple = _get_atm_iv(ticker)
            if iv_tuple is None:
                # Still populate earnings info before returning
                result["earnings_dte"] = _get_earnings_dte(ticker)
                result["earnings_warning"] = (
                    result["earnings_dte"] is not None
                    and result["earnings_dte"] <= EARNINGS_WARNING_DAYS
                )
                return result

            current_iv, expiry_date = iv_tuple
            result["iv"] = current_iv
            result["last_updated"] = datetime.utcnow().isoformat()

            if self.db_config is not None:
                try:
                    self._persist_iv(ticker, current_iv, expiry_date)
                except Exception as e:
                    logger.warning("Could not persist IV for %s: %s", ticker, e)

        # 3. Earnings date (always fetched — cheap yfinance call)
        earnings_dte = _get_earnings_dte(ticker)
        result["earnings_dte"] = earnings_dte
        result["earnings_warning"] = (
            earnings_dte is not None and earnings_dte <= EARNINGS_WARNING_DAYS
        )

        # 4. Calculate IVR from 52-week history
        if self.db_config is not None:
            try:
                low, high, count = self._query_52w_range(ticker)
                result["iv_52w_low"] = low
                result["iv_52w_high"] = high
                result["data_points"] = count
                if low is not None and high is not None and high > low:
                    ivr = round((current_iv - low) / (high - low) * 100, 1)
                    result["ivr"] = ivr
                    result["signal"] = _ivr_signal(ivr)
            except Exception as e:
                logger.warning("Could not calculate IVR for %s: %s", ticker, e)

        # Override signal if earnings are imminent — IV spike is earnings premium
        if result["earnings_warning"]:
            result["signal"] = "Earnings Soon — Skip"

        return result

    def get_term_structure(self, ticker: str) -> list[dict]:
        """
        Return ATM IV for each available expiry between 7–365 DTE.

        Returns a list sorted by DTE:
            [{"expiry": "YYYY-MM-DD", "dte": int, "iv": float}, ...]
        """
        return _get_term_structure(ticker.upper())

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_or_create_security_id(self, session, ticker: str) -> int:
        from ..models.database import SecurityMaster
        sec = session.query(SecurityMaster).filter_by(ticker=ticker).first()
        if sec is None:
            sec = SecurityMaster(
                ticker=ticker,
                security_type="STOCK",
                is_active=True,
            )
            session.add(sec)
            session.flush()
        return sec.id

    def _persist_iv(self, ticker: str, iv: float, expiry_date: date) -> None:
        """Save one IV snapshot per ticker per calendar day."""
        from ..models.database import IVHistory
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        with self.db_config.get_session_context() as session:
            sec_id = self._get_or_create_security_id(session, ticker)
            existing = session.query(IVHistory).filter(
                IVHistory.security_id == sec_id,
                IVHistory.recorded_at >= today_start,
            ).first()
            if existing:
                return  # Already have today's snapshot
            snapshot = IVHistory(
                security_id=sec_id,
                recorded_at=datetime.utcnow(),
                iv=iv,
                expiry_date=expiry_date,
            )
            session.add(snapshot)

    def _query_today_iv(self, ticker: str) -> Optional[float]:
        """Return today's IV from iv_history if it exists, else None."""
        from ..models.database import IVHistory, SecurityMaster
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            with self.db_config.get_session_context() as session:
                row = (
                    session.query(IVHistory.iv)
                    .join(SecurityMaster, IVHistory.security_id == SecurityMaster.id)
                    .filter(
                        SecurityMaster.ticker == ticker,
                        IVHistory.recorded_at >= today_start,
                    )
                    .first()
                )
                return float(row[0]) if row else None
        except Exception:
            return None

    def _query_52w_range(self, ticker: str) -> tuple[Optional[float], Optional[float], int]:
        """Return (min_iv, max_iv, count) over the past 52 weeks from iv_history."""
        from ..models.database import IVHistory, SecurityMaster
        cutoff = datetime.utcnow() - timedelta(weeks=52)
        with self.db_config.get_session_context() as session:
            sec = session.query(SecurityMaster).filter_by(ticker=ticker).first()
            if sec is None:
                return None, None, 0
            row = session.query(
                func.min(IVHistory.iv),
                func.max(IVHistory.iv),
                func.count(IVHistory.id),
            ).filter(
                IVHistory.security_id == sec.id,
                IVHistory.recorded_at >= cutoff,
            ).one()
            low = float(row[0]) if row[0] is not None else None
            high = float(row[1]) if row[1] is not None else None
            count = int(row[2])
            return low, high, count


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_iv_service: Optional[IVService] = None


def get_iv_service() -> IVService:
    global _iv_service
    if _iv_service is None:
        _iv_service = IVService()
    return _iv_service


def set_iv_service(svc: IVService) -> None:
    global _iv_service
    _iv_service = svc
