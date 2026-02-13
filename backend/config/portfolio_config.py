"""
Default Portfolio Configuration for AlphaVelocity

Canonical definition of the default model portfolio (ticker -> shares).
Import this from any module that needs the default portfolio to avoid
circular imports and ensure a single source of truth.
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
