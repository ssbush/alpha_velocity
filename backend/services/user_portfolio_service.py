"""
User Portfolio Service
Handles portfolio CRUD operations for authenticated users
"""

import logging
from typing import Any, Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

from ..models.database import (
    Portfolio, Holding, Transaction, SecurityMaster,
    Category, PerformanceSnapshot
)


class UserPortfolioService:
    """Service for user portfolio management"""

    def __init__(self, db_session: Session) -> None:
        self.db: Session = db_session

    # ========== Portfolio CRUD ==========

    def create_portfolio(self, user_id: int, name: str, description: Optional[str] = None) -> Portfolio:
        """Create a new portfolio for a user"""
        # Check for duplicate name for this user
        existing = self.db.query(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.name == name,
            Portfolio.is_active == True
        ).first()

        if existing:
            raise ValueError(f"Portfolio '{name}' already exists")

        portfolio = Portfolio(
            user_id=user_id,
            name=name,
            description=description,
            is_active=True
        )

        try:
            self.db.add(portfolio)
            self.db.commit()
            self.db.refresh(portfolio)
            return portfolio
        except IntegrityError as e:
            self.db.rollback()
            raise ValueError(f"Error creating portfolio: {str(e)}")

    def get_portfolio(self, portfolio_id: int, user_id: int) -> Optional[Portfolio]:
        """Get a portfolio by ID (validates user ownership)"""
        return self.db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
            Portfolio.is_active == True
        ).first()

    def get_user_portfolios(self, user_id: int) -> List[Portfolio]:
        """Get all active portfolios for a user"""
        return self.db.query(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.is_active == True
        ).order_by(Portfolio.created_at.desc()).all()

    def update_portfolio(self, portfolio_id: int, user_id: int, **kwargs) -> Optional[Portfolio]:
        """Update portfolio details"""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None

        allowed_fields = ['name', 'description']
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(portfolio, field, value)

        try:
            self.db.commit()
            self.db.refresh(portfolio)
            return portfolio
        except IntegrityError:
            self.db.rollback()
            raise ValueError(f"Portfolio name already exists")

    def delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        """Soft delete a portfolio"""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False

        portfolio.is_active = False
        self.db.commit()
        return True

    # ========== Holdings Management ==========

    def get_portfolio_holdings(self, portfolio_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Get all holdings for a portfolio with enriched data"""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return []

        holdings = self.db.query(Holding).filter(
            Holding.portfolio_id == portfolio_id
        ).join(SecurityMaster).all()

        # Get category mapping from portfolio service
        try:
            from ..services.portfolio_service import PortfolioService
            from ..services.momentum_engine import MomentumEngine
            momentum_engine = MomentumEngine()
            portfolio_service = PortfolioService(momentum_engine)
            categories = portfolio_service.get_all_categories()

            # Build ticker to category mapping
            ticker_to_category = {}
            for category_name, category_info in categories.items():
                for ticker in category_info['tickers']:
                    ticker_to_category[ticker] = category_name
        except Exception as e:
            logger.warning("Could not load category mapping: %s", e)
            ticker_to_category = {}

        result = []
        for holding in holdings:
            # Use database category if set, otherwise lookup from portfolio service
            category_name = None
            if holding.category:
                category_name = holding.category.name
            else:
                category_name = ticker_to_category.get(holding.security.ticker)

            # If still no category, try to get sector from price service as fallback
            if not category_name:
                try:
                    from .price_service import get_price_service
                    info = get_price_service().get_stock_info(holding.security.ticker)
                    sector = info.get('sector') if info else None
                    if sector:
                        category_name = f"{sector}"
                    else:
                        category_name = "Other Holdings"
                except Exception as e:
                    logger.warning("Could not fetch sector for %s: %s", holding.security.ticker, e)
                    category_name = "Other Holdings"

            result.append({
                'id': holding.id,
                'ticker': holding.security.ticker,
                'company_name': holding.security.company_name,
                'shares': float(holding.shares),
                'average_cost_basis': float(holding.average_cost_basis) if holding.average_cost_basis else None,
                'total_cost_basis': float(holding.total_cost_basis) if holding.total_cost_basis else None,
                'category': category_name,
                'security_type': holding.security.security_type
            })

        return result

    def add_or_update_holding(
        self,
        portfolio_id: int,
        user_id: int,
        ticker: str,
        shares: Decimal,
        average_cost_basis: Optional[Decimal] = None,
        category_name: Optional[str] = None
    ) -> Holding:
        """Add a new holding or update existing one"""
        # Validate portfolio ownership
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            raise ValueError("Portfolio not found")

        # Get or create security
        security = self._get_or_create_security(ticker)

        # Get category if provided
        category = None
        if category_name:
            category = self.db.query(Category).filter(Category.name == category_name).first()

        # Check if holding exists
        holding = self.db.query(Holding).filter(
            Holding.portfolio_id == portfolio_id,
            Holding.security_id == security.id
        ).first()

        if holding:
            # Update existing holding
            holding.shares = shares
            if average_cost_basis:
                holding.average_cost_basis = average_cost_basis
                holding.total_cost_basis = shares * average_cost_basis
            if category:
                holding.category_id = category.id
        else:
            # Create new holding
            total_cost_basis = shares * average_cost_basis if average_cost_basis else None
            holding = Holding(
                portfolio_id=portfolio_id,
                security_id=security.id,
                category_id=category.id if category else None,
                shares=shares,
                average_cost_basis=average_cost_basis,
                total_cost_basis=total_cost_basis
            )
            self.db.add(holding)

        self.db.commit()
        self.db.refresh(holding)
        return holding

    def remove_holding(self, portfolio_id: int, user_id: int, ticker: str) -> bool:
        """Remove a holding from portfolio"""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return False

        security = self.db.query(SecurityMaster).filter(
            SecurityMaster.ticker == ticker.upper()
        ).first()

        if not security:
            return False

        holding = self.db.query(Holding).filter(
            Holding.portfolio_id == portfolio_id,
            Holding.security_id == security.id
        ).first()

        if not holding:
            return False

        self.db.delete(holding)
        self.db.commit()
        return True

    # ========== Transactions ==========

    def add_transaction(
        self,
        portfolio_id: int,
        user_id: int,
        ticker: str,
        transaction_type: str,
        shares: Decimal,
        price_per_share: Decimal,
        transaction_date: date,
        fees: Decimal = Decimal('0'),
        notes: Optional[str] = None
    ) -> Transaction:
        """Add a transaction and update holdings"""
        # Validate portfolio ownership
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            raise ValueError("Portfolio not found")

        # Validate transaction type
        valid_types = ['BUY', 'SELL', 'DIVIDEND', 'SPLIT', 'REINVEST']
        if transaction_type.upper() not in valid_types:
            raise ValueError(f"Invalid transaction type. Must be one of: {valid_types}")

        # Get or create security
        security = self._get_or_create_security(ticker)

        # SPLIT-specific validation
        if transaction_type.upper() == 'SPLIT':
            if shares <= 0:
                raise ValueError("Split ratio must be greater than 0")
            if price_per_share != 0:
                raise ValueError("Price per share must be 0 for stock splits")
            # Must have an existing holding to split
            existing_holding = self.db.query(Holding).join(SecurityMaster).filter(
                Holding.portfolio_id == portfolio_id,
                SecurityMaster.ticker == ticker.upper()
            ).first()
            if not existing_holding:
                raise ValueError(f"No existing holding for {ticker} to apply split")

        # Calculate total amount
        total_amount = shares * price_per_share + fees

        # Create transaction — store shares as positive for BUY and SPLIT
        transaction = Transaction(
            portfolio_id=portfolio_id,
            security_id=security.id,
            transaction_type=transaction_type.upper(),
            transaction_date=transaction_date,
            shares=shares if transaction_type.upper() in ['BUY', 'SPLIT'] else -shares,
            price_per_share=price_per_share,
            total_amount=total_amount,
            fees=fees,
            notes=notes
        )

        self.db.add(transaction)

        # Update holdings based on transaction type
        if transaction_type.upper() in ['BUY', 'SELL', 'REINVEST', 'SPLIT']:
            self._update_holding_from_transaction(portfolio_id, security.id, transaction)

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_portfolio_transactions(
        self,
        portfolio_id: int,
        user_id: int,
        limit: Optional[int] = 100
    ) -> List[Dict[str, Any]]:
        """Get transaction history for a portfolio"""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return []

        query = self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id
        ).join(SecurityMaster).order_by(
            Transaction.transaction_date.desc()
        )

        if limit is not None:
            query = query.limit(limit)

        transactions = query.all()

        result = []
        for txn in transactions:
            result.append({
                'id': txn.id,
                'ticker': txn.security.ticker,
                'transaction_type': txn.transaction_type,
                'transaction_date': txn.transaction_date.isoformat(),
                'shares': float(txn.shares),
                'price_per_share': float(txn.price_per_share) if txn.price_per_share else None,
                'total_amount': float(txn.total_amount),
                'fees': float(txn.fees),
                'notes': txn.notes
            })

        return result

    def delete_transaction(
        self,
        portfolio_id: int,
        user_id: int,
        transaction_id: int
    ) -> bool:
        """Delete a transaction and recalculate holdings"""
        # Validate portfolio ownership
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            raise ValueError("Portfolio not found")

        # Get the transaction
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.portfolio_id == portfolio_id
        ).first()

        if not transaction:
            raise ValueError("Transaction not found")

        # Store security_id before deletion
        security_id = transaction.security_id

        # Delete the transaction
        self.db.delete(transaction)
        self.db.commit()

        # Recalculate holdings for this security from all remaining transactions
        self._recalculate_holding(portfolio_id, security_id)

        return True

    def _recalculate_holding(self, portfolio_id: int, security_id: int) -> None:
        """Recalculate holdings from all transactions for a specific security"""
        # Get all transactions for this security in chronological order
        transactions = self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.security_id == security_id
        ).order_by(Transaction.transaction_date).all()

        # Delete existing holding
        existing_holding = self.db.query(Holding).filter(
            Holding.portfolio_id == portfolio_id,
            Holding.security_id == security_id
        ).first()

        if existing_holding:
            self.db.delete(existing_holding)
            self.db.flush()

        # Recalculate from scratch
        if not transactions:
            # No transactions left, holding already deleted
            self.db.commit()
            return

        total_shares = Decimal('0')
        total_cost = Decimal('0')

        for txn in transactions:
            if txn.transaction_type in ['BUY', 'REINVEST']:
                total_shares += txn.shares
                total_cost += txn.shares * txn.price_per_share
            elif txn.transaction_type == 'SPLIT':
                # Split multiplies shares; total cost stays the same
                ratio = txn.shares  # stored as positive ratio
                total_shares = total_shares * ratio
            elif txn.transaction_type == 'SELL':
                # For sells, shares are already stored as negative
                shares_sold = abs(txn.shares)
                if total_shares > 0:
                    # Calculate average cost basis before the sale
                    avg_cost = total_cost / total_shares if total_shares > 0 else Decimal('0')
                    # Reduce shares and cost
                    total_shares -= shares_sold
                    total_cost -= shares_sold * avg_cost

        # Create new holding if there are shares left
        if total_shares > 0:
            avg_cost_basis = total_cost / total_shares if total_shares > 0 else Decimal('0')
            new_holding = Holding(
                portfolio_id=portfolio_id,
                security_id=security_id,
                shares=total_shares,
                average_cost_basis=avg_cost_basis,
                total_cost_basis=total_cost
            )
            self.db.add(new_holding)

        self.db.commit()

    # ========== Portfolio Summary ==========

    def get_portfolio_summary(self, portfolio_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive portfolio summary"""
        portfolio = self.get_portfolio(portfolio_id, user_id)
        if not portfolio:
            return None

        holdings = self.get_portfolio_holdings(portfolio_id, user_id)

        total_positions = len(holdings)
        total_cost_basis = sum(h['total_cost_basis'] or 0 for h in holdings)

        return {
            'portfolio_id': portfolio.id,
            'name': portfolio.name,
            'description': portfolio.description,
            'created_at': portfolio.created_at.isoformat(),
            'total_positions': total_positions,
            'total_cost_basis': total_cost_basis,
            'holdings': holdings
        }

    def get_all_portfolios_with_summaries(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all portfolios for user with brief summaries including current values"""
        from ..services.daily_cache_service import DailyCacheService

        # Use daily cached prices instead of making live API calls
        cache_service = DailyCacheService()
        cached_prices = cache_service.get_cached_prices()

        portfolios = self.get_user_portfolios(user_id)
        summaries = []

        for portfolio in portfolios:
            holdings = self.get_portfolio_holdings(portfolio.id, user_id)

            total_positions = len(holdings)
            total_cost_basis = 0
            total_current_value = 0

            # Calculate current values using cached prices
            for holding in holdings:
                cost_basis = holding.get('total_cost_basis') or 0
                total_cost_basis += cost_basis

                # Use cached price from daily cache
                ticker = holding['ticker']
                shares = holding['shares']
                current_price = cached_prices.get(ticker, 0)

                if current_price > 0:
                    total_current_value += current_price * shares
                else:
                    # If no cached price, use cost basis as fallback
                    total_current_value += cost_basis

            # Calculate return
            total_return = 0
            total_return_pct = 0
            if total_cost_basis > 0:
                total_return = total_current_value - total_cost_basis
                total_return_pct = (total_return / total_cost_basis) * 100

            summaries.append({
                'portfolio_id': portfolio.id,
                'name': portfolio.name,
                'description': portfolio.description,
                'total_positions': total_positions,
                'total_value': round(total_current_value, 2),
                'total_cost_basis': round(total_cost_basis, 2),
                'total_return': round(total_return, 2),
                'total_return_pct': round(total_return_pct, 2),
                'created_at': portfolio.created_at.isoformat()
            })

        return summaries

    # ========== Helper Methods ==========

    def _get_or_create_security(self, ticker: str) -> SecurityMaster:
        """Get existing security or create a new one"""
        ticker = ticker.upper()
        security = self.db.query(SecurityMaster).filter(
            SecurityMaster.ticker == ticker
        ).first()

        if not security:
            # Create new security with basic info
            security = SecurityMaster(
                ticker=ticker,
                security_type='STOCK',  # Default, can be updated later
                is_active=True
            )
            self.db.add(security)
            self.db.flush()  # Get the ID without committing

        return security

    def _update_holding_from_transaction(
        self,
        portfolio_id: int,
        security_id: int,
        transaction: Transaction
    ) -> None:
        """Update holding based on transaction"""
        holding = self.db.query(Holding).filter(
            Holding.portfolio_id == portfolio_id,
            Holding.security_id == security_id
        ).first()

        if transaction.transaction_type == 'BUY' or transaction.transaction_type == 'REINVEST':
            if holding:
                # Update existing holding with weighted average cost basis
                new_shares = holding.shares + transaction.shares
                if holding.average_cost_basis and transaction.price_per_share:
                    holding.average_cost_basis = (
                        (holding.shares * holding.average_cost_basis +
                         transaction.shares * transaction.price_per_share) / new_shares
                    )
                holding.shares = new_shares
                holding.total_cost_basis = holding.shares * holding.average_cost_basis
            else:
                # Create new holding
                holding = Holding(
                    portfolio_id=portfolio_id,
                    security_id=security_id,
                    shares=transaction.shares,
                    average_cost_basis=transaction.price_per_share,
                    total_cost_basis=transaction.shares * transaction.price_per_share
                )
                self.db.add(holding)

        elif transaction.transaction_type == 'SPLIT':
            if holding:
                ratio = transaction.shares  # stored as positive split ratio
                total_cost = holding.total_cost_basis
                holding.shares = holding.shares * ratio
                holding.average_cost_basis = total_cost / holding.shares if holding.shares > 0 else Decimal('0')
                holding.total_cost_basis = total_cost  # total investment unchanged

        elif transaction.transaction_type == 'SELL':
            if holding:
                holding.shares = holding.shares + transaction.shares  # transaction.shares is negative
                if holding.shares <= 0:
                    self.db.delete(holding)
                else:
                    holding.total_cost_basis = holding.shares * holding.average_cost_basis
