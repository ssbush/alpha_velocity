# AlphaVelocity

AI Supply Chain Momentum Scoring Engine - A systematic approach to momentum-based stock analysis and portfolio management.

## Overview

AlphaVelocity generates comprehensive momentum scores for stocks using multiple factors:
- **Price Momentum (40%)**: Multi-timeframe returns and moving average signals
- **Technical Momentum (25%)**: RSI, volume confirmation, rate of change
- **Fundamental Momentum (25%)**: P/E ratios, growth metrics, analyst ratings
- **Relative Momentum (10%)**: Performance vs. market benchmarks

## Quick Start

### API Development

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Run the API server**:
```bash
python -m backend.main
```

3. **Access the API**:
- API docs: http://localhost:8000/docs
- Portfolio analysis: http://localhost:8000/portfolio/analysis
- Momentum score: http://localhost:8000/momentum/NVDA

### API Endpoints

#### Core Endpoints
- `GET /` - Health check
- `GET /momentum/{ticker}` - Get momentum score for a ticker
- `GET /portfolio/analysis` - Analyze default portfolio
- `GET /categories` - List all portfolio categories
- `GET /categories/{name}/analysis` - Analyze specific category
- `GET /momentum/top/{limit}` - Get top momentum stocks

#### Example Response
```json
{
  "ticker": "NVDA",
  "composite_score": 85.2,
  "rating": "Strong Buy",
  "price_momentum": 92.1,
  "technical_momentum": 78.5,
  "fundamental_momentum": 85.0,
  "relative_momentum": 88.3
}
```

## Architecture

```
backend/
├── main.py              # FastAPI application
├── services/            # Business logic
│   ├── momentum_engine.py
│   └── portfolio_service.py
├── models/              # Pydantic data models
├── utils/               # Data providers
└── api/                 # API endpoints (future)
```

## Portfolio Categories

The system organizes investments into 8 strategic categories:

1. **Large-Cap Anchors (20%)** - NVDA, MSFT, META, etc.
2. **Small-Cap Specialists (15%)** - VRT, MOD, BE, etc.
3. **Data Center Infrastructure (15%)** - DLR, SRVR, IRM, etc.
4. **International Tech/Momentum (12%)** - EWJ, EWT, etc.
5. **Tactical Fixed Income (8%)** - SHY, VCIT, etc.
6. **Sector Momentum Rotation (10%)** - XLI, XLE, etc.
7. **Critical Metals & Mining (7%)** - MP, ALB, etc.
8. **Specialized Materials ETFs (5%)** - REMX, LIT, etc.

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Legacy Code
Original implementation files are preserved in `legacy/` directory.

### Next Steps
- Implement Alpha Vantage data provider
- Add mobile app (React Native/Flutter)
- Add user authentication
- Implement portfolio persistence
- Add real-time updates

## API Documentation

When running the server, visit http://localhost:8000/docs for interactive API documentation.