#!/usr/bin/env python3
"""
Populate database with real market data and momentum scores
This script fetches current stock prices and calculates momentum scores
"""

import os
import sys
import asyncio
import psycopg2
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append('backend')
from models.database import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Load environment variables
load_dotenv()

class MarketDataPopulator:
    def __init__(self):
        self.db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def fetch_stock_data(self, ticker):
        """Fetch current stock data from Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="6mo")  # 6 months of data

            if hist.empty:
                print(f"❌ No data for {ticker}")
                return None

            current_price = hist['Close'].iloc[-1]

            # Calculate simple momentum metrics
            if len(hist) >= 20:
                ma_20 = hist['Close'].rolling(20).mean().iloc[-1]
                price_momentum = ((current_price - ma_20) / ma_20) * 100
            else:
                price_momentum = 0

            # Get 3-month return
            if len(hist) >= 60:
                three_month_return = ((current_price - hist['Close'].iloc[-60]) / hist['Close'].iloc[-60]) * 100
            else:
                three_month_return = 0

            return {
                'ticker': ticker,
                'current_price': float(current_price),
                'volume': int(hist['Volume'].iloc[-1]),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'price_momentum': price_momentum,
                'three_month_return': three_month_return,
                'history': hist.tail(30)  # Last 30 days
            }
        except Exception as e:
            print(f"❌ Error fetching data for {ticker}: {e}")
            return None

    def calculate_momentum_score(self, data):
        """Calculate composite momentum score"""
        if not data:
            return 50.0  # Default neutral score

        # Simple momentum calculation
        price_score = min(max((data['price_momentum'] + 50), 0), 100)
        return_score = min(max((data['three_month_return'] * 2 + 50), 0), 100)

        # Weighted composite score
        composite_score = (price_score * 0.6) + (return_score * 0.4)
        return round(composite_score, 1)

    def populate_security_details(self, session):
        """Update security master with detailed information"""
        print("📊 Updating security master with market data...")

        securities = session.query(SecurityMaster).all()

        for security in securities:
            print(f"🔍 Fetching data for {security.ticker}...")
            data = self.fetch_stock_data(security.ticker)

            if data:
                # Update security master
                security.sector = data['sector'][:100] if data['sector'] else security.sector
                security.industry = data['industry'][:100] if data['industry'] else security.industry
                security.updated_at = datetime.utcnow()

                print(f"✅ Updated {security.ticker}: {data['sector']}")
            else:
                print(f"⚠️  Skipped {security.ticker}")

        session.commit()

    def populate_price_history(self, session):
        """Populate price history table"""
        print("💰 Populating price history...")

        securities = session.query(SecurityMaster).all()

        for security in securities:
            print(f"📈 Adding price history for {security.ticker}...")
            data = self.fetch_stock_data(security.ticker)

            if data and 'history' in data:
                # Add price history records
                for date, row in data['history'].iterrows():
                    price_record = PriceHistory(
                        security_id=security.id,
                        price_date=date.date(),
                        open_price=float(row['Open']),
                        high_price=float(row['High']),
                        low_price=float(row['Low']),
                        close_price=float(row['Close']),
                        volume=int(row['Volume']),
                        created_at=datetime.utcnow()
                    )
                    session.add(price_record)

                print(f"✅ Added {len(data['history'])} price records for {security.ticker}")

        session.commit()

    def populate_momentum_scores(self, session):
        """Populate momentum scores table"""
        print("🚀 Calculating momentum scores...")

        securities = session.query(SecurityMaster).all()

        for security in securities:
            print(f"⚡ Calculating momentum for {security.ticker}...")
            data = self.fetch_stock_data(security.ticker)

            momentum_score = self.calculate_momentum_score(data)

            # Create momentum score record
            score_record = MomentumScore(
                security_id=security.id,
                score_date=datetime.utcnow().date(),
                composite_score=float(momentum_score),
                price_momentum=float(data['price_momentum']) if data else 0.0,
                technical_momentum=float(momentum_score * 0.8),  # Simplified
                fundamental_momentum=float(momentum_score * 0.9),  # Simplified
                relative_momentum=float(momentum_score * 0.7),  # Simplified
                created_at=datetime.utcnow()
            )
            session.add(score_record)

            print(f"✅ {security.ticker}: Momentum Score = {momentum_score}")

        session.commit()

    def update_holdings_with_current_data(self, session):
        """Update holdings with current market values"""
        print("💼 Updating portfolio holdings with current values...")

        holdings = session.query(Holdings).all()

        for holding in holdings:
            security = holding.security
            print(f"💵 Updating holding: {security.ticker}")

            data = self.fetch_stock_data(security.ticker)
            if data:
                # Update holding with current market value
                current_value = holding.quantity * data['current_price']

                # Calculate cost basis if not set
                if not holding.cost_basis:
                    holding.cost_basis = data['current_price'] * 0.9  # Assume 10% gain

                holding.updated_at = datetime.utcnow()

                print(f"✅ {security.ticker}: {holding.quantity} shares @ ${data['current_price']:.2f} = ${current_value:,.2f}")

        session.commit()

    def run_population(self):
        """Run the complete market data population"""
        print("🏃‍♂️ Starting market data population...\n")

        session = self.SessionLocal()

        try:
            # Step 1: Update security master details
            self.populate_security_details(session)
            print()

            # Step 2: Populate price history
            self.populate_price_history(session)
            print()

            # Step 3: Calculate and store momentum scores
            self.populate_momentum_scores(session)
            print()

            # Step 4: Update holdings with current values
            self.update_holdings_with_current_data(session)
            print()

            print("🎉 Market data population completed successfully!")

            # Show summary
            security_count = session.query(SecurityMaster).count()
            price_count = session.query(PriceHistory).count()
            momentum_count = session.query(MomentumScore).count()
            holdings_count = session.query(Holdings).count()

            print(f"\n📊 Summary:")
            print(f"  Securities: {security_count}")
            print(f"  Price Records: {price_count}")
            print(f"  Momentum Scores: {momentum_count}")
            print(f"  Holdings: {holdings_count}")

        except Exception as e:
            print(f"❌ Error during population: {e}")
            session.rollback()
        finally:
            session.close()

def main():
    """Main function"""
    print("🔮 AlphaVelocity Market Data Populator")
    print("=" * 50)

    populator = MarketDataPopulator()
    populator.run_population()

if __name__ == "__main__":
    main()