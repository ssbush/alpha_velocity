import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
import warnings
import time
import logging
import pytz
warnings.filterwarnings('ignore')

from .historical_service import HistoricalDataService

logger = logging.getLogger(__name__)

class MomentumEngine:
    """
    AlphaVelocity Momentum Scoring Engine

    Generates systematic momentum scores for stocks using multiple factors:
    - Price Momentum (40%)
    - Technical Momentum (25%)
    - Fundamental Momentum (25%)
    - Relative Momentum (10%)
    """

    def __init__(self, price_service=None) -> None:
        from .price_service import PriceService
        self.weights: Dict[str, float] = {
            'price_momentum': 0.50,
            'technical_momentum': 0.35,
            'relative_momentum': 0.15
        }
        self.price_service: 'PriceService' = price_service or PriceService()

        # In-memory score cache.  TTL is market-hours-aware — see _cache_ttl property.
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}

        # Historical data service
        self.historical_service: HistoricalDataService = HistoricalDataService()

    @property
    def _cache_ttl(self) -> int:
        """During market hours return a 1-hour TTL so intraday score drift
        (volume, ROC, RSI) is reflected promptly.  Outside market hours a
        24-hour TTL is fine — scores won't move until the next session."""
        now = datetime.now(pytz.timezone("US/Eastern"))
        market_open  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0,  second=0, microsecond=0)
        if now.weekday() < 5 and market_open <= now <= market_close:
            return 3600   # 1 hour during the trading session
        return 86400      # 24 hours outside market hours

    def get_stock_data(self, ticker: str, period: str = '1y') -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
        """Fetch stock data via price service"""
        return self.price_service.get_stock_data(ticker, period)

    def calculate_price_momentum(self, hist_data: pd.DataFrame) -> float:
        """Calculate price momentum component (50% of total score).

        Three sub-components:
        - Trend direction   (20 pts): is price above key moving averages?
        - Return magnitude  (40 pts): weighted absolute performance across timeframes
        - Momentum acceleration (40 pts): is the trend speeding up or slowing down?

        Replacing the old binary MA-above/below scoring (which could max out the
        component regardless of actual returns) with a balanced three-part model
        that rewards acceleration and penalises deceleration early.
        """
        if len(hist_data) < 249:
            return 0

        current_price = hist_data['Close'].iloc[-1]

        # --- Trend direction (max 20 pts) ---
        ma_20  = hist_data['Close'].rolling(20).mean().iloc[-1]
        ma_50  = hist_data['Close'].rolling(50).mean().iloc[-1]
        ma_200 = hist_data['Close'].rolling(200).mean().iloc[-1]
        direction_score = 0
        if current_price > ma_20:  direction_score += 7
        if current_price > ma_50:  direction_score += 6
        if current_price > ma_200: direction_score += 7

        # --- Return magnitude (max 40 pts) ---
        periods = {'1m': 21, '3m': 63, '6m': 126, '12m': 249}
        returns = {p: (current_price / hist_data['Close'].iloc[-d]) - 1
                   for p, d in periods.items()}

        w = {'1m': 0.4, '3m': 0.3, '6m': 0.2, '12m': 0.1}
        weighted_return = sum(returns[p] * w[p] for p in returns)
        # Neutral (0 %) → 20 pts; ±25 % weighted return → [0, 40]
        magnitude_score = max(0.0, min(40.0, 20.0 + weighted_return * 80.0))

        # --- Momentum acceleration (max 40 pts) ---
        # Annualise 1-month vs 3-month returns to detect whether speed is changing
        r1m_ann = (1.0 + returns['1m']) ** 12 - 1.0
        r3m_ann = (1.0 + returns['3m']) **  4 - 1.0
        return_accel = r1m_ann - r3m_ann   # positive = accelerating, negative = decelerating

        # MA-20 slope over last 10 trading days, annualised (~252/10 ≈ 25×)
        ma20_series = hist_data['Close'].rolling(20).mean()
        ma20_prev   = ma20_series.iloc[-11]
        ma20_slope_ann = ((ma20_series.iloc[-1] / ma20_prev) - 1.0) * 25.0 if ma20_prev > 0 else 0.0

        # 70 % return acceleration + 30 % MA-20 slope direction
        combined_accel = 0.7 * return_accel + 0.3 * ma20_slope_ann
        # Neutral (0) → 20 pts; ±~67 % annualised acceleration → [0, 40]
        accel_score = max(0.0, min(40.0, 20.0 + combined_accel * 30.0))

        return min(100.0, direction_score + magnitude_score + accel_score)

    def calculate_technical_momentum(self, hist_data: pd.DataFrame) -> float:
        """Calculate technical momentum component (25% of total score)"""
        if len(hist_data) < 50:
            return 0

        # RSI Calculation
        delta = hist_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # RSI scoring (50-70 is ideal momentum range)
        if 50 <= current_rsi <= 70:
            rsi_score = 100
        elif 30 <= current_rsi < 50:
            rsi_score = (current_rsi - 30) * 2.5
        elif 70 < current_rsi <= 85:
            rsi_score = 100 - ((current_rsi - 70) * 2)
        else:
            rsi_score = 0

        # Volume confirmation
        avg_volume = hist_data['Volume'].rolling(30).mean().iloc[-1]
        current_volume = hist_data['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # Volume score
        volume_score = min(100, volume_ratio * 50)

        # Rate of Change (10-day)
        current_price = hist_data['Close'].iloc[-1]
        price_10d_ago = hist_data['Close'].iloc[-10]
        roc = ((current_price / price_10d_ago) - 1) * 100
        roc_score = min(100, max(0, roc * 10 + 50))

        technical_score = (rsi_score * 0.4) + (volume_score * 0.3) + (roc_score * 0.3)
        return min(100, max(0, technical_score))

    # ------------------------------------------------------------------ #
    # Fixed income helpers                                                  #
    # ------------------------------------------------------------------ #

    _FIXED_INCOME_KEYWORDS = frozenset([
        'bond', 'treasury', 'fixed income', 'government', 'corporate bond',
        'inflation', 'tips', 'ultrashort', 'floating rate', 'bank loan',
        'mortgage', 'muni', 'municipal', 'intermediate core', 'short-term bond',
        'long-term bond', 'high yield bond', 'income', 'aggregate bond',
    ])

    def _is_fixed_income(self, stock_info: Dict[str, Any]) -> bool:
        """Return True when yfinance identifies the security as a bond/fixed-income ETF.

        Checks the category field first (most reliable), then falls back to
        longName/shortName for ETFs whose category yfinance returns as None.
        """
        # Only ETFs and mutual funds can be fixed income instruments — never equities
        quote_type = (stock_info.get('quoteType') or '').upper()
        if quote_type not in ('ETF', 'MUTUALFUND'):
            return False
        for field in ('category', 'longName', 'shortName'):
            text = (stock_info.get(field) or '').lower()
            if text and any(kw in text for kw in self._FIXED_INCOME_KEYWORDS):
                return True
        return False

    def calculate_fixed_income_fundamental(
        self, stock_info: Dict[str, Any], hist_data: pd.DataFrame
    ) -> float:
        """Fundamental score for bond ETFs (replaces P/E scoring).

        Two equal components:
        - Yield score (0-50 pts): higher distribution/SEC yield is better.
          Maps 0 % → 0 pts, 6 %+ → 50 pts linearly.
        - Trend vs AGG (0-50 pts): 30-day outperformance of the broad bond
          benchmark. ±2 % maps to ±25 pts around a neutral 25 pts.
        """
        try:
            # --- Yield component ---
            raw_yield = stock_info.get('yield') or stock_info.get('dividendYield') or 0
            yield_pts = min(50.0, float(raw_yield) * 833.0)  # 6 % = 50 pts

            # --- Trend vs AGG component ---
            trend_pts = 25.0  # neutral default
            if hist_data is not None and len(hist_data) >= 21:
                try:
                    agg_data, _ = self.get_stock_data('AGG', '1y')
                    if agg_data is not None and len(agg_data) >= 21:
                        ticker_30d = (hist_data['Close'].iloc[-1] /
                                      hist_data['Close'].iloc[-21]) - 1
                        agg_30d = (agg_data['Close'].iloc[-1] /
                                   agg_data['Close'].iloc[-21]) - 1
                        rel = ticker_30d - agg_30d
                        # ±2 % outperformance maps to ±25 pts around 25
                        trend_pts = max(0.0, min(50.0, 25.0 + rel * 1250.0))
                except Exception:
                    pass

            return min(100.0, yield_pts + trend_pts)
        except Exception:
            return 50.0

    def calculate_fundamental_momentum(self, stock_info: Dict[str, Any]) -> float:
        """Calculate fundamental momentum component (25% of total score)"""
        try:
            forward_pe = stock_info.get('forwardPE', 0)
            trailing_pe = stock_info.get('trailingPE', 0)
            peg_ratio = stock_info.get('pegRatio', 0)

            # Basic scoring logic
            fundamental_score = 50  # Base score

            # P/E ratio scoring
            if 0 < forward_pe < 25:
                fundamental_score += 20
            elif 25 <= forward_pe < 40:
                fundamental_score += 10

            # PEG ratio scoring
            if 0 < peg_ratio < 1:
                fundamental_score += 20
            elif 1 <= peg_ratio < 2:
                fundamental_score += 10

            return min(100, max(0, fundamental_score))

        except Exception:
            return 50  # Default score if data unavailable

    def calculate_relative_momentum(self, ticker: str, hist_data: pd.DataFrame, benchmark: str = 'SPY') -> float:
        """Calculate relative momentum component (10% of total score)"""
        try:
            benchmark_data, _ = self.get_stock_data(benchmark, '1y')
            if benchmark_data is None or len(benchmark_data) < 21:
                return 50

            # Calculate 1-month relative performance
            stock_return = (hist_data['Close'].iloc[-1] / hist_data['Close'].iloc[-21]) - 1
            benchmark_return = (benchmark_data['Close'].iloc[-1] / benchmark_data['Close'].iloc[-21]) - 1

            relative_performance = stock_return - benchmark_return

            # Score relative performance
            if relative_performance > 0.05:  # Outperforming by 5%+
                return 100
            elif relative_performance > 0:
                return 50 + (relative_performance * 1000)  # Scale 0-5% to 50-100
            else:
                return max(0, 50 + (relative_performance * 500))  # Scale negative performance

        except Exception:
            return 50

    def calculate_historical_momentum_score(self, ticker: str, end_date: str) -> Dict[str, Any]:
        """Calculate momentum score for a ticker as of a specific historical date"""
        from datetime import datetime, timedelta

        try:
            # Convert end_date string to datetime
            target_date = datetime.strptime(end_date, '%Y-%m-%d')

            # Get historical data up to the target date (need 1+ years for momentum calculations)
            start_date = target_date - timedelta(days=400)  # Extra buffer for weekends/holidays

            # Fetch historical data up to the target date
            hist_data = self.price_service.get_history_by_date_range(
                ticker,
                start=start_date.strftime('%Y-%m-%d'),
                end=(target_date + timedelta(days=1)).strftime('%Y-%m-%d')
            )

            if hist_data is None or len(hist_data) < 50:
                return {
                    'ticker': ticker,
                    'composite_score': 0,
                    'rating': 'Insufficient Data',
                    'price_momentum': 0,
                    'technical_momentum': 0,
                    'relative_momentum': 0
                }

            # Calculate individual components using historical data up to target date
            price_momentum = self.calculate_price_momentum(hist_data)
            technical_momentum = self.calculate_technical_momentum(hist_data)
            relative_momentum = self.calculate_historical_relative_momentum(ticker, hist_data, target_date)

            # Calculate weighted composite score (fundamental component removed)
            composite_score = (
                price_momentum     * self.weights['price_momentum'] +
                technical_momentum * self.weights['technical_momentum'] +
                relative_momentum  * self.weights['relative_momentum']
            )

            # Determine rating
            if composite_score >= 80:
                rating = 'Strong Buy'
            elif composite_score >= 65:
                rating = 'Buy'
            elif composite_score >= 50:
                rating = 'Hold'
            elif composite_score >= 35:
                rating = 'Weak Hold'
            else:
                rating = 'Sell'

            return {
                'ticker': ticker,
                'composite_score': round(composite_score, 1),
                'rating': rating,
                'price_momentum': round(price_momentum, 1),
                'technical_momentum': round(technical_momentum, 1),
                'relative_momentum': round(relative_momentum, 1)
            }

        except Exception as e:
            # Fallback to a reasonable default based on historical context
            return {
                'ticker': ticker,
                'composite_score': 60.0,
                'rating': 'Hold',
                'price_momentum': 60.0,
                'technical_momentum': 60.0,
                'relative_momentum': 60.0
            }

    def calculate_historical_relative_momentum(self, ticker: str, hist_data: pd.DataFrame, target_date: datetime, benchmark: str = 'SPY') -> float:
        """Calculate relative momentum against benchmark for a specific historical date"""
        try:
            from datetime import timedelta

            # Get benchmark data for the same period
            start_date = target_date - timedelta(days=400)
            benchmark_data = self.price_service.get_history_by_date_range(
                benchmark,
                start=start_date.strftime('%Y-%m-%d'),
                end=(target_date + timedelta(days=1)).strftime('%Y-%m-%d')
            )

            if benchmark_data is None or len(hist_data) < 21:
                return 50

            # Calculate 21-day returns for both stock and benchmark
            stock_return = (hist_data['Close'].iloc[-1] / hist_data['Close'].iloc[-21] - 1) if len(hist_data) >= 21 else 0
            benchmark_return = (benchmark_data['Close'].iloc[-1] / benchmark_data['Close'].iloc[-21] - 1) if len(benchmark_data) >= 21 else 0

            relative_performance = stock_return - benchmark_return

            # Scale to 0-100
            if relative_performance > 0.05:  # > 5% outperformance
                return 100
            elif relative_performance > 0:
                return 50 + (relative_performance * 1000)  # Scale 0-5% to 50-100
            else:
                return max(0, 50 + (relative_performance * 500))  # Scale negative performance

        except Exception:
            return 50

    def calculate_momentum_score(self, ticker: str) -> Dict[str, Any]:
        """Calculate comprehensive momentum score for a ticker"""
        # Check cache first
        cache_key = f"momentum_{ticker}"
        current_time = time.time()

        if cache_key in self._cache:
            cached_data, cache_time = self._cache[cache_key]
            if current_time - cache_time < self._cache_ttl:
                return cached_data

        hist_data, stock_info = self.get_stock_data(ticker)

        if hist_data is None or len(hist_data) < 50:
            result = {
                'ticker': ticker,
                'composite_score': 0,
                'rating': 'Insufficient Data',
                'price_momentum': 0,
                'technical_momentum': 0,
                'relative_momentum': 0,
                'current_price': None
            }
            # Cache the insufficient data result too
            self._cache[cache_key] = (result, current_time)
            return result

        # Calculate individual components
        # Fixed income ETFs use AGG as relative-momentum benchmark
        is_fi = self._is_fixed_income(stock_info or {})
        price_momentum = self.calculate_price_momentum(hist_data)
        technical_momentum = self.calculate_technical_momentum(hist_data)
        if is_fi:
            relative_momentum = self.calculate_relative_momentum(ticker, hist_data, benchmark='AGG')
            fundamental_momentum = self.calculate_fixed_income_fundamental(stock_info or {}, hist_data)
        else:
            relative_momentum = self.calculate_relative_momentum(ticker, hist_data)
            fundamental_momentum = self.calculate_fundamental_momentum(stock_info or {})

        # Calculate weighted composite score (fundamental component removed)
        composite_score = (
            price_momentum     * self.weights['price_momentum'] +
            technical_momentum * self.weights['technical_momentum'] +
            relative_momentum  * self.weights['relative_momentum']
        )

        # Determine rating
        if composite_score >= 80:
            rating = 'Strong Buy'
        elif composite_score >= 65:
            rating = 'Buy'
        elif composite_score >= 50:
            rating = 'Hold'
        elif composite_score >= 35:
            rating = 'Weak Hold'
        else:
            rating = 'Sell'

        # Get current price from historical data
        current_price = float(hist_data['Close'].iloc[-1]) if hist_data is not None and not hist_data.empty else None

        result = {
            'ticker': ticker,
            'composite_score': round(composite_score, 1),
            'rating': rating,
            'price_momentum': round(price_momentum, 1),
            'technical_momentum': round(technical_momentum, 1),
            'fundamental_momentum': round(fundamental_momentum, 1),
            'relative_momentum': round(relative_momentum, 1),
            'current_price': current_price,
            'scoring_model': 'fixed_income' if is_fi else 'equity',
        }

        # Cache the result
        self._cache[cache_key] = (result, current_time)

        # Record historical data (only for successful calculations)
        if result['composite_score'] > 0:
            try:
                self.historical_service.record_momentum_score(ticker, result)
            except Exception as e:
                # Don't fail the main calculation if historical recording fails
                logger.warning(
                    f"Failed to record historical data for {ticker}",
                    extra={'ticker': ticker, 'error': str(e)},
                    exc_info=True
                )

        return result

    def calculate_momentum_score_debug(self, ticker: str) -> Dict[str, Any]:
        """Full scoring breakdown for a single ticker — bypasses in-memory cache."""
        hist_data, stock_info = self.get_stock_data(ticker)

        if hist_data is None or len(hist_data) < 50:
            return {"error": "Insufficient data", "data_points": len(hist_data) if hist_data is not None else 0}

        current_price = float(hist_data['Close'].iloc[-1])

        # ---- price momentum internals ----
        pm_debug: Dict[str, Any] = {}
        if len(hist_data) >= 249:
            ma_20  = float(hist_data['Close'].rolling(20).mean().iloc[-1])
            ma_50  = float(hist_data['Close'].rolling(50).mean().iloc[-1])
            ma_200 = float(hist_data['Close'].rolling(200).mean().iloc[-1])
            direction_score = sum([7 if current_price > ma_20 else 0,
                                   6 if current_price > ma_50 else 0,
                                   7 if current_price > ma_200 else 0])

            periods = {'1m': 21, '3m': 63, '6m': 126, '12m': 249}
            returns = {p: round((current_price / float(hist_data['Close'].iloc[-d])) - 1, 4)
                       for p, d in periods.items()}
            w = {'1m': 0.4, '3m': 0.3, '6m': 0.2, '12m': 0.1}
            weighted_return = sum(returns[p] * w[p] for p in returns)
            magnitude_score = max(0.0, min(40.0, 20.0 + weighted_return * 80.0))

            r1m_ann = (1.0 + returns['1m']) ** 12 - 1.0
            r3m_ann = (1.0 + returns['3m']) **  4 - 1.0
            return_accel = r1m_ann - r3m_ann
            ma20_series = hist_data['Close'].rolling(20).mean()
            ma20_prev = float(ma20_series.iloc[-11])
            ma20_slope_ann = ((float(ma20_series.iloc[-1]) / ma20_prev) - 1.0) * 25.0 if ma20_prev > 0 else 0.0
            combined_accel = 0.7 * return_accel + 0.3 * ma20_slope_ann
            accel_score = max(0.0, min(40.0, 20.0 + combined_accel * 30.0))

            pm_debug = {
                "ma_20": round(ma_20, 2), "ma_50": round(ma_50, 2), "ma_200": round(ma_200, 2),
                "price_vs_ma20": current_price > ma_20,
                "price_vs_ma50": current_price > ma_50,
                "price_vs_ma200": current_price > ma_200,
                "direction_score": direction_score,
                "period_returns": returns,
                "weighted_return": round(weighted_return, 4),
                "magnitude_score": round(magnitude_score, 2),
                "r1m_annualised": round(r1m_ann, 4),
                "r3m_annualised": round(r3m_ann, 4),
                "return_acceleration": round(return_accel, 4),
                "ma20_slope_ann": round(ma20_slope_ann, 4),
                "combined_acceleration": round(combined_accel, 4),
                "accel_score": round(accel_score, 2),
                "price_momentum_total": round(min(100.0, direction_score + magnitude_score + accel_score), 2),
            }

        # ---- technical momentum internals ----
        tm_debug: Dict[str, Any] = {}
        if len(hist_data) >= 50:
            delta = hist_data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))
            current_rsi = float(rsi_series.iloc[-1])

            if 50 <= current_rsi <= 70:
                rsi_score = 100.0
            elif 30 <= current_rsi < 50:
                rsi_score = (current_rsi - 30) * 2.5
            elif 70 < current_rsi <= 85:
                rsi_score = 100 - ((current_rsi - 70) * 2)
            else:
                rsi_score = 0.0

            avg_volume = float(hist_data['Volume'].rolling(30).mean().iloc[-1])
            current_volume = float(hist_data['Volume'].iloc[-1])
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_score = min(100.0, volume_ratio * 50)

            price_10d_ago = float(hist_data['Close'].iloc[-10])
            roc = ((current_price / price_10d_ago) - 1) * 100
            roc_score = min(100.0, max(0.0, roc * 10 + 50))

            technical_total = (rsi_score * 0.4) + (volume_score * 0.3) + (roc_score * 0.3)
            tm_debug = {
                "rsi": round(current_rsi, 2),
                "rsi_score": round(rsi_score, 2),
                "avg_volume_30d": round(avg_volume, 0),
                "current_volume": round(current_volume, 0),
                "volume_ratio": round(volume_ratio, 3),
                "volume_score": round(volume_score, 2),
                "roc_10d_pct": round(roc, 3),
                "roc_score": round(roc_score, 2),
                "technical_momentum_total": round(min(100.0, max(0.0, technical_total)), 2),
            }

        # ---- relative momentum internals ----
        rm_debug: Dict[str, Any] = {}
        try:
            benchmark_data, _ = self.get_stock_data('SPY', '1y')
            if benchmark_data is not None and len(benchmark_data) >= 21 and len(hist_data) >= 21:
                stock_ret = (float(hist_data['Close'].iloc[-1]) / float(hist_data['Close'].iloc[-21])) - 1
                bench_ret = (float(benchmark_data['Close'].iloc[-1]) / float(benchmark_data['Close'].iloc[-21])) - 1
                rel_perf = stock_ret - bench_ret
                if rel_perf > 0.05:
                    rm_score = 100.0
                elif rel_perf > 0:
                    rm_score = 50 + rel_perf * 1000
                else:
                    rm_score = max(0.0, 50 + rel_perf * 500)
                rm_debug = {
                    "stock_1m_return": round(stock_ret, 4),
                    "spy_1m_return": round(bench_ret, 4),
                    "relative_performance": round(rel_perf, 4),
                    "relative_momentum_total": round(rm_score, 2),
                    "threshold_for_100": 0.05,
                }
        except Exception:
            rm_debug = {"error": "Could not compute relative momentum"}

        # ---- fundamental internals ----
        fm_debug: Dict[str, Any] = {}
        is_fi = self._is_fixed_income(stock_info or {})
        if not is_fi:
            fwd_pe  = (stock_info or {}).get('forwardPE', 0) or 0
            trail_pe = (stock_info or {}).get('trailingPE', 0) or 0
            peg     = (stock_info or {}).get('pegRatio', 0) or 0
            fm_debug = {
                "forward_pe": fwd_pe, "trailing_pe": trail_pe, "peg_ratio": peg,
                "note": "fundamental_momentum is computed but excluded from composite score",
            }

        # ---- cache state ----
        cache_key = f"momentum_{ticker}"
        cached = cache_key in self._cache
        cache_age_s = None
        if cached:
            _, cache_time = self._cache[cache_key]
            cache_age_s = round(time.time() - cache_time, 0)

        # ---- composite ----
        price_momentum = self.calculate_price_momentum(hist_data)
        technical_momentum = self.calculate_technical_momentum(hist_data)
        is_fi = self._is_fixed_income(stock_info or {})
        relative_momentum = self.calculate_relative_momentum(ticker, hist_data, 'AGG' if is_fi else 'SPY')
        composite = (price_momentum * self.weights['price_momentum']
                     + technical_momentum * self.weights['technical_momentum']
                     + relative_momentum  * self.weights['relative_momentum'])

        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "data_points": len(hist_data),
            "scoring_model": "fixed_income" if is_fi else "equity",
            "weights": self.weights,
            "composite_score": round(composite, 2),
            "price_momentum": round(price_momentum, 2),
            "technical_momentum": round(technical_momentum, 2),
            "relative_momentum": round(relative_momentum, 2),
            "cache_state": {"cached": cached, "age_seconds": cache_age_s},
            "price_momentum_breakdown": pm_debug,
            "technical_momentum_breakdown": tm_debug,
            "relative_momentum_breakdown": rm_debug,
            "fundamental_inputs": fm_debug,
        }

    def clear_cache(self) -> None:
        """Clear the momentum score cache"""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        current_time: float = time.time()
        valid_entries: int = sum(1 for _, (_, cache_time) in self._cache.items()
                          if current_time - cache_time < self._cache_ttl)
        return {
            'total_entries': len(self._cache),
            'valid_entries': valid_entries,
            'cache_ttl_seconds': self._cache_ttl
        }