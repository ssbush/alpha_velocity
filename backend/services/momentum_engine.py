import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
import warnings
import time
import logging
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
            'price_momentum': 0.40,
            'technical_momentum': 0.25,
            'fundamental_momentum': 0.25,
            'relative_momentum': 0.10
        }
        self.price_service: 'PriceService' = price_service or PriceService()

        # Simple memory cache for momentum scores (24 hour TTL)
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._cache_ttl: int = 86400  # 24 hours (until next trading day)

        # Historical data service
        self.historical_service: HistoricalDataService = HistoricalDataService()

    def get_stock_data(self, ticker: str, period: str = '1y') -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
        """Fetch stock data via price service"""
        return self.price_service.get_stock_data(ticker, period)

    def calculate_price_momentum(self, hist_data: pd.DataFrame) -> float:
        """Calculate price momentum component (40% of total score)"""
        if len(hist_data) < 249:
            return 0

        current_price = hist_data['Close'].iloc[-1]

        # Calculate returns over different periods
        returns = {}
        periods = {
            '1m': 21,   # 1 month
            '3m': 63,   # 3 months
            '6m': 126,  # 6 months
            '12m': 249  # 12 months
        }

        for period, days in periods.items():
            if len(hist_data) >= days:
                past_price = hist_data['Close'].iloc[-days]
                returns[period] = (current_price / past_price) - 1
            else:
                returns[period] = 0

        # Weight recent performance more heavily
        weights = {'1m': 0.4, '3m': 0.3, '6m': 0.2, '12m': 0.1}
        weighted_return = sum(returns[period] * weights[period] for period in returns)

        # Moving average signals
        ma_20 = hist_data['Close'].rolling(20).mean().iloc[-1]
        ma_50 = hist_data['Close'].rolling(50).mean().iloc[-1]
        ma_200 = hist_data['Close'].rolling(200).mean().iloc[-1]

        ma_score = 0
        if current_price > ma_20:
            ma_score += 0.4
        if current_price > ma_50:
            ma_score += 0.3
        if current_price > ma_200:
            ma_score += 0.3

        # Combine weighted return and MA signals
        momentum_score = (weighted_return * 100) + (ma_score * 100)

        return min(100, max(0, momentum_score))

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
                    'fundamental_momentum': 0,
                    'relative_momentum': 0
                }

            # Calculate individual components using historical data up to target date
            price_momentum = self.calculate_price_momentum(hist_data)
            technical_momentum = self.calculate_technical_momentum(hist_data)

            # For fundamental data, we'll use a simplified approach since historical fundamentals are harder to get
            # Use a base score with some variation based on price performance
            recent_return = (hist_data['Close'].iloc[-1] / hist_data['Close'].iloc[-21] - 1) if len(hist_data) >= 21 else 0
            fundamental_momentum = max(30, min(90, 60 + (recent_return * 100)))  # Scale around 60

            # Calculate relative momentum against SPY for the same period
            relative_momentum = self.calculate_historical_relative_momentum(ticker, hist_data, target_date)

            # Calculate weighted composite score
            composite_score = (
                price_momentum * self.weights['price_momentum'] +
                technical_momentum * self.weights['technical_momentum'] +
                fundamental_momentum * self.weights['fundamental_momentum'] +
                relative_momentum * self.weights['relative_momentum']
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
                'fundamental_momentum': round(fundamental_momentum, 1),
                'relative_momentum': round(relative_momentum, 1)
            }

        except Exception as e:
            # Fallback to a reasonable default based on historical context
            return {
                'ticker': ticker,
                'composite_score': 60.0,  # Neutral score for historical data
                'rating': 'Hold',
                'price_momentum': 60.0,
                'technical_momentum': 60.0,
                'fundamental_momentum': 60.0,
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
                'fundamental_momentum': 0,
                'relative_momentum': 0,
                'current_price': None
            }
            # Cache the insufficient data result too
            self._cache[cache_key] = (result, current_time)
            return result

        # Calculate individual components
        # Fixed income ETFs use yield+trend scoring and AGG as benchmark
        is_fi = self._is_fixed_income(stock_info or {})
        price_momentum = self.calculate_price_momentum(hist_data)
        technical_momentum = self.calculate_technical_momentum(hist_data)
        if is_fi:
            fundamental_momentum = self.calculate_fixed_income_fundamental(stock_info or {}, hist_data)
            relative_momentum = self.calculate_relative_momentum(ticker, hist_data, benchmark='AGG')
        else:
            fundamental_momentum = self.calculate_fundamental_momentum(stock_info or {})
            relative_momentum = self.calculate_relative_momentum(ticker, hist_data)

        # Calculate weighted composite score
        composite_score = (
            price_momentum * self.weights['price_momentum'] +
            technical_momentum * self.weights['technical_momentum'] +
            fundamental_momentum * self.weights['fundamental_momentum'] +
            relative_momentum * self.weights['relative_momentum']
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