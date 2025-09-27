#!/usr/bin/env python3
"""
Set up portfolio categories and assign holdings to appropriate categories
Based on the AlphaVelocity model portfolio structure
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append('backend')
from models.database import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

load_dotenv()

class CategoryManager:
    def __init__(self):
        self.db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_categories(self, session):
        """Create the full AlphaVelocity category structure"""
        print("📂 Creating portfolio categories...")

        categories = [
            {
                'name': 'Large-Cap Anchors',
                'description': 'Core large-cap technology holdings for stability',
                'target_allocation_pct': 20.00,
                'benchmark_ticker': 'QQQ'
            },
            {
                'name': 'Small-Cap Specialists',
                'description': 'High-growth small-cap technology companies',
                'target_allocation_pct': 15.00,
                'benchmark_ticker': 'XLK'
            },
            {
                'name': 'Data Center Infrastructure',
                'description': 'Real estate and infrastructure supporting AI/cloud',
                'target_allocation_pct': 15.00,
                'benchmark_ticker': 'VNQ'
            },
            {
                'name': 'International Tech/Momentum',
                'description': 'International technology and momentum exposure',
                'target_allocation_pct': 12.00,
                'benchmark_ticker': 'VEA'
            },
            {
                'name': 'Tactical Fixed Income',
                'description': 'Short-term tactical fixed income positions',
                'target_allocation_pct': 8.00,
                'benchmark_ticker': 'AGG'
            },
            {
                'name': 'Sector Momentum Rotation',
                'description': 'Rotating sector ETFs based on momentum',
                'target_allocation_pct': 10.00,
                'benchmark_ticker': 'SPY'
            },
            {
                'name': 'Critical Metals & Mining',
                'description': 'Metals and mining essential for AI infrastructure',
                'target_allocation_pct': 7.00,
                'benchmark_ticker': 'XLB'
            },
            {
                'name': 'Specialized Materials ETFs',
                'description': 'Specialized materials and commodity ETFs',
                'target_allocation_pct': 5.00,
                'benchmark_ticker': 'XLB'
            }
        ]

        # Clear existing categories except the first 3 (to preserve any existing data)
        existing_categories = session.query(Category).filter(Category.id > 3).all()
        for cat in existing_categories:
            session.delete(cat)

        # Add new categories
        for cat_data in categories:
            # Check if category already exists by name
            existing = session.query(Category).filter(Category.name == cat_data['name']).first()
            if not existing:
                category = Category(
                    name=cat_data['name'],
                    description=cat_data['description'],
                    target_allocation_pct=cat_data['target_allocation_pct'],
                    benchmark_ticker=cat_data['benchmark_ticker'],
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                session.add(category)
                print(f"✅ Created category: {cat_data['name']} ({cat_data['target_allocation_pct']}%)")
            else:
                # Update existing category
                existing.description = cat_data['description']
                existing.target_allocation_pct = cat_data['target_allocation_pct']
                existing.benchmark_ticker = cat_data['benchmark_ticker']
                print(f"📝 Updated category: {cat_data['name']}")

        session.commit()

    def assign_holdings_to_categories(self, session):
        """Assign holdings to appropriate categories based on ticker analysis"""
        print("\n🏷️  Assigning holdings to categories...")

        # Define ticker to category mapping based on AlphaVelocity model
        ticker_to_category = {
            # Large-Cap Anchors (20%)
            'NVDA': 'Large-Cap Anchors',
            'MSFT': 'Large-Cap Anchors',
            'AAPL': 'Large-Cap Anchors',
            'GOOGL': 'Large-Cap Anchors',
            'META': 'Large-Cap Anchors',

            # Small-Cap Specialists (15%)
            'AVGO': 'Small-Cap Specialists',
            'NOW': 'Small-Cap Specialists',
            'VRT': 'Small-Cap Specialists',
            'MOD': 'Small-Cap Specialists',
            'UI': 'Small-Cap Specialists',

            # Data Center Infrastructure (15%)
            'DLR': 'Data Center Infrastructure',
            'IRM': 'Data Center Infrastructure',
            'CCI': 'Data Center Infrastructure',
            'SRVR': 'Data Center Infrastructure',

            # International Tech/Momentum (12%)
            'EWJ': 'International Tech/Momentum',
            'EWT': 'International Tech/Momentum',

            # Tactical Fixed Income (8%)
            'SHY': 'Tactical Fixed Income',

            # Sector Momentum Rotation (10%)
            'XLI': 'Sector Momentum Rotation',

            # Critical Metals & Mining (7%)
            'MP': 'Critical Metals & Mining',

            # Specialized Materials ETFs (5%)
            'BE': 'Specialized Materials ETFs'
        }

        # Get all categories
        categories = {cat.name: cat for cat in session.query(Category).all()}

        # Assign each holding to a category
        holdings = session.query(Holding).all()

        for holding in holdings:
            ticker = holding.security.ticker
            category_name = ticker_to_category.get(ticker)

            if category_name and category_name in categories:
                holding.category_id = categories[category_name].id
                print(f"✅ {ticker} → {category_name}")
            else:
                print(f"⚠️  {ticker} → No category assigned")

        session.commit()

    def create_category_summary(self, session):
        """Create a summary of categories and their holdings"""
        print("\n📊 Portfolio Category Summary:")
        print("=" * 60)

        # Query categories with their holdings
        categories = session.query(Category).order_by(Category.target_allocation_pct.desc()).all()

        total_value = 0
        for category in categories:
            holdings = session.query(Holding).filter(Holding.category_id == category.id).all()

            category_value = 0
            holding_count = len(holdings)

            for holding in holdings:
                if holding.total_cost_basis:
                    # Estimate current value as 10% more than cost basis
                    estimated_value = float(holding.total_cost_basis) * 1.1
                    category_value += estimated_value

            total_value += category_value

            print(f"\n{category.name} ({category.target_allocation_pct}%)")
            print(f"  Holdings: {holding_count}")
            print(f"  Estimated Value: ${category_value:,.2f}")
            print(f"  Benchmark: {category.benchmark_ticker}")

            if holdings:
                print("  Tickers:", ", ".join([h.security.ticker for h in holdings]))

        print(f"\n{'='*60}")
        print(f"Total Portfolio Value: ${total_value:,.2f}")

    def run_setup(self):
        """Run the complete category setup"""
        print("🚀 Setting up Portfolio Categories")
        print("=" * 50)

        session = self.SessionLocal()

        try:
            # Step 1: Create categories
            self.create_categories(session)

            # Step 2: Assign holdings to categories
            self.assign_holdings_to_categories(session)

            # Step 3: Show summary
            self.create_category_summary(session)

            print("\n🎉 Portfolio categories setup completed!")

        except Exception as e:
            print(f"❌ Error during category setup: {e}")
            session.rollback()
        finally:
            session.close()

def main():
    """Main function"""
    manager = CategoryManager()
    manager.run_setup()

if __name__ == "__main__":
    main()