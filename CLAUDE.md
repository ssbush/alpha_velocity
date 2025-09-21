# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlphaVelocity is a Python-based momentum scoring engine for stock analysis and portfolio management. The system analyzes stocks using multiple momentum factors (price, technical, fundamental, and relative momentum) and applies these to categorized AI supply chain portfolios.

## Core Architecture

### Main Components

- **AlphaVelocity0_2.py**: Primary momentum scoring engine class with weighted factor analysis
- **portfolio_pool.py**: Portfolio configuration module containing predefined ticker categories and model portfolio allocations
- **AlphaVelocity.py** / **AlphaVelocity0.1.py**: Earlier versions of the scoring engine

### Portfolio Structure

The system organizes investments into 8 strategic categories:
- Large-Cap Anchors (20% allocation, QQQ benchmark)
- Small-Cap Specialists (15% allocation, XLK benchmark)
- Data Center Infrastructure (15% allocation, VNQ benchmark)
- International Tech/Momentum (12% allocation, VEA benchmark)
- Tactical Fixed Income (8% allocation, AGG benchmark)
- Sector Momentum Rotation (10% allocation, SPY benchmark)
- Critical Metals & Mining (7% allocation, XLB benchmark)
- Specialized Materials ETFs (5% allocation, XLB benchmark)

### Momentum Scoring Weights
- Price Momentum: 40%
- Technical Momentum: 25%
- Fundamental Momentum: 25%
- Relative Momentum: 10%

## Development Commands

### Running Tests
```bash
# Run categorized analysis test
python3 test_categorized_analysis.py

# Run model portfolio analysis
python3 test_model_portfolio.py

# Run unit tests (if available)
python3 -m unittest discover
```

### Main Execution
```bash
# Run latest version of AlphaVelocity
python3 AlphaVelocity0_2.py

# Run portfolio analysis
python3 -c "from portfolio_pool import analyze_model_portfolio; from AlphaVelocity0_2 import AlphaVelocity; av = AlphaVelocity(); analyze_model_portfolio({}, av)"
```

## Dependencies

Key external dependencies:
- pandas: Data manipulation and analysis
- numpy: Numerical computations
- yfinance: Yahoo Finance data retrieval
- datetime: Date/time handling

Standard library modules:
- unittest: Testing framework (pytest not available)
- warnings: Warning control

## Development Environment

- Python 3.11.2
- Dev container configured with VS Code extensions for Python development
- Uses unittest for testing (pytest not installed)
- Format on save enabled via VS Code settings