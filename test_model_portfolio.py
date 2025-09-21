#!/usr/bin/env python3
"""
Test script to analyze the model portfolio with AlphaVelocity momentum signals
"""

from portfolio_pool import model_portfolio, analyze_model_portfolio
from AlphaVelocity0_2 import AlphaVelocity

def main():
    print("🚀 AlphaVelocity Model Portfolio Analysis")
    print("=" * 60)

    # Initialize AlphaVelocity engine
    av = AlphaVelocity()

    # Analyze the model portfolio
    portfolio_df, total_value, avg_score = analyze_model_portfolio(model_portfolio, av)

    # Display results
    print("\nPortfolio Holdings (sorted by momentum score):")
    print("-" * 80)
    pd_display = portfolio_df.copy()

    # Clean up display format for numeric columns
    pd_display['Momentum_Score'] = portfolio_df['Momentum_Score'].astype(float)
    pd_display['Price_Momentum'] = portfolio_df['Price_Momentum'].astype(float)
    pd_display['Technical_Momentum'] = portfolio_df['Technical_Momentum'].astype(float)

    print(portfolio_df.to_string(index=False))

    # Show top momentum picks
    top_3 = portfolio_df.head(3)
    print(f"\nTop 3 Momentum Positions:")
    print("-" * 40)
    for _, row in top_3.iterrows():
        emoji = "🟢" if row['Momentum_Score'] >= 60 else "🟡" if row['Momentum_Score'] >= 40 else "🔴"
        print(f"{emoji} {row['Ticker']} - {row['Portfolio_%']} - Score: {row['Momentum_Score']:.1f} ({row['Rating']})")

    # Show weakest positions
    weak_positions = portfolio_df[portfolio_df['Momentum_Score'] < 40]
    if not weak_positions.empty:
        print(f"\nWeak Momentum Positions (Score < 40):")
        print("-" * 40)
        for _, row in weak_positions.iterrows():
            print(f"🔴 {row['Ticker']} - {row['Portfolio_%']} - Score: {row['Momentum_Score']:.1f} ({row['Rating']})")

    # Portfolio summary by strategy category
    print(f"\nPortfolio Composition by Strategy:")
    print("-" * 40)

    # Map tickers to categories (based on model_portfolio structure)
    category_mapping = {
        'Large-Cap Anchors': ['NVDA', 'AVGO', 'MSFT', 'META', 'NOW'],
        'Small-Cap Specialists': ['VRT', 'MOD', 'BE', 'UI'],
        'Data Center Infrastructure': ['DLR', 'SRVR', 'IRM'],
        'International Tech/Momentum': ['EWJ', 'EWT'],
        'Tactical Fixed Income': ['SHY'],
        'Sector Momentum Rotation': ['XLI'],
        'Critical Metals & Mining': ['MP']
    }

    category_values = {}
    for category, tickers in category_mapping.items():
        category_total = 0
        category_positions = portfolio_df[portfolio_df['Ticker'].isin(tickers)]

        for _, pos in category_positions.iterrows():
            # Extract numeric value from formatted string
            value_str = pos['Market_Value'].replace('$', '').replace(',', '')
            category_total += float(value_str)

        if category_total > 0:
            category_pct = (category_total / total_value) * 100
            category_values[category] = {'value': category_total, 'percentage': category_pct}
            avg_momentum = category_positions['Momentum_Score'].mean() if not category_positions.empty else 0
            print(f"{category}: {category_pct:.1f}% (${category_total:,.0f}) - Avg Momentum: {avg_momentum:.1f}")

if __name__ == "__main__":
    main()