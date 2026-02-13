"""
Portfolio Configuration for AlphaVelocity

Canonical definitions of the default model portfolio and portfolio categories.
Import from any module that needs these to avoid circular imports and ensure
a single source of truth.
"""

# Default model portfolio for demo / analysis
DEFAULT_PORTFOLIO = {
    "NVDA": 7, "AVGO": 4, "MSFT": 2, "META": 1, "NOW": 1, "AAPL": 4, "GOOGL": 4,
    "VRT": 7, "MOD": 10, "BE": 30, "UI": 3,
    "DLR": 6, "SRVR": 58, "IRM": 10, "CCI": 10,
    "EWJ": 14, "EWT": 17,
    "SHY": 13,
    "XLI": 7,
    "MP": 16
}

# Portfolio categories with target allocations and benchmarks
PORTFOLIO_CATEGORIES = {
    'Large-Cap Anchors': {
        'tickers': ['NVDA', 'TSM', 'ASML', 'AVGO', 'MSFT', 'META', 'AAPL', 'AMD', 'GOOGL', 'TSLA', 'PLTR', 'CSCO', 'CRWV', 'ORCL', 'DT', 'AUR', 'MBLY', 'NOW'],
        'target_allocation': 0.20,
        'benchmark': 'QQQ'
    },
    'Small-Cap Specialists': {
        'tickers': ['VRT', 'MOD', 'BE', 'CIEN', 'ATKR', 'UI', 'APLD', 'SMCI', 'GDS', 'VNET'],
        'target_allocation': 0.15,
        'benchmark': 'XLK'
    },
    'Data Center Infrastructure': {
        'tickers': ['SRVR', 'DLR', 'EQIX', 'AMT', 'CCI', 'COR', 'IRM', 'ACM', 'JCI', 'IDGT', 'DTCR'],
        'target_allocation': 0.15,
        'benchmark': 'VNQ'
    },
    'International Tech/Momentum': {
        'tickers': ['EWJ', 'EWT', 'INDA', 'EWY'],
        'target_allocation': 0.12,
        'benchmark': 'VEA'
    },
    'Tactical Fixed Income': {
        'tickers': ['SHY', 'VCIT', 'IPE'],
        'target_allocation': 0.08,
        'benchmark': 'AGG'
    },
    'Sector Momentum Rotation': {
        'tickers': ['XLE', 'XLF', 'XLI', 'XLU', 'XLB'],
        'target_allocation': 0.10,
        'benchmark': 'SPY'
    },
    'Critical Metals & Mining': {
        'tickers': ['MP', 'LYC', 'ARA', 'ALB', 'SQM', 'LAC', 'FCX', 'SCCO', 'TECK'],
        'target_allocation': 0.07,
        'benchmark': 'XLB'
    },
    'Specialized Materials ETFs': {
        'tickers': ['REMX', 'LIT', 'XMET'],
        'target_allocation': 0.05,
        'benchmark': 'XLB'
    }
}

# Map API sort field names to DataFrame column names
SORT_COLUMN_MAP = {
    'momentum_score': 'Momentum_Score',
    'ticker': 'Ticker',
    'market_value': 'Market_Value',
    'portfolio_percent': 'Portfolio_%',
    'price': 'Price',
    'shares': 'Shares',
}
