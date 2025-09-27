#!/usr/bin/env python3
"""
Simple Database Migration for AlphaVelocity
"""

import os
import sys
from dotenv import load_dotenv
from decimal import Decimal
from datetime import datetime

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, 'backend')

def run_migration():
    """Run simple database migration"""
    print("🚀 Starting AlphaVelocity database migration...")

    try:
        from database.config import db_config
        from models.database import User, Portfolio, SecurityMaster, Category, Holding

        # Test connection
        if not db_config.test_connection():
            print("❌ Database connection failed")
            return False

        # Create tables
        db_config.create_all_tables()

        with db_config.get_session_context() as session:
            # Create default user
            user = session.query(User).filter_by(username='admin').first()
            if not user:
                user = User(
                    username='admin',
                    email='admin@alphavelocity.com',
                    password_hash='$2b$12$dummy_hash_for_development',
                    first_name='Alpha',
                    last_name='Velocity'
                )
                session.add(user)
                session.flush()
                print(f"✅ Created user: {user.username}")

            # Create default portfolio
            portfolio = session.query(Portfolio).filter_by(user_id=user.id, name='Default Portfolio').first()
            if not portfolio:
                portfolio = Portfolio(
                    user_id=user.id,
                    name='Default Portfolio',
                    description='AlphaVelocity momentum-based AI supply chain portfolio'
                )
                session.add(portfolio)
                session.flush()
                print(f"✅ Created portfolio: {portfolio.name}")

            # Create categories
            categories_data = [
                {
                    'name': 'Large-Cap Anchors',
                    'description': 'Large-cap technology leaders',
                    'target_allocation_pct': Decimal('20.00'),
                    'benchmark_ticker': 'QQQ'
                },
                {
                    'name': 'Small-Cap Specialists',
                    'description': 'Small-cap technology companies',
                    'target_allocation_pct': Decimal('15.00'),
                    'benchmark_ticker': 'XLK'
                },
                {
                    'name': 'Data Center Infrastructure',
                    'description': 'Infrastructure supporting AI and cloud computing',
                    'target_allocation_pct': Decimal('15.00'),
                    'benchmark_ticker': 'VNQ'
                }
            ]

            for cat_data in categories_data:
                existing = session.query(Category).filter_by(name=cat_data['name']).first()
                if not existing:
                    category = Category(**cat_data)
                    session.add(category)

            # Create sample securities from DEFAULT_PORTFOLIO
            DEFAULT_PORTFOLIO = {
                "NVDA": 7, "AVGO": 4, "MSFT": 2, "META": 1, "NOW": 1, "AAPL": 4, "GOOGL": 4,
                "VRT": 7, "MOD": 10, "BE": 30, "UI": 3,
                "DLR": 6, "SRVR": 58, "IRM": 10, "CCI": 10,
                "EWJ": 14, "EWT": 17, "SHY": 13, "XLI": 7, "MP": 16
            }

            securities_created = 0
            holdings_created = 0

            for ticker, shares in DEFAULT_PORTFOLIO.items():
                # Create security if not exists
                security = session.query(SecurityMaster).filter_by(ticker=ticker).first()
                if not security:
                    security = SecurityMaster(
                        ticker=ticker,
                        company_name=f"{ticker} Inc.",
                        security_type='STOCK',
                        exchange='NASDAQ'
                    )
                    session.add(security)
                    session.flush()
                    securities_created += 1

                # Create holding if not exists
                existing_holding = session.query(Holding).filter_by(
                    portfolio_id=portfolio.id,
                    security_id=security.id
                ).first()

                if not existing_holding:
                    holding = Holding(
                        portfolio_id=portfolio.id,
                        security_id=security.id,
                        shares=Decimal(str(shares))
                    )
                    session.add(holding)
                    holdings_created += 1

            session.commit()
            print(f"✅ Created {securities_created} securities and {holdings_created} holdings")

        print("🎉 Database migration completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_migration()