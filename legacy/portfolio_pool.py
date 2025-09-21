##  * Portfolio Pool *

model_portfolio = {
    ## lc_anchors
    "NVDA": 7, "AVGO": 4, "MSFT": 2, "META": 1, "NOW": 1,

    ## sp_spec
    "VRT": 7, "MOD": 10, "BE": 30, "UI": 3, 

    ## dc_infra
    "DLR": 6, "SRVR": 58, "IRM": 10,

    ## int_tm
    "EWJ": 14, "EWT": 17,

    ## tac_fi
    "SHY": 13,

    ## smr
    "XLI": 7,

    ## cmm
    "MP": 16
}

def analyze_model_portfolio(model_portfolio, av_engine=None):
    """
    Analyze model portfolio with position sizes, percentages, and momentum signals

    Parameters:
    - model_portfolio: dict with ticker: shares mapping
    - av_engine: AlphaVelocity instance (optional, will create if None)

    Returns:
    - DataFrame with analysis results
    """
    import yfinance as yf
    import pandas as pd

    if av_engine is None:
        from AlphaVelocity0_2 import AlphaVelocity
        av_engine = AlphaVelocity()

    # Get current prices for all positions
    tickers = list(model_portfolio.keys())
    prices_data = {}

    print(f"Fetching current prices for {len(tickers)} positions...")

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1d')
            if not hist.empty:
                prices_data[ticker] = hist['Close'].iloc[-1]
            else:
                print(f"Warning: No price data for {ticker}")
                prices_data[ticker] = 0
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            prices_data[ticker] = 0

    # Calculate portfolio values
    portfolio_data = []
    total_value = 0

    for ticker, shares in model_portfolio.items():
        price = prices_data.get(ticker, 0)
        market_value = shares * price
        total_value += market_value

        portfolio_data.append({
            'ticker': ticker,
            'shares': shares,
            'price': price,
            'market_value': market_value
        })

    # Calculate percentages and get momentum signals
    results = []

    for data in portfolio_data:
        ticker = data['ticker']
        percentage = (data['market_value'] / total_value * 100) if total_value > 0 else 0

        # Get momentum score
        print(f"Getting momentum signal for {ticker}...")
        momentum_result = av_engine.calculate_momentum_score(ticker)

        if momentum_result:
            composite_score = momentum_result['composite_score']
            rating = momentum_result['rating']
            price_momentum = momentum_result['price_momentum']
            technical_momentum = momentum_result['technical_momentum']
        else:
            composite_score = 0
            rating = 'N/A'
            price_momentum = 0
            technical_momentum = 0

        results.append({
            'Ticker': ticker,
            'Shares': data['shares'],
            'Price': f"${data['price']:.2f}",
            'Market_Value': f"${data['market_value']:,.2f}",
            'Portfolio_%': f"{percentage:.1f}%",
            'Momentum_Score': composite_score,
            'Rating': rating,
            'Price_Momentum': price_momentum,
            'Technical_Momentum': technical_momentum
        })

    # Create DataFrame and sort by portfolio percentage (descending)
    df = pd.DataFrame(results)
    df = df.sort_values('Momentum_Score', ascending=False)

    # Add summary statistics
    total_portfolio_value = sum(data['market_value'] for data in portfolio_data)
    avg_momentum_score = df['Momentum_Score'].mean()

    print(f"\n{'='*80}")
    print(f"MODEL PORTFOLIO ANALYSIS")
    print(f"{'='*80}")
    print(f"Total Portfolio Value: ${total_portfolio_value:,.2f}")
    print(f"Number of Positions: {len(model_portfolio)}")
    print(f"Average Momentum Score: {avg_momentum_score:.1f}")
    print(f"{'='*80}")

    return df, total_portfolio_value, avg_momentum_score

## - Large-Cap Anchors (20%)
lc_anchors = [
    'NVDA', 'TSM', 'ASML', 'AVGO', 'MSFT', 'META', 'AAPL',
    'AMD', 'ASML', 'GOOGL', 'TSLA', 'PLTR', 'CSCO', 'CRWV',
    'ORCL', 'DT', 'AUR', 'MBLY', 'NOW'
    ]

## - Small-Cap Specialists (15%)
sp_spec = [
    'VRT', 'MOD', 'BE', # Power & Cooling
    'CIEN', 'ATKR', 'UI', # Networking & Components
    'APLD', 'SMCI', 'GDS', 'VNET' # Data center
    ]

## - Data  Center Infrastructure (15%)
dc_ifra = [
    'SRVR', 'DLR', 'EQIX', 'AMT', 'CCI', # Core REITs
    'COR', 'IRM', # Dynamic REIT Rotation
    'ACM', # Construction
    'JCI', # Cooling
    'IDGT', 'DTCR', # Data center ETFs
    ]

## - International Tech/Momentum (12%)
int_tm = [
    'EWJ', 'EWT', 'INDA', 'EWY'
    ]

## - Tactical Fixed Income (8%)
tac_fi = [
    'SHY', 'VCIT', 'IPE'
    ]

## - Sector Momentum Rotation (10%)
smr = [
    'XLE', 'XLF', 'XLI', 'XLU', 'XLB'
    ]

## - Critical Metals & Mining (5-7%)
cmm = [
    'MP', 'LYC', 'ARA', 'ALB', 'SQM', 'LAC', 'FCX', 'SCCO', 'TECK'
    ]

## - Specialized Materials ETFs (3-5%)
sme = [
    'REMX', 'LIT', 'XMET'
    ]
