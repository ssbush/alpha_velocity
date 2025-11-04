"""
Database-enabled Portfolio Service for AlphaVelocity

Manages portfolios using PostgreSQL database instead of JSON files
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database.config import db_config
from models.database import (
    User, Portfolio, SecurityMaster, Category, Holding, Transaction,
    MomentumScore, PriceHistory, PerformanceSnapshot, PortfolioCategoryTarget
)
from services.momentum_engine import MomentumEngine
from utils.data_providers import DataProvider

class DatabasePortfolioService:
    """Portfolio service using PostgreSQL database"""

    def __init__(self, momentum_engine: MomentumEngine = None):
        self.momentum_engine = momentum_engine or MomentumEngine()
        self.data_provider = DataProvider()

    def get_portfolio_category_targets(self, portfolio_id: int, session: Session) -> Dict[int, Decimal]:
        """Get portfolio-specific category targets, falling back to global defaults

        Returns: Dict mapping category_id to target_allocation_pct
        """
        # First try to get portfolio-specific targets
        targets = session.query(PortfolioCategoryTarget).filter_by(
            portfolio_id=portfolio_id
        ).all()

        if targets:
            return {t.category_id: t.target_allocation_pct for t in targets}

        # Fall back to global category targets
        categories = session.query(Category).filter_by(is_active=True).all()
        return {c.id: c.target_allocation_pct for c in categories}

    def get_user_portfolios(self, user_id: int) -> List[Dict]:
        """Get all portfolios for a user"""
        with db_config.get_session_context() as session:
            portfolios = session.query(Portfolio).filter_by(
                user_id=user_id,
                is_active=True
            ).all()

            return [{
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'created_at': p.created_at.isoformat(),
                'updated_at': p.updated_at.isoformat()
            } for p in portfolios]

    def get_portfolio_holdings(self, portfolio_id: int) -> List[Dict]:
        """Get all holdings for a portfolio with current market values"""
        with db_config.get_session_context() as session:
            holdings = session.query(Holding).join(SecurityMaster).filter(
                Holding.portfolio_id == portfolio_id
            ).all()

            results = []
            total_value = Decimal('0')

            for holding in holdings:
                # Get current price
                try:
                    hist_data, _ = self.data_provider.get_stock_data(holding.security.ticker, '1d')
                    if hist_data is not None and not hist_data.empty:
                        current_price = Decimal(str(hist_data['Close'].iloc[-1]))
                    else:
                        current_price = Decimal('0')
                except:
                    current_price = Decimal('0')

                market_value = holding.shares * current_price
                total_value += market_value

                # Get latest momentum score
                momentum_score = session.query(MomentumScore).filter_by(
                    security_id=holding.security_id
                ).order_by(desc(MomentumScore.score_date)).first()

                results.append({
                    'id': holding.id,
                    'ticker': holding.security.ticker,
                    'company_name': holding.security.company_name,
                    'shares': float(holding.shares),
                    'current_price': float(current_price),
                    'market_value': float(market_value),
                    'cost_basis': float(holding.average_cost_basis) if holding.average_cost_basis else None,
                    'category': holding.category.name if holding.category else 'Uncategorized',
                    'momentum_score': float(momentum_score.composite_score) if momentum_score else 0,
                    'momentum_rating': momentum_score.rating if momentum_score else 'N/A'
                })

            # Calculate portfolio percentages
            total_value_float = float(total_value)
            for holding in results:
                holding['portfolio_percentage'] = (
                    (holding['market_value'] / total_value_float * 100) if total_value_float > 0 else 0
                )

            return results, total_value_float

    def get_category_analysis(self, portfolio_id: int) -> Dict:
        """Analyze portfolio by categories"""
        with db_config.get_session_context() as session:
            # Get all categories with their target allocations
            categories = session.query(Category).filter_by(is_active=True).all()

            # Get portfolio holdings by category
            category_analysis = {}
            total_portfolio_value = Decimal('0')

            for category in categories:
                holdings = session.query(Holding).join(SecurityMaster).filter(
                    Holding.portfolio_id == portfolio_id,
                    Holding.category_id == category.id
                ).all()

                category_value = Decimal('0')
                position_count = 0

                for holding in holdings:
                    try:
                        hist_data, _ = self.data_provider.get_stock_data(holding.security.ticker, '1d')
                        if hist_data is not None and not hist_data.empty:
                            current_price = Decimal(str(hist_data['Close'].iloc[-1]))
                            market_value = holding.shares * current_price
                            category_value += market_value
                            position_count += 1
                    except:
                        continue

                total_portfolio_value += category_value

                category_analysis[category.name] = {
                    'target_allocation_pct': float(category.target_allocation_pct) if category.target_allocation_pct else 0,
                    'current_value': float(category_value),
                    'position_count': position_count,
                    'benchmark_ticker': category.benchmark_ticker
                }

            # Calculate actual percentages
            total_value_float = float(total_portfolio_value)
            for category_name, data in category_analysis.items():
                data['actual_allocation_pct'] = (
                    (data['current_value'] / total_value_float * 100) if total_value_float > 0 else 0
                )
                data['allocation_difference'] = data['actual_allocation_pct'] - data['target_allocation_pct']

            return {
                'total_portfolio_value': total_value_float,
                'categories': category_analysis
            }

    def add_transaction(self, portfolio_id: int, ticker: str, transaction_type: str,
                       shares: float, price_per_share: float, transaction_date: date = None,
                       fees: float = 0, notes: str = None) -> Dict:
        """Add a new transaction and update holdings"""
        if transaction_date is None:
            transaction_date = date.today()

        with db_config.get_session_context() as session:
            # Get or create security
            security = session.query(SecurityMaster).filter_by(ticker=ticker).first()
            if not security:
                # Create new security (basic info)
                security = SecurityMaster(
                    ticker=ticker,
                    company_name=ticker,  # Will be updated later
                    security_type='STOCK'
                )
                session.add(security)
                session.flush()

            # Determine category for this ticker
            # Look up in category_securities table
            category_id = None
            result = session.execute(
                """
                SELECT category_id FROM category_securities
                WHERE security_id = :security_id
                LIMIT 1
                """,
                {"security_id": security.id}
            ).fetchone()

            if result:
                category_id = result[0]
            else:
                # Use "Uncategorized" as default (id=16)
                uncategorized = session.query(Category).filter_by(name='Uncategorized').first()
                if uncategorized:
                    category_id = uncategorized.id

            # Create transaction
            total_amount = shares * Decimal(str(price_per_share))
            if transaction_type == 'SELL':
                shares = -abs(shares)  # Ensure sells are negative
                total_amount = -abs(total_amount)

            transaction = Transaction(
                portfolio_id=portfolio_id,
                security_id=security.id,
                transaction_type=transaction_type,
                transaction_date=transaction_date,
                shares=Decimal(str(shares)),
                price_per_share=Decimal(str(price_per_share)),
                total_amount=total_amount,
                fees=Decimal(str(fees)),
                notes=notes
            )
            session.add(transaction)

            # Update or create holding
            holding = session.query(Holding).filter_by(
                portfolio_id=portfolio_id,
                security_id=security.id
            ).first()

            if not holding:
                # Create new holding with category
                holding = Holding(
                    portfolio_id=portfolio_id,
                    security_id=security.id,
                    category_id=category_id,
                    shares=Decimal(str(abs(shares))),
                    average_cost_basis=Decimal(str(price_per_share)),
                    total_cost_basis=abs(total_amount)
                )
                session.add(holding)
            else:
                # Update existing holding
                new_shares = holding.shares + Decimal(str(shares))

                if new_shares > 0:
                    # Update weighted average cost basis for buys
                    if transaction_type == 'BUY':
                        total_cost = (holding.total_cost_basis or Decimal('0')) + abs(total_amount)
                        holding.average_cost_basis = total_cost / new_shares
                        holding.total_cost_basis = total_cost

                    holding.shares = new_shares
                else:
                    # Position closed
                    holding.shares = Decimal('0')

            session.flush()

            return {
                'transaction_id': transaction.id,
                'ticker': ticker,
                'transaction_type': transaction_type,
                'shares': float(shares),
                'price_per_share': float(price_per_share),
                'total_amount': float(total_amount),
                'fees': float(fees),
                'transaction_date': transaction_date.isoformat()
            }

    def get_transaction_history(self, portfolio_id: int, limit: int = 50) -> List[Dict]:
        """Get recent transaction history for a portfolio"""
        with db_config.get_session_context() as session:
            transactions = session.query(Transaction).join(SecurityMaster).filter(
                Transaction.portfolio_id == portfolio_id
            ).order_by(desc(Transaction.transaction_date), desc(Transaction.id)).limit(limit).all()

            return [{
                'id': t.id,
                'ticker': t.security.ticker,
                'company_name': t.security.company_name,
                'transaction_type': t.transaction_type,
                'shares': float(t.shares),
                'price_per_share': float(t.price_per_share) if t.price_per_share else None,
                'total_amount': float(t.total_amount),
                'fees': float(t.fees),
                'transaction_date': t.transaction_date.isoformat(),
                'notes': t.notes,
                'created_at': t.created_at.isoformat()
            } for t in transactions]

    def record_performance_snapshot(self, portfolio_id: int, snapshot_date: date = None) -> Dict:
        """Record daily performance snapshot for a portfolio"""
        if snapshot_date is None:
            snapshot_date = date.today()

        with db_config.get_session_context() as session:
            # Check if snapshot already exists
            existing = session.query(PerformanceSnapshot).filter_by(
                portfolio_id=portfolio_id,
                snapshot_date=snapshot_date
            ).first()

            if existing:
                return {'message': 'Snapshot already exists for this date'}

            # Calculate current portfolio metrics
            holdings, total_value = self.get_portfolio_holdings(portfolio_id)

            # Calculate momentum metrics
            momentum_scores = [h['momentum_score'] for h in holdings if h['momentum_score'] > 0]
            avg_momentum = sum(momentum_scores) / len(momentum_scores) if momentum_scores else 0

            # Calculate cost basis and P&L
            total_cost_basis = sum(
                (h['cost_basis'] or 0) * h['shares']
                for h in holdings
                if h['cost_basis']
            )
            unrealized_gain_loss = total_value - total_cost_basis if total_cost_basis > 0 else None

            # Create snapshot
            snapshot = PerformanceSnapshot(
                portfolio_id=portfolio_id,
                snapshot_date=snapshot_date,
                total_value=Decimal(str(total_value)),
                total_cost_basis=Decimal(str(total_cost_basis)) if total_cost_basis > 0 else None,
                unrealized_gain_loss=Decimal(str(unrealized_gain_loss)) if unrealized_gain_loss is not None else None,
                average_momentum_score=Decimal(str(avg_momentum)),
                number_of_positions=len(holdings)
            )
            session.add(snapshot)
            session.flush()

            return {
                'snapshot_id': snapshot.id,
                'portfolio_id': portfolio_id,
                'snapshot_date': snapshot_date.isoformat(),
                'total_value': total_value,
                'total_cost_basis': total_cost_basis,
                'unrealized_gain_loss': unrealized_gain_loss,
                'average_momentum_score': avg_momentum,
                'number_of_positions': len(holdings)
            }

    def get_performance_history(self, portfolio_id: int, days: int = 365) -> List[Dict]:
        """Get performance history for charting"""
        with db_config.get_session_context() as session:
            snapshots = session.query(PerformanceSnapshot).filter(
                PerformanceSnapshot.portfolio_id == portfolio_id
            ).order_by(desc(PerformanceSnapshot.snapshot_date)).limit(days).all()

            # Reverse to get chronological order
            snapshots.reverse()

            return [{
                'date': s.snapshot_date.isoformat(),
                'total_value': float(s.total_value),
                'average_momentum_score': float(s.average_momentum_score) if s.average_momentum_score else 0,
                'number_of_positions': s.number_of_positions,
                'unrealized_gain_loss': float(s.unrealized_gain_loss) if s.unrealized_gain_loss else None
            } for s in snapshots]

    def update_momentum_scores(self, portfolio_id: int) -> Dict:
        """Update momentum scores for all securities in portfolio"""
        with db_config.get_session_context() as session:
            # Get all securities in portfolio
            securities = session.query(SecurityMaster).join(Holding).filter(
                Holding.portfolio_id == portfolio_id
            ).distinct().all()

            updated_count = 0
            today = date.today()

            for security in securities:
                # Check if we already have today's score
                existing_score = session.query(MomentumScore).filter_by(
                    security_id=security.id,
                    score_date=today
                ).first()

                if existing_score:
                    continue

                # Calculate new momentum score
                try:
                    momentum_result = self.momentum_engine.calculate_momentum_score(security.ticker)

                    if momentum_result['composite_score'] > 0:
                        momentum_score = MomentumScore(
                            security_id=security.id,
                            score_date=today,
                            composite_score=Decimal(str(momentum_result['composite_score'])),
                            price_momentum=Decimal(str(momentum_result['price_momentum'])),
                            technical_momentum=Decimal(str(momentum_result['technical_momentum'])),
                            fundamental_momentum=Decimal(str(momentum_result['fundamental_momentum'])),
                            relative_momentum=Decimal(str(momentum_result['relative_momentum'])),
                            rating=momentum_result['rating']
                        )
                        session.add(momentum_score)
                        updated_count += 1
                except Exception as e:
                    print(f"Error calculating momentum for {security.ticker}: {e}")
                    continue

            session.flush()

            return {
                'updated_securities': updated_count,
                'total_securities': len(securities),
                'update_date': today.isoformat()
            }