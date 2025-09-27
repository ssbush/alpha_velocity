#!/usr/bin/env python3
"""
Database Demo Script for AlphaVelocity

Demonstrates the database functionality (requires PostgreSQL)
"""

import requests
import json
import time
from datetime import date, datetime

# API base URL
BASE_URL = "http://localhost:8000"

def check_database_status():
    """Check if database is available and connected"""
    print("🔍 Checking database status...")
    response = requests.get(f"{BASE_URL}/database/status")
    status = response.json()

    print(f"   Available: {status.get('available', False)}")
    print(f"   Connected: {status.get('connected', False)}")
    print(f"   Message: {status.get('message', 'Unknown')}")

    return status.get('available', False) and status.get('connected', False)

def run_migration():
    """Run database migration"""
    print("\n📦 Running database migration...")
    try:
        response = requests.post(f"{BASE_URL}/database/migrate")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ {result.get('message', 'Migration completed')}")
            return True
        else:
            print(f"   ❌ Migration failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def get_user_portfolios(user_id=1):
    """Get portfolios for a user"""
    print(f"\n👤 Getting portfolios for user {user_id}...")
    try:
        response = requests.get(f"{BASE_URL}/database/portfolios?user_id={user_id}")
        if response.status_code == 200:
            data = response.json()
            portfolios = data.get('portfolios', [])
            print(f"   ✅ Found {len(portfolios)} portfolios")
            for portfolio in portfolios:
                print(f"      - {portfolio['name']} (ID: {portfolio['id']})")
            return portfolios
        else:
            print(f"   ❌ Error: {response.text}")
            return []
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

def get_portfolio_holdings(portfolio_id=1):
    """Get holdings for a portfolio"""
    print(f"\n💼 Getting holdings for portfolio {portfolio_id}...")
    try:
        response = requests.get(f"{BASE_URL}/database/portfolio/{portfolio_id}/holdings")
        if response.status_code == 200:
            data = response.json()
            holdings = data.get('holdings', [])
            total_value = data.get('total_value', 0)

            print(f"   ✅ Portfolio value: ${total_value:,.2f}")
            print(f"   ✅ Found {len(holdings)} holdings:")

            for holding in holdings[:5]:  # Show first 5
                print(f"      - {holding['ticker']}: {holding['shares']} shares @ ${holding['current_price']:.2f} = ${holding['market_value']:.2f}")

            if len(holdings) > 5:
                print(f"      ... and {len(holdings) - 5} more")

            return holdings
        else:
            print(f"   ❌ Error: {response.text}")
            return []
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

def add_sample_transaction(portfolio_id=1):
    """Add a sample transaction"""
    print(f"\n💰 Adding sample transaction to portfolio {portfolio_id}...")

    transaction_data = {
        "ticker": "AAPL",
        "transaction_type": "BUY",
        "shares": 5,
        "price_per_share": 150.00,
        "fees": 0.00,
        "notes": "Demo purchase from database setup"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/database/portfolio/{portfolio_id}/transaction",
            json=transaction_data
        )

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Transaction added:")
            print(f"      - {result['ticker']}: {result['transaction_type']} {result['shares']} shares")
            print(f"      - Total: ${result['total_amount']:.2f}")
            return result
        else:
            print(f"   ❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def get_transaction_history(portfolio_id=1):
    """Get transaction history"""
    print(f"\n📊 Getting transaction history for portfolio {portfolio_id}...")
    try:
        response = requests.get(f"{BASE_URL}/database/portfolio/{portfolio_id}/transactions?limit=10")
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('transactions', [])

            print(f"   ✅ Found {len(transactions)} recent transactions:")
            for txn in transactions[:3]:  # Show first 3
                print(f"      - {txn['transaction_date']}: {txn['transaction_type']} {txn['shares']} {txn['ticker']} @ ${txn.get('price_per_share', 0):.2f}")

            return transactions
        else:
            print(f"   ❌ Error: {response.text}")
            return []
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

def record_performance_snapshot(portfolio_id=1):
    """Record a performance snapshot"""
    print(f"\n📈 Recording performance snapshot for portfolio {portfolio_id}...")
    try:
        response = requests.post(f"{BASE_URL}/database/portfolio/{portfolio_id}/snapshot")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Snapshot recorded:")
            print(f"      - Total value: ${result.get('total_value', 0):,.2f}")
            print(f"      - Momentum score: {result.get('average_momentum_score', 0):.1f}")
            print(f"      - Positions: {result.get('number_of_positions', 0)}")
            return result
        else:
            print(f"   ❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def get_category_analysis(portfolio_id=1):
    """Get category analysis"""
    print(f"\n📊 Getting category analysis for portfolio {portfolio_id}...")
    try:
        response = requests.get(f"{BASE_URL}/database/portfolio/{portfolio_id}/categories")
        if response.status_code == 200:
            analysis = response.json()
            total_value = analysis.get('total_portfolio_value', 0)
            categories = analysis.get('categories', {})

            print(f"   ✅ Portfolio value: ${total_value:,.2f}")
            print(f"   ✅ Category allocation analysis:")

            for category, data in list(categories.items())[:3]:  # Show first 3
                target = data.get('target_allocation_pct', 0)
                actual = data.get('actual_allocation_pct', 0)
                diff = data.get('allocation_difference', 0)

                print(f"      - {category}:")
                print(f"        Target: {target:.1f}% | Actual: {actual:.1f}% | Diff: {diff:+.1f}%")

            return analysis
        else:
            print(f"   ❌ Error: {response.text}")
            return {}
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {}

def main():
    """Run the database demo"""
    print("🚀 AlphaVelocity Database Demo")
    print("=" * 50)

    # Check database status
    if not check_database_status():
        print("\n❌ Database not available. Please:")
        print("   1. Install PostgreSQL")
        print("   2. Install Python dependencies: pip install sqlalchemy psycopg2-binary")
        print("   3. Run: python scripts/setup_database.py")
        return

    print("\n✅ Database is available! Running demo...")

    # Run migration
    if not run_migration():
        print("❌ Migration failed. Cannot continue demo.")
        return

    # Demo portfolio operations
    portfolios = get_user_portfolios()
    if not portfolios:
        print("❌ No portfolios found. Migration may have failed.")
        return

    portfolio_id = portfolios[0]['id']

    # Get current holdings
    holdings = get_portfolio_holdings(portfolio_id)

    # Add a sample transaction
    add_sample_transaction(portfolio_id)

    # Get transaction history
    get_transaction_history(portfolio_id)

    # Record performance snapshot
    record_performance_snapshot(portfolio_id)

    # Get category analysis
    get_category_analysis(portfolio_id)

    print("\n🎉 Database demo completed successfully!")
    print("\nThe database system includes:")
    print("✅ Multi-user portfolio management")
    print("✅ Transaction tracking with cost basis")
    print("✅ Performance analytics and reporting")
    print("✅ Category allocation analysis")
    print("✅ Historical data migration")
    print("✅ RESTful API endpoints")

if __name__ == "__main__":
    main()