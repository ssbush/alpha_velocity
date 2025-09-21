from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

from .services.momentum_engine import MomentumEngine
from .services.portfolio_service import PortfolioService
from .models.momentum import MomentumScore
from .models.portfolio import (
    PortfolioAnalysis, CategoryInfo, CategoryAnalysis,
    Portfolio, PortfolioHolding
)

# Initialize FastAPI app
app = FastAPI(
    title="AlphaVelocity API",
    description="AI Supply Chain Momentum Scoring Engine",
    version="1.0.0"
)

# Add CORS middleware for mobile app access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
momentum_engine = MomentumEngine()
portfolio_service = PortfolioService(momentum_engine)

# Default model portfolio for demo
DEFAULT_PORTFOLIO = {
    "NVDA": 7, "AVGO": 4, "MSFT": 2, "META": 1, "NOW": 1,
    "VRT": 7, "MOD": 10, "BE": 30, "UI": 3,
    "DLR": 6, "SRVR": 58, "IRM": 10,
    "EWJ": 14, "EWT": 17,
    "SHY": 13,
    "XLI": 7,
    "MP": 16
}

@app.get("/")
async def root():
    """API health check"""
    return {"message": "AlphaVelocity API is running", "version": "1.0.0"}

@app.get("/momentum/{ticker}", response_model=MomentumScore)
async def get_momentum_score(ticker: str):
    """Get momentum score for a specific ticker"""
    try:
        result = momentum_engine.calculate_momentum_score(ticker.upper())
        return MomentumScore(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating momentum for {ticker}: {str(e)}")

@app.get("/portfolio/analysis")
async def analyze_portfolio(portfolio_data: Optional[str] = None):
    """Analyze portfolio holdings (uses default if none provided)"""
    try:
        # Use default portfolio if none provided
        portfolio = DEFAULT_PORTFOLIO

        df, total_value, avg_score = portfolio_service.analyze_portfolio(portfolio)

        # Convert DataFrame to list of holdings
        holdings = []
        for _, row in df.iterrows():
            holdings.append(PortfolioHolding(
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

        return PortfolioAnalysis(
            holdings=holdings,
            total_value=total_value,
            average_momentum_score=avg_score,
            number_of_positions=len(portfolio)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing portfolio: {str(e)}")

@app.get("/categories", response_model=List[CategoryInfo])
async def get_categories():
    """Get all portfolio categories"""
    try:
        categories = portfolio_service.get_all_categories()
        result = []
        for name, info in categories.items():
            result.append(CategoryInfo(
                name=name,
                tickers=info['tickers'],
                target_allocation=info['target_allocation'],
                benchmark=info['benchmark']
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching categories: {str(e)}")

@app.get("/categories/{category_name}/analysis", response_model=CategoryAnalysis)
async def analyze_category(category_name: str):
    """Analyze a specific portfolio category"""
    try:
        result = portfolio_service.get_category_analysis(category_name)
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])

        return CategoryAnalysis(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing category {category_name}: {str(e)}")

@app.get("/momentum/top/{limit}")
async def get_top_momentum_stocks(limit: int = 10, category: Optional[str] = None):
    """Get top momentum stocks, optionally filtered by category"""
    try:
        if limit > 50:
            limit = 50  # Reasonable limit

        result = portfolio_service.get_top_momentum_stocks(category, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top momentum stocks: {str(e)}")

@app.get("/categories/{category_name}/tickers")
async def get_category_tickers(category_name: str):
    """Get tickers for a specific category"""
    try:
        tickers = portfolio_service.get_category_tickers(category_name)
        if not tickers:
            raise HTTPException(status_code=404, detail=f"Category {category_name} not found")
        return {"category": category_name, "tickers": tickers}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching tickers for {category_name}: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)