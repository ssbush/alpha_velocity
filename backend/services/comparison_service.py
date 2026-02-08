from typing import Dict, List, Tuple, Optional
import pandas as pd
from datetime import datetime
import logging
from .portfolio_service import PortfolioService

logger = logging.getLogger(__name__)
from ..models.comparison import (
    PortfolioComparison, PortfolioSummary, AllocationComparison,
    HoldingComparison, PerformanceComparison, DiversificationMetrics
)
from ..models.portfolio import PortfolioHolding

class ComparisonService:
    """Service for comparing portfolios side-by-side"""

    def __init__(self, portfolio_service: PortfolioService) -> None:
        self.portfolio_service: PortfolioService = portfolio_service

    def compare_portfolios(self, portfolio_a: Dict[str, int], portfolio_b: Dict[str, int],
                          portfolio_a_id: str = "custom", portfolio_b_id: str = "model") -> PortfolioComparison:
        """Compare two portfolios comprehensively"""

        # Analyze both portfolios
        portfolio_a_analysis = self._analyze_single_portfolio(portfolio_a, portfolio_a_id, "Custom Portfolio")
        portfolio_b_analysis = self._analyze_single_portfolio(portfolio_b, portfolio_b_id, "Model Portfolio")

        # Create detailed comparisons
        allocation_comparison = self._compare_allocations(portfolio_a, portfolio_b)
        holding_comparison = self._compare_holdings(portfolio_a, portfolio_b)
        performance_comparison = self._compare_performance(portfolio_a_analysis, portfolio_b_analysis)

        # Calculate diversification metrics
        diversification_a = self._calculate_diversification_metrics(portfolio_a_analysis, portfolio_a_id)
        diversification_b = self._calculate_diversification_metrics(portfolio_b_analysis, portfolio_b_id)

        # Generate recommendations and key differences
        recommendation, key_differences = self._generate_recommendations(
            portfolio_a_analysis, portfolio_b_analysis, allocation_comparison, performance_comparison
        )

        return PortfolioComparison(
            portfolio_a=portfolio_a_analysis,
            portfolio_b=portfolio_b_analysis,
            allocation_comparison=allocation_comparison,
            holding_comparison=holding_comparison,
            performance_comparison=performance_comparison,
            diversification_a=diversification_a,
            diversification_b=diversification_b,
            recommendation=recommendation,
            key_differences=key_differences,
            comparison_date=datetime.now().isoformat()
        )

    def _analyze_single_portfolio(self, portfolio: Dict[str, int], portfolio_id: str, name: str) -> PortfolioSummary:
        """Analyze a single portfolio and return summary"""
        df, total_value, avg_score = self.portfolio_service.analyze_portfolio(portfolio)

        # Get top 5 holdings
        top_holdings = []
        for _, row in df.head(5).iterrows():
            top_holdings.append(PortfolioHolding(
                ticker=row['Ticker'],
                shares=row['Shares'],
                price=row['Price'],
                market_value=row['Market_Value'],
                portfolio_percent=row['Portfolio_%'],
                momentum_score=row['Momentum_Score'],
                rating=row['Rating'],
                price_momentum=row['Price_Momentum'],
                technical_momentum=row['Technical_Momentum']
            ))

        # Get performance analytics if available
        try:
            performance = self.portfolio_service.momentum_engine.historical_service.get_performance_analytics(portfolio_id)
        except:
            performance = None

        return PortfolioSummary(
            portfolio_id=portfolio_id,
            name=name,
            total_value=total_value,
            average_momentum_score=avg_score,
            number_of_positions=len(portfolio),
            top_holdings=top_holdings,
            performance=performance
        )

    def _compare_allocations(self, portfolio_a: Dict[str, int], portfolio_b: Dict[str, int]) -> List[AllocationComparison]:
        """Compare category allocations between portfolios"""
        allocation_comparisons = []

        # Calculate allocations for both portfolios
        allocation_a = self._calculate_category_allocation(portfolio_a)
        allocation_b = self._calculate_category_allocation(portfolio_b)

        # Get all categories
        all_categories = set(allocation_a.keys()) | set(allocation_b.keys())

        for category in all_categories:
            category_info = self.portfolio_service.portfolio_categories.get(category, {})
            target_percent = category_info.get('target_allocation', 0) * 100

            percent_a = allocation_a.get(category, 0) * 100
            percent_b = allocation_b.get(category, 0) * 100

            allocation_comparisons.append(AllocationComparison(
                category=category,
                portfolio_a_percent=percent_a,
                portfolio_b_percent=percent_b,
                difference=percent_a - percent_b,
                target_percent=target_percent,
                portfolio_a_gap=percent_a - target_percent,
                portfolio_b_gap=percent_b - target_percent
            ))

        # Sort by absolute difference
        allocation_comparisons.sort(key=lambda x: abs(x.difference), reverse=True)
        return allocation_comparisons

    def _calculate_category_allocation(self, portfolio: Dict[str, int]) -> Dict[str, float]:
        """Calculate category allocation for a portfolio"""
        # Get stock prices for calculation
        total_value = 0
        category_values = {}

        for ticker, shares in portfolio.items():
            try:
                hist_data, _ = self.portfolio_service.data_provider.get_stock_data(ticker, '1d')
                if hist_data is not None and not hist_data.empty:
                    price = hist_data['Close'].iloc[-1]
                    value = price * shares
                    total_value += value

                    # Find category for this ticker
                    category = self._find_ticker_category(ticker)
                    if category:
                        category_values[category] = category_values.get(category, 0) + value
            except Exception as e:
                logger.warning(
                    f"Error processing {ticker}",
                    extra={'ticker': ticker, 'error': str(e)}
                )
                continue

        # Convert to percentages
        if total_value > 0:
            return {category: value / total_value for category, value in category_values.items()}
        return {}

    def _find_ticker_category(self, ticker: str) -> str:
        """Find which category a ticker belongs to"""
        for category_name, category_info in self.portfolio_service.portfolio_categories.items():
            if ticker in category_info['tickers']:
                return category_name
        return "Other"

    def _compare_holdings(self, portfolio_a: Dict[str, int], portfolio_b: Dict[str, int]) -> List[HoldingComparison]:
        """Compare individual holdings between portfolios"""
        holding_comparisons = []
        all_tickers = set(portfolio_a.keys()) | set(portfolio_b.keys())

        # Calculate total values for percentage calculations
        total_value_a = self._calculate_total_value(portfolio_a)
        total_value_b = self._calculate_total_value(portfolio_b)

        for ticker in all_tickers:
            in_a = ticker in portfolio_a
            in_b = ticker in portfolio_b

            weight_a = None
            weight_b = None
            score_a = None
            score_b = None

            if in_a:
                shares_a = portfolio_a[ticker]
                try:
                    hist_data, _ = self.portfolio_service.data_provider.get_stock_data(ticker, '1d')
                    if hist_data is not None and not hist_data.empty:
                        price = hist_data['Close'].iloc[-1]
                        weight_a = (price * shares_a / total_value_a) * 100 if total_value_a > 0 else 0

                    momentum_result = self.portfolio_service.momentum_engine.calculate_momentum_score(ticker)
                    score_a = momentum_result['composite_score']
                except:
                    pass

            if in_b:
                shares_b = portfolio_b[ticker]
                try:
                    hist_data, _ = self.portfolio_service.data_provider.get_stock_data(ticker, '1d')
                    if hist_data is not None and not hist_data.empty:
                        price = hist_data['Close'].iloc[-1]
                        weight_b = (price * shares_b / total_value_b) * 100 if total_value_b > 0 else 0

                    if score_a is None:  # Avoid duplicate calculation
                        momentum_result = self.portfolio_service.momentum_engine.calculate_momentum_score(ticker)
                        score_b = momentum_result['composite_score']
                    else:
                        score_b = score_a  # Same score since it's the same ticker
                except:
                    pass

            weight_diff = None
            score_diff = None
            if weight_a is not None and weight_b is not None:
                weight_diff = weight_a - weight_b
            if score_a is not None and score_b is not None:
                score_diff = score_a - score_b

            holding_comparisons.append(HoldingComparison(
                ticker=ticker,
                in_portfolio_a=in_a,
                in_portfolio_b=in_b,
                portfolio_a_weight=weight_a,
                portfolio_b_weight=weight_b,
                portfolio_a_score=score_a,
                portfolio_b_score=score_b,
                weight_difference=weight_diff,
                score_difference=score_diff
            ))

        # Sort by weight difference (largest differences first)
        holding_comparisons.sort(
            key=lambda x: abs(x.weight_difference) if x.weight_difference is not None else 0,
            reverse=True
        )
        return holding_comparisons

    def _calculate_total_value(self, portfolio: Dict[str, int]) -> float:
        """Calculate total portfolio value"""
        total_value = 0
        for ticker, shares in portfolio.items():
            try:
                hist_data, _ = self.portfolio_service.data_provider.get_stock_data(ticker, '1d')
                if hist_data is not None and not hist_data.empty:
                    price = hist_data['Close'].iloc[-1]
                    total_value += price * shares
            except:
                continue
        return total_value

    def _compare_performance(self, portfolio_a: PortfolioSummary, portfolio_b: PortfolioSummary) -> List[PerformanceComparison]:
        """Compare performance metrics between portfolios"""
        comparisons = []

        # Basic metrics comparison
        metrics = [
            ("Total Value", portfolio_a.total_value, portfolio_b.total_value),
            ("Average Momentum Score", portfolio_a.average_momentum_score, portfolio_b.average_momentum_score),
            ("Number of Positions", float(portfolio_a.number_of_positions), float(portfolio_b.number_of_positions))
        ]

        # Add historical performance metrics if available
        if portfolio_a.performance and portfolio_b.performance:
            metrics.extend([
                ("Total Return (%)", portfolio_a.performance.total_return, portfolio_b.performance.total_return),
                ("Daily Return (%)", portfolio_a.performance.daily_return, portfolio_b.performance.daily_return),
                ("Volatility (%)", portfolio_a.performance.volatility, portfolio_b.performance.volatility),
                ("Sharpe Ratio", portfolio_a.performance.sharpe_ratio, portfolio_b.performance.sharpe_ratio),
                ("Max Drawdown (%)", portfolio_a.performance.max_drawdown, portfolio_b.performance.max_drawdown)
            ])

        for metric, value_a, value_b in metrics:
            difference = value_a - value_b

            # Determine winner based on metric type
            if metric in ["Total Value", "Average Momentum Score", "Total Return (%)", "Daily Return (%)", "Sharpe Ratio"]:
                # Higher is better
                winner = "portfolio_a" if value_a > value_b else "portfolio_b" if value_b > value_a else "tie"
            elif metric in ["Volatility (%)", "Max Drawdown (%)"]:
                # Lower is better
                winner = "portfolio_a" if value_a < value_b else "portfolio_b" if value_b < value_a else "tie"
            else:
                # Neutral metrics
                winner = "tie" if abs(difference) < 0.01 else ("portfolio_a" if difference > 0 else "portfolio_b")

            comparisons.append(PerformanceComparison(
                metric=metric,
                portfolio_a_value=value_a,
                portfolio_b_value=value_b,
                difference=difference,
                winner=winner
            ))

        return comparisons

    def _calculate_diversification_metrics(self, portfolio: PortfolioSummary, portfolio_id: str) -> DiversificationMetrics:
        """Calculate diversification metrics for a portfolio"""
        holdings = portfolio.top_holdings

        # Calculate concentration ratio (top 5 holdings)
        if len(holdings) >= 5:
            top_5_weight = sum(float(h.portfolio_percent.rstrip('%')) for h in holdings[:5])
        else:
            top_5_weight = sum(float(h.portfolio_percent.rstrip('%')) for h in holdings)

        # Calculate sectors count (simplified - using categories as proxy)
        unique_categories = set()
        for holding in holdings:
            category = self._find_ticker_category(holding.ticker)
            if category != "Other":
                unique_categories.add(category)

        # Average position size
        average_position_size = 100.0 / portfolio.number_of_positions if portfolio.number_of_positions > 0 else 0

        # Largest position
        largest_position = max(float(h.portfolio_percent.rstrip('%')) for h in holdings) if holdings else 0

        return DiversificationMetrics(
            portfolio_id=portfolio_id,
            concentration_ratio=top_5_weight,
            sector_count=len(unique_categories),
            average_position_size=average_position_size,
            largest_position_percent=largest_position
        )

    def _generate_recommendations(self, portfolio_a: PortfolioSummary, portfolio_b: PortfolioSummary,
                                allocation_comparison: List[AllocationComparison],
                                performance_comparison: List[PerformanceComparison]) -> Tuple[str, List[str]]:
        """Generate recommendations and key differences"""

        key_differences = []

        # Analyze momentum score difference
        score_diff = portfolio_a.average_momentum_score - portfolio_b.average_momentum_score
        if abs(score_diff) > 2:
            better_portfolio = "Custom" if score_diff > 0 else "Model"
            key_differences.append(f"{better_portfolio} portfolio has {abs(score_diff):.1f} points higher momentum score")

        # Analyze diversification
        pos_diff = portfolio_a.number_of_positions - portfolio_b.number_of_positions
        if abs(pos_diff) > 3:
            more_diverse = "Custom" if pos_diff > 0 else "Model"
            key_differences.append(f"{more_diverse} portfolio is more diversified with {abs(pos_diff)} additional positions")

        # Analyze allocation differences
        major_allocation_diffs = [ac for ac in allocation_comparison if abs(ac.difference) > 5]
        for diff in major_allocation_diffs[:3]:  # Top 3 differences
            higher_portfolio = "Custom" if diff.difference > 0 else "Model"
            key_differences.append(f"{higher_portfolio} portfolio has {abs(diff.difference):.1f}% more allocation to {diff.category}")

        # Generate overall recommendation
        performance_wins_a = sum(1 for pc in performance_comparison if pc.winner == "portfolio_a")
        performance_wins_b = sum(1 for pc in performance_comparison if pc.winner == "portfolio_b")

        if performance_wins_a > performance_wins_b:
            recommendation = "Custom portfolio shows better performance metrics and may be worth considering."
        elif performance_wins_b > performance_wins_a:
            recommendation = "Model portfolio demonstrates superior performance characteristics."
        else:
            recommendation = "Both portfolios show similar performance. Consider your risk tolerance and investment goals."

        # Add specific recommendations based on gaps
        large_gaps = [ac for ac in allocation_comparison if abs(ac.portfolio_a_gap) > 3]
        if large_gaps:
            recommendation += f" Consider rebalancing {large_gaps[0].category} allocation."

        return recommendation, key_differences