"""
Simple Database Service for AlphaVelocity
Works with current FastAPI import structure
"""

import logging
import os
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

def get_db_service():
    """Get database service with proper imports"""
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

        from .database.config import db_config
        from .models.database import User, Portfolio, SecurityMaster, Category, Holding, Transaction

        class SimpleDatabaseService:
            """Simple database service for API endpoints"""

            def __init__(self):
                self.db_config = db_config

            def test_connection(self):
                """Test database connection"""
                return self.db_config.test_connection()

            def get_portfolios(self, user_id: int = 1):
                """Get all portfolios for a user"""
                try:
                    with self.db_config.get_session_context() as session:
                        portfolios = session.query(Portfolio).filter_by(user_id=user_id).all()
                        return [
                            {
                                "id": p.id,
                                "name": p.name,
                                "description": p.description,
                                "created_at": p.created_at.isoformat(),
                                "is_active": p.is_active
                            }
                            for p in portfolios
                        ]
                except Exception as e:
                    raise Exception(f"Error getting portfolios: {e}")

            def get_portfolio_holdings(self, portfolio_id: int):
                """Get holdings for a portfolio"""
                try:
                    with self.db_config.get_session_context() as session:
                        holdings = session.query(Holding, SecurityMaster).join(
                            SecurityMaster, Holding.security_id == SecurityMaster.id
                        ).filter(Holding.portfolio_id == portfolio_id).all()

                        return [
                            {
                                "id": h.Holding.id,
                                "ticker": h.SecurityMaster.ticker,
                                "company_name": h.SecurityMaster.company_name,
                                "shares": float(h.Holding.shares),
                                "average_cost_basis": float(h.Holding.average_cost_basis) if h.Holding.average_cost_basis else None,
                                "total_cost_basis": float(h.Holding.total_cost_basis) if h.Holding.total_cost_basis else None,
                                "security_type": h.SecurityMaster.security_type
                            }
                            for h in holdings
                        ]
                except Exception as e:
                    raise Exception(f"Error getting holdings: {e}")

            def get_categories_analysis(self, portfolio_id: int):
                """Get category analysis for a portfolio"""
                try:
                    with self.db_config.get_session_context() as session:
                        # Get holdings with categories
                        holdings = session.query(Holding, SecurityMaster, Category).join(
                            SecurityMaster, Holding.security_id == SecurityMaster.id
                        ).outerjoin(
                            Category, Holding.category_id == Category.id
                        ).filter(Holding.portfolio_id == portfolio_id).all()

                        # Group by category
                        categories = {}
                        for h in holdings:
                            cat_name = h.Category.name if h.Category else "Uncategorized"
                            if cat_name not in categories:
                                categories[cat_name] = {
                                    "name": cat_name,
                                    "holdings": [],
                                    "total_shares": 0,
                                    "target_allocation": float(h.Category.target_allocation_pct) if h.Category else 0
                                }

                            categories[cat_name]["holdings"].append({
                                "ticker": h.SecurityMaster.ticker,
                                "shares": float(h.Holding.shares)
                            })
                            categories[cat_name]["total_shares"] += float(h.Holding.shares)

                        return list(categories.values())
                except Exception as e:
                    raise Exception(f"Error getting category analysis: {e}")

            def add_transaction(self, portfolio_id: int, transaction_data: dict):
                """Add a new transaction"""
                try:
                    with self.db_config.get_session_context() as session:
                        # Get or create security
                        ticker = transaction_data.get("ticker")
                        security = session.query(SecurityMaster).filter_by(ticker=ticker).first()

                        if not security:
                            security = SecurityMaster(
                                ticker=ticker,
                                company_name=f"{ticker} Inc.",
                                security_type="STOCK",
                                exchange="NASDAQ"
                            )
                            session.add(security)
                            session.flush()

                        # Calculate total amount
                        shares = Decimal(str(transaction_data.get("shares", 0)))
                        price_per_share = Decimal(str(transaction_data.get("price_per_share", 0)))
                        fees = Decimal(str(transaction_data.get("fees", 0)))
                        total_amount = (shares * price_per_share) + fees

                        # Create transaction
                        transaction = Transaction(
                            portfolio_id=portfolio_id,
                            security_id=security.id,
                            transaction_type=transaction_data.get("transaction_type", "BUY"),
                            transaction_date=datetime.strptime(transaction_data.get("transaction_date", datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
                            shares=shares,
                            price_per_share=price_per_share,
                            total_amount=total_amount,
                            fees=fees
                        )
                        session.add(transaction)
                        session.commit()

                        return {
                            "id": transaction.id,
                            "ticker": ticker,
                            "transaction_type": transaction.transaction_type,
                            "shares": float(transaction.shares),
                            "price_per_share": float(transaction.price_per_share),
                            "total_amount": float(transaction.total_amount)
                        }
                except Exception as e:
                    raise Exception(f"Error adding transaction: {e}")

            def get_portfolio_by_categories(self, portfolio_id: int):
                """Get portfolio holdings organized by categories"""
                try:
                    with self.db_config.get_session_context() as session:
                        # Query holdings with categories
                        holdings_query = session.query(
                            Holding,
                            SecurityMaster,
                            Category
                        ).join(
                            SecurityMaster, Holding.security_id == SecurityMaster.id
                        ).outerjoin(
                            Category, Holding.category_id == Category.id
                        ).filter(Holding.portfolio_id == portfolio_id)

                        holdings_data = holdings_query.all()

                        # Organize by categories
                        categories_dict = {}

                        for holding, security, category in holdings_data:
                            cat_name = category.name if category else "Uncategorized"

                            if cat_name not in categories_dict:
                                categories_dict[cat_name] = {
                                    "category_name": cat_name,
                                    "target_allocation_pct": float(category.target_allocation_pct) if category and category.target_allocation_pct else 0,
                                    "benchmark_ticker": category.benchmark_ticker if category else None,
                                    "description": category.description if category else None,
                                    "holdings": [],
                                    "total_value": 0,
                                    "total_cost_basis": 0,
                                    "position_count": 0
                                }

                            # Calculate current value using real-time prices
                            cost_basis = float(holding.total_cost_basis) if holding.total_cost_basis else 0
                            current_value = cost_basis  # Default fallback

                            # Fetch current market price
                            try:
                                from .services.price_service import get_price_service
                                current_price = get_price_service().get_current_price(security.ticker)
                                if current_price is not None:
                                    current_value = float(holding.shares) * current_price
                                else:
                                    logger.warning("No price data available for %s", security.ticker)
                            except Exception as e:
                                logger.error("Error fetching price for %s: %s", security.ticker, e)
                                # Keep fallback value (cost_basis)

                            holding_data = {
                                "id": holding.id,
                                "ticker": security.ticker,
                                "company_name": security.company_name,
                                "sector": security.sector,
                                "shares": float(holding.shares),
                                "average_cost_basis": float(holding.average_cost_basis) if holding.average_cost_basis else 0,
                                "total_cost_basis": cost_basis,
                                "current_value": current_value,
                                "security_type": security.security_type
                            }

                            categories_dict[cat_name]["holdings"].append(holding_data)
                            categories_dict[cat_name]["total_value"] += current_value
                            categories_dict[cat_name]["total_cost_basis"] += cost_basis
                            categories_dict[cat_name]["position_count"] += 1

                        # Convert to list and sort by target allocation
                        categories_list = list(categories_dict.values())
                        categories_list.sort(key=lambda x: x["target_allocation_pct"], reverse=True)

                        return {
                            "portfolio_id": portfolio_id,
                            "categories": categories_list,
                            "total_categories": len(categories_list),
                            "total_positions": sum(cat["position_count"] for cat in categories_list),
                            "total_portfolio_value": sum(cat["total_value"] for cat in categories_list)
                        }

                except Exception as e:
                    raise Exception(f"Error getting portfolio by categories: {e}")

            def get_transactions(self, portfolio_id: int, limit: int = 50):
                """Get transaction history"""
                try:
                    with self.db_config.get_session_context() as session:
                        transactions = session.query(Transaction, SecurityMaster).join(
                            SecurityMaster, Transaction.security_id == SecurityMaster.id
                        ).filter(
                            Transaction.portfolio_id == portfolio_id
                        ).order_by(Transaction.created_at.desc()).limit(limit).all()

                        return [
                            {
                                "id": t.Transaction.id,
                                "ticker": t.SecurityMaster.ticker,
                                "transaction_type": t.Transaction.transaction_type,
                                "transaction_date": t.Transaction.transaction_date.isoformat(),
                                "shares": float(t.Transaction.shares),
                                "price_per_share": float(t.Transaction.price_per_share) if t.Transaction.price_per_share else None,
                                "total_amount": float(t.Transaction.total_amount),
                                "fees": float(t.Transaction.fees) if t.Transaction.fees else 0,
                                "created_at": t.Transaction.created_at.isoformat()
                            }
                            for t in transactions
                        ]
                except Exception as e:
                    raise Exception(f"Error getting transactions: {e}")

        return SimpleDatabaseService()

    except Exception as e:
        logger.error("Database service initialization failed: %s", e)
        return None

# Global database service instance
_db_service = None

def get_database_service():
    """Get or create database service instance"""
    global _db_service
    if _db_service is None:
        _db_service = get_db_service()
    return _db_service