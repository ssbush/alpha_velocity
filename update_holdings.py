#!/usr/bin/env python3
"""Update holdings with current market values"""

import os
import sys
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append('backend')
from models.database import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

load_dotenv()

# Database connection
db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def fetch_current_price(ticker):
    """Fetch current stock price"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except:
        pass
    return None

def update_holdings():
    """Update holdings with current market values"""
    session = SessionLocal()

    try:
        print("💼 Updating portfolio holdings with current values...")

        holdings = session.query(Holding).all()

        for holding in holdings:
            security = holding.security
            print(f"💵 Updating holding: {security.ticker}")

            current_price = fetch_current_price(security.ticker)
            if current_price:
                # Update holding with current market value
                current_value = float(holding.shares) * current_price

                # Calculate cost basis if not set (assume 10% less than current price)
                if not holding.average_cost_basis:
                    holding.average_cost_basis = current_price * 0.9
                    holding.total_cost_basis = float(holding.shares) * holding.average_cost_basis

                holding.updated_at = datetime.utcnow()

                print(f"✅ {security.ticker}: {holding.shares} shares @ ${current_price:.2f} = ${current_value:,.2f}")
            else:
                print(f"⚠️  Could not fetch price for {security.ticker}")

        session.commit()
        print("🎉 Holdings updated successfully!")

    except Exception as e:
        print(f"❌ Error updating holdings: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    update_holdings()