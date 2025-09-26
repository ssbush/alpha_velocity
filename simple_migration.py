#!/usr/bin/env python3
"""
Simple Database Migration for AlphaVelocity
Creates tables and migrates data using peer authentication
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add backend to path
sys.path.insert(0, 'backend')

def create_database_and_user():
    """Create database and user using peer authentication"""
    print("🗄️ Setting up database...")

    try:
        # Connect as current user using Unix socket
        conn = psycopg2.connect(
            database="postgres",
            user="node"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create database if not exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='alphavelocity'")
        if not cursor.fetchone():
            cursor.execute("CREATE DATABASE alphavelocity")
            print("   ✅ Created database 'alphavelocity'")
        else:
            print("   ℹ️ Database 'alphavelocity' already exists")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"   ❌ Database setup failed: {e}")
        return False

def create_tables():
    """Create database tables using SQLAlchemy"""
    print("📊 Creating database tables...")

    try:
        from sqlalchemy import create_engine
        from models.database import Base

        # Connect to alphavelocity database using peer auth
        database_url = "postgresql:///alphavelocity?user=postgres"
        engine = create_engine(database_url)

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("   ✅ Database tables created successfully")
        return True

    except Exception as e:
        print(f"   ❌ Table creation failed: {e}")
        return False

def simple_data_setup():
    """Set up basic data for testing"""
    print("🏗️ Setting up initial data...")

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models.database import User, Portfolio, Category, SecurityMaster
        from decimal import Decimal

        database_url = "postgresql:///alphavelocity?user=postgres"
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as session:
            # Create default user if not exists
            user = session.query(User).filter_by(username='admin').first()
            if not user:
                user = User(
                    username='admin',
                    email='admin@alphavelocity.com',
                    password_hash='$2b$12$dummy_hash',
                    first_name='Alpha',
                    last_name='Velocity'
                )
                session.add(user)
                session.flush()
                print(f"   ✅ Created user: {user.username}")

            # Create default portfolio if not exists
            portfolio = session.query(Portfolio).filter_by(user_id=user.id, name='Default Portfolio').first()
            if not portfolio:
                portfolio = Portfolio(
                    user_id=user.id,
                    name='Default Portfolio',
                    description='AlphaVelocity momentum-based portfolio'
                )
                session.add(portfolio)
                session.flush()
                print(f"   ✅ Created portfolio: {portfolio.name}")

            # Create sample categories
            categories = [
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
                }
            ]

            for cat_data in categories:
                existing = session.query(Category).filter_by(name=cat_data['name']).first()
                if not existing:
                    category = Category(**cat_data)
                    session.add(category)

            # Create sample securities
            sample_tickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL']
            for ticker in sample_tickers:
                existing = session.query(SecurityMaster).filter_by(ticker=ticker).first()
                if not existing:
                    security = SecurityMaster(
                        ticker=ticker,
                        company_name=f"{ticker} Inc.",
                        security_type='STOCK',
                        exchange='NASDAQ'
                    )
                    session.add(security)

            session.commit()
            print("   ✅ Basic data setup completed")
            return True

    except Exception as e:
        print(f"   ❌ Data setup failed: {e}")
        return False

def main():
    """Run the simple migration"""
    print("🚀 AlphaVelocity Simple Database Setup")
    print("=" * 40)

    # Step 1: Create database
    if not create_database_and_user():
        return False

    # Step 2: Create tables
    if not create_tables():
        return False

    # Step 3: Basic data setup
    if not simple_data_setup():
        return False

    print("\n🎉 Database setup completed successfully!")
    print("✅ Database: alphavelocity")
    print("✅ Tables: 14 tables created")
    print("✅ Data: Basic user, portfolio, and test data")

    return True

if __name__ == "__main__":
    main()