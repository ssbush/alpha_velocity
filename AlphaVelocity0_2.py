import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import portfolio categories
from portfolio_pool import (
    lc_anchors, sp_spec, dc_ifra, int_tm,
    tac_fi, smr, cmm, sme, model_portfolio, analyze_model_portfolio
)

class AlphaVelocity:
    """
    AlphaVelocity Momentum Scoring Engine
    
    Generates systematic momentum scores for stocks using multiple factors:
    - Price Momentum (40%)
    - Technical Momentum (25%) 
    - Fundamental Momentum (25%)
    - Relative Momentum (10%)
    """
    
    def __init__(self):
        self.weights = {
            'price_momentum': 0.40,
            'technical_momentum': 0.25,
            'fundamental_momentum': 0.25,
            'relative_momentum': 0.10
        }
        
        # Portfolio categories with target allocations
        self.portfolio_categories = {
            'Large-Cap Anchors': {'tickers': lc_anchors, 'target_allocation': 0.20, 'benchmark': 'QQQ'},
            'Small-Cap Specialists': {'tickers': sp_spec, 'target_allocation': 0.15, 'benchmark': 'XLK'},
            'Data Center Infrastructure': {'tickers': dc_ifra, 'target_allocation': 0.15, 'benchmark': 'VNQ'},
            'International Tech/Momentum': {'tickers': int_tm, 'target_allocation': 0.12, 'benchmark': 'VEA'},
            'Tactical Fixed Income': {'tickers': tac_fi, 'target_allocation': 0.08, 'benchmark': 'AGG'},
            'Sector Momentum Rotation': {'tickers': smr, 'target_allocation': 0.10, 'benchmark': 'SPY'},
            'Critical Metals & Mining': {'tickers': cmm, 'target_allocation': 0.07, 'benchmark': 'XLB'},
            'Specialized Materials ETFs': {'tickers': sme, 'target_allocation': 0.05, 'benchmark': 'XLB'}
        }
        
    def get_stock_data(self, ticker, period='1y'):
        """Fetch stock data from Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            info = stock.info
            return hist, info
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None, None
    
    def calculate_price_momentum(self, hist_data):
        """Calculate price momentum component (40% of total score)"""
        if len(hist_data) < 249:  # Need at least 1 year of data (conservative estimate)
            return 0
            
        current_price = hist_data['Close'].iloc[-1]
        
        # Calculate returns over different periods
        returns = {}
        periods = {
            '1m': 21,   # 1 month
            '3m': 63,   # 3 months
            '6m': 126,  # 6 months
            '12m': 249  # 12 months (conservative trading days estimate)
        }
        
        for period, days in periods.items():
            if len(hist_data) >= days:
                past_price = hist_data['Close'].iloc[-days]
                returns[period] = (current_price / past_price) - 1
            else:
                returns[period] = 0
        
        # Weight recent performance more heavily
        weights = {'1m': 0.4, '3m': 0.3, '6m': 0.2, '12m': 0.1}
        weighted_return = sum(returns[period] * weights[period] for period in returns)
        
        # Moving average signals
        ma_20 = hist_data['Close'].rolling(20).mean().iloc[-1]
        ma_50 = hist_data['Close'].rolling(50).mean().iloc[-1]
        ma_200 = hist_data['Close'].rolling(200).mean().iloc[-1]
        
        ma_score = 0
        if current_price > ma_20:
            ma_score += 0.4
        if current_price > ma_50:
            ma_score += 0.3
        if current_price > ma_200:
            ma_score += 0.3
            
        # Combine weighted return and MA signals
        momentum_score = (weighted_return * 100) + (ma_score * 100)
        
        return min(100, max(0, momentum_score))
    
    def calculate_technical_momentum(self, hist_data):
        """Calculate technical momentum component (25% of total score)"""
        if len(hist_data) < 50:
            return 0
            
        # RSI Calculation
        delta = hist_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # RSI scoring (50-70 is ideal momentum range)
        if 50 <= current_rsi <= 70:
            rsi_score = 100
        elif 30 <= current_rsi < 50:
            rsi_score = (current_rsi - 30) * 2.5  # Scale 30-50 to 0-50
        elif 70 < current_rsi <= 85:
            rsi_score = 100 - ((current_rsi - 70) * 2)  # Slight penalty for overbought
        else:
            rsi_score = 0
            
        # Volume confirmation
        avg_volume = hist_data['Volume'].rolling(30).mean().iloc[-1]
        current_volume = hist_data['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volume score (higher volume on up days is good)
        volume_score = min(100, volume_ratio * 50)
        
        # Rate of Change (10-day)
        current_price = hist_data['Close'].iloc[-1]
        price_10d_ago = hist_data['Close'].iloc[-10]
        roc = ((current_price / price_10d_ago) - 1) * 100
        roc_score = min(100, max(0, roc * 10 + 50))
        
        technical_score = (rsi_score * 0.4) + (volume_score * 0.3) + (roc_score * 0.3)
        return min(100, max(0, technical_score))
    
    def calculate_fundamental_momentum(self, stock_info):
        """Calculate fundamental momentum component (25% of total score)"""
        # This is simplified - in practice you'd want real-time earnings data
        try:
            # Basic fundamental checks
            forward_pe = stock_info.get('forwardPE', 0)
            trailing_pe = stock_info.get('trailingPE', 0)
            peg_ratio = stock_info.get('pegRatio', 0)
            
            # Revenue and earnings growth
            revenue_growth = stock_info.get('revenueGrowth', 0)
            earnings_growth = stock_info.get('earningsGrowth', 0)
            
            # Profitability metrics
            roe = stock_info.get('returnOnEquity', 0)
            profit_margin = stock_info.get('profitMargins', 0)
            
            # Scoring based on growth and profitability
            growth_score = 0
            if revenue_growth and revenue_growth > 0:
                growth_score += min(50, revenue_growth * 100)
            if earnings_growth and earnings_growth > 0:
                growth_score += min(50, earnings_growth * 100)
                
            profitability_score = 0
            if roe and roe > 0:
                profitability_score += min(50, roe * 100)
            if profit_margin and profit_margin > 0:
                profitability_score += min(50, profit_margin * 100)
                
            # Valuation score (lower PEG is better)
            valuation_score = 0
            if peg_ratio and 0 < peg_ratio < 2:
                valuation_score = 100 - (peg_ratio * 50)
                
            fundamental_score = (growth_score * 0.4) + (profitability_score * 0.4) + (valuation_score * 0.2)
            return min(100, max(0, fundamental_score))
            
        except Exception as e:
            print(f"Error calculating fundamental momentum: {e}")
            return 50  # Default neutral score
    
    def calculate_relative_momentum(self, hist_data, benchmark_ticker='SPY', sector_benchmark=None):
        """Calculate relative momentum vs benchmark and sector (10% of total score)"""
        try:
            # Get primary benchmark data (usually SPY)
            benchmark = yf.Ticker(benchmark_ticker)
            bench_hist = benchmark.history(period='1y')
            
            if len(bench_hist) < 63:  # Need at least 3 months
                return 50
            
            # Calculate relative performance vs primary benchmark
            stock_3m = (hist_data['Close'].iloc[-1] / hist_data['Close'].iloc[-63]) - 1
            bench_3m = (bench_hist['Close'].iloc[-1] / bench_hist['Close'].iloc[-63]) - 1
            relative_3m_primary = stock_3m - bench_3m
            
            if len(hist_data) >= 126:
                stock_6m = (hist_data['Close'].iloc[-1] / hist_data['Close'].iloc[-126]) - 1
                bench_6m = (bench_hist['Close'].iloc[-1] / bench_hist['Close'].iloc[-126]) - 1
                relative_6m_primary = stock_6m - bench_6m
            else:
                relative_6m_primary = relative_3m_primary
            
            primary_relative = (relative_3m_primary * 0.7) + (relative_6m_primary * 0.3)
            
            # If sector benchmark provided, calculate sector-relative performance
            if sector_benchmark:
                try:
                    sector_bench = yf.Ticker(sector_benchmark)
                    sector_hist = sector_bench.history(period='1y')
                    
                    if len(sector_hist) >= 63:
                        sector_3m = (sector_hist['Close'].iloc[-1] / sector_hist['Close'].iloc[-63]) - 1
                        sector_relative_3m = stock_3m - sector_3m
                        
                        if len(sector_hist) >= 126:
                            sector_6m = (sector_hist['Close'].iloc[-1] / sector_hist['Close'].iloc[-126]) - 1
                            sector_relative_6m = stock_6m - sector_6m
                        else:
                            sector_relative_6m = sector_relative_3m
                            
                        sector_relative = (sector_relative_3m * 0.7) + (sector_relative_6m * 0.3)
                        
                        # Combine primary and sector relative (60% primary, 40% sector)
                        combined_relative = (primary_relative * 0.6) + (sector_relative * 0.4)
                    else:
                        combined_relative = primary_relative
                except:
                    combined_relative = primary_relative
            else:
                combined_relative = primary_relative
            
            # Convert to 0-100 scale
            relative_score = 50 + (combined_relative * 500)
            return min(100, max(0, relative_score))
            
        except Exception as e:
            print(f"Error calculating relative momentum: {e}")
            return 50
    
    def calculate_momentum_score(self, ticker, benchmark='SPY', sector_benchmark=None):
        """Calculate composite momentum score for a stock"""
        print(f"Calculating AlphaVelocity score for {ticker}...")
        
        # Get stock data
        hist_data, stock_info = self.get_stock_data(ticker)
        if hist_data is None:
            return None
            
        # Calculate component scores
        price_momentum = self.calculate_price_momentum(hist_data)
        technical_momentum = self.calculate_technical_momentum(hist_data)
        fundamental_momentum = self.calculate_fundamental_momentum(stock_info)
        relative_momentum = self.calculate_relative_momentum(hist_data, benchmark, sector_benchmark)
        
        # Calculate weighted composite score
        composite_score = (
            price_momentum * self.weights['price_momentum'] +
            technical_momentum * self.weights['technical_momentum'] +
            fundamental_momentum * self.weights['fundamental_momentum'] +
            relative_momentum * self.weights['relative_momentum']
        )
        
        return {
            'ticker': ticker,
            'composite_score': round(composite_score, 2),
            'price_momentum': round(price_momentum, 2),
            'technical_momentum': round(technical_momentum, 2),
            'fundamental_momentum': round(fundamental_momentum, 2),
            'relative_momentum': round(relative_momentum, 2),
            'rating': self.get_rating(composite_score),
            'benchmark': benchmark,
            'sector_benchmark': sector_benchmark
        }
    
    def get_rating(self, score):
        """Convert numeric score to rating"""
        if score >= 80:
            return "Very Strong"
        elif score >= 60:
            return "Strong"
        elif score >= 40:
            return "Neutral"
        elif score >= 20:
            return "Weak"
        else:
            return "Very Weak"

    def analyze_categorized_portfolio(self):
        """Analyze the full categorized AI supply chain portfolio"""
        category_results = {}
        
        print("AlphaVelocity Categorized Portfolio Analysis")
        print("=" * 60)
        
        for category_name, category_data in self.portfolio_categories.items():
            print(f"\nAnalyzing {category_name} ({category_data['target_allocation']*100:.0f}% allocation)...")
            
            tickers = category_data['tickers']
            benchmark = category_data['benchmark']
            
            # Analyze each security in the category
            category_scores = []
            for ticker in tickers:
                score = self.calculate_momentum_score(ticker, benchmark)
                if score:
                    score['category'] = category_name
                    score['target_allocation'] = category_data['target_allocation']
                    category_scores.append(score)
            
            # Sort by momentum score within category
            category_scores.sort(key=lambda x: x['composite_score'], reverse=True)
            
            category_results[category_name] = {
                'scores': category_scores,
                'target_allocation': category_data['target_allocation'],
                'benchmark': benchmark,
                'top_pick': category_scores[0] if category_scores else None,
                'avg_score': np.mean([s['composite_score'] for s in category_scores]) if category_scores else 0
            }
            
        return category_results

    def analyze_portfolio(self, tickers, benchmark='SPY'):
        """Analyze multiple stocks and return ranked results"""
        results = []
        
        for ticker in tickers:
            score = self.calculate_momentum_score(ticker, benchmark)
            if score:
                results.append(score)
                
        # Sort by composite score (descending)
        results.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # Convert to DataFrame for easy viewing
        df = pd.DataFrame(results)
        return df
    
    def analyze_reit_portfolio(self, reit_tickers, benchmark='SPY', reit_benchmark='VNQ'):
        """Specialized REIT analysis with appropriate benchmarks"""
        results = []
        
        print(f"Analyzing REIT portfolio with benchmarks: {benchmark} (primary), {reit_benchmark} (sector)")
        
        for ticker in reit_tickers:
            score = self.calculate_momentum_score(ticker, benchmark, reit_benchmark)
            if score:
                results.append(score)
                
        # Sort by composite score (descending)
        results.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # Convert to DataFrame for easy viewing
        df = pd.DataFrame(results)
        return df

    def calculate_country_momentum(self, country_etf_ticker, base_benchmark='SPY', global_benchmark='VEA'):
        """Calculate momentum score for country ETFs with multiple benchmark comparisons"""
        try:
            # Get country ETF data
            country_data, country_info = self.get_stock_data(country_etf_ticker)
            if country_data is None:
                return None
                
            current_price = country_data['Close'].iloc[-1]
            
            # Calculate relative performance vs multiple benchmarks
            benchmarks = {
                'vs_spy': base_benchmark,      # vs US market
                'vs_global': global_benchmark   # vs developed international
            }
            
            relative_scores = {}
            
            for bench_name, bench_ticker in benchmarks.items():
                try:
                    bench_data, _ = self.get_stock_data(bench_ticker)
                    if bench_data is not None and len(bench_data) >= 126:
                        # 3-month and 6-month relative performance
                        country_3m = (country_data['Close'].iloc[-1] / country_data['Close'].iloc[-63]) - 1
                        bench_3m = (bench_data['Close'].iloc[-1] / bench_data['Close'].iloc[-63]) - 1
                        rel_3m = country_3m - bench_3m
                        
                        country_6m = (country_data['Close'].iloc[-1] / country_data['Close'].iloc[-126]) - 1
                        bench_6m = (bench_data['Close'].iloc[-1] / bench_data['Close'].iloc[-126]) - 1
                        rel_6m = country_6m - bench_6m
                        
                        # Weight recent performance more heavily
                        relative_scores[bench_name] = (rel_3m * 0.7) + (rel_6m * 0.3)
                    else:
                        relative_scores[bench_name] = 0
                except:
                    relative_scores[bench_name] = 0
            
            # Technical momentum for country ETF
            technical_score = self.calculate_technical_momentum(country_data)
            
            # Volume and liquidity check
            avg_volume = country_data['Volume'].rolling(30).mean().iloc[-1]
            volume_score = min(100, (avg_volume / 1000000))  # Prefer higher volume ETFs
            
            # Currency momentum (simplified - could be enhanced with FX data)
            price_momentum_score = self.calculate_price_momentum(country_data)
            
            return {
                'country': country_etf_ticker,
                'relative_vs_spy': relative_scores.get('vs_spy', 0),
                'relative_vs_global': relative_scores.get('vs_global', 0),
                'technical_momentum': technical_score / 100,  # Normalize to 0-1
                'price_momentum': price_momentum_score / 100,
                'volume_score': volume_score / 100,
                'composite_score': self.calculate_country_composite_score(relative_scores, technical_score, price_momentum_score, volume_score)
            }
            
        except Exception as e:
            print(f"Error calculating country momentum for {country_etf_ticker}: {e}")
            return None

    def calculate_country_composite_score(self, relative_scores, technical_score, price_momentum, volume_score):
        """Calculate weighted composite score for country momentum"""
        # Weights for country selection
        weights = {
            'relative_vs_spy': 0.3,      # 30% - outperformance vs US
            'relative_vs_global': 0.25,   # 25% - outperformance vs international
            'technical': 0.25,           # 25% - technical momentum
            'price_momentum': 0.15,      # 15% - absolute price momentum
            'volume': 0.05               # 5% - liquidity preference
        }
        
        # Convert relative performance to 0-100 scale
        rel_spy_score = 50 + (relative_scores.get('vs_spy', 0) * 500)
        rel_global_score = 50 + (relative_scores.get('vs_global', 0) * 500)
        
        # Ensure scores are within bounds
        rel_spy_score = min(100, max(0, rel_spy_score))
        rel_global_score = min(100, max(0, rel_global_score))
        
        composite = (
            rel_spy_score * weights['relative_vs_spy'] +
            rel_global_score * weights['relative_vs_global'] +
            technical_score * weights['technical'] +
            price_momentum * weights['price_momentum'] +
            volume_score * weights['volume']
        )
        
        return round(composite, 2)

    def analyze_international_rotation(self, country_etfs=None, top_n=3):
        """Analyze country ETFs for international momentum rotation"""
        if country_etfs is None:
            # Default country ETF universe with tech/semiconductor exposure
            country_etfs = {
                'EWJ': 'Japan (Nintendo, Sony, semiconductor equipment)',
                'EWT': 'Taiwan (TSMC, semiconductor foundries)', 
                'EWY': 'South Korea (Samsung, SK Hynix, memory)',
                'INDA': 'India (IT services, software)',
                'EWG': 'Germany (SAP, industrial automation)',
                'EWU': 'United Kingdom (ARM, fintech)',
                'EWC': 'Canada (Shopify, tech services)',
                'EWA': 'Australia (mining tech, data centers)'
            }
        
        results = []
        print("Analyzing International Tech/Momentum Opportunities...")
        
        for etf_ticker, description in country_etfs.items():
            country_score = self.calculate_country_momentum(etf_ticker)
            if country_score:
                country_score['description'] = description
                country_score['rating'] = self.get_rating(country_score['composite_score'])
                results.append(country_score)
        
        # Sort by composite score
        results.sort(key=lambda x: x['composite_score'], reverse=True)
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Return top N countries for rotation
        top_countries = df.head(top_n)
        
        print(f"\nTop {top_n} Countries for International Rotation:")
        print("-" * 80)
        for _, row in top_countries.iterrows():
            print(f"{row['country']}: {row['composite_score']:.1f} ({row['rating']}) - {row['description']}")
        
        return df, top_countries

    def get_international_allocation_weights(self, top_countries_df, total_allocation=0.12):
        """Calculate position weights for international allocation"""
        if len(top_countries_df) == 0:
            return {}
            
        # Score-weighted allocation (higher scores get more allocation)
        total_score = top_countries_df['composite_score'].sum()
        
        allocations = {}
        for _, row in top_countries_df.iterrows():
            weight = (row['composite_score'] / total_score) * total_allocation
            allocations[row['country']] = round(weight, 4)
            
        return allocations

    def check_country_rotation_signals(self, current_holdings, country_momentum_df, rotation_threshold=15):
        """Check if country rotation is needed based on momentum changes"""
        rotation_signals = []
        
        for holding in current_holdings:
            current_country = country_momentum_df[country_momentum_df['country'] == holding]
            if not current_country.empty:
                score = current_country.iloc[0]['composite_score']
                rating = current_country.iloc[0]['rating']
                
                if score < rotation_threshold:
                    rotation_signals.append({
                        'action': 'SELL',
                        'country': holding,
                        'reason': f'Score fell to {score:.1f} (below {rotation_threshold})',
                        'rating': rating
                    })
        
        # Check for new opportunities
        top_opportunities = country_momentum_df.head(3)
        for _, opportunity in top_opportunities.iterrows():
            if opportunity['country'] not in current_holdings and opportunity['composite_score'] > 60:
                rotation_signals.append({
                    'action': 'BUY',
                    'country': opportunity['country'],
                    'reason': f'Strong momentum score: {opportunity["composite_score"]:.1f}',
                    'rating': opportunity['rating']
                })
        
        return rotation_signals
        
    def get_sector_benchmarks(self, sector_type='tech'):
        """Get appropriate sector benchmark tickers"""
        benchmarks = {
            'tech': 'XLK',      # Technology Select Sector SPDR
            'reit': 'VNQ',      # Vanguard Real Estate ETF
            'datacenter': 'SRVR', # Data Center ETF (closest proxy)
            'semiconductor': 'SOXX', # iShares Semiconductor ETF
            'ai_infra': 'DTCR', # Global X Data Center ETF
            'materials': 'XLB', # Materials Select Sector SPDR
            'energy': 'XLE',    # Energy Select Sector SPDR
            'financials': 'XLF', # Financial Select Sector SPDR
            'healthcare': 'XLV', # Health Care Select Sector SPDR
        }
        return benchmarks.get(sector_type, 'SPY')
    
    def get_top_momentum_stocks(self, tickers, top_n=10):
        """Get top N stocks by momentum score"""
        df = self.analyze_portfolio(tickers)
        return df.head(top_n)
    
    def display_categorized_results(self, category_results):
        """Display categorized portfolio analysis in organized format"""
        print("\n" + "=" * 80)
        print("AI SUPPLY CHAIN MOMENTUM ANALYSIS - CATEGORY BREAKDOWN")
        print("=" * 80)
        
        total_weighted_score = 0
        total_allocation = 0
        
        for category_name, category_data in category_results.items():
            scores = category_data['scores']
            target_alloc = category_data['target_allocation']
            benchmark = category_data['benchmark']
            avg_score = category_data['avg_score']
            
            print(f"\n📈 {category_name.upper()}")
            print(f"Target Allocation: {target_alloc*100:.0f}% | Benchmark: {benchmark} | Avg Score: {avg_score:.1f}")
            print("-" * 60)
            
            if scores:
                # Show top 3 momentum picks in each category
                top_picks = scores[:3]
                for i, score in enumerate(top_picks, 1):
                    rating = score['rating']
                    emoji = "🟢" if score['composite_score'] >= 60 else "🟡" if score['composite_score'] >= 40 else "🔴"
                    print(f"{emoji} {i}. {score['ticker']:<6} Score: {score['composite_score']:>5.1f} ({rating})")
                
                if len(scores) > 3:
                    print(f"    ... and {len(scores)-3} more securities")
            else:
                print("    No valid momentum scores available")
                
            # Calculate weighted contribution to portfolio
            weighted_score = avg_score * target_alloc
            total_weighted_score += weighted_score
            total_allocation += target_alloc
            
        print(f"\n" + "=" * 80)
        print(f"PORTFOLIO WEIGHTED MOMENTUM SCORE: {total_weighted_score:.1f}")
        print(f"TOTAL ALLOCATION: {total_allocation*100:.0f}%")
        print("=" * 80)
        
        return total_weighted_score
    
    def generate_rebalancing_signals(self, category_results, momentum_threshold=40, top_n_per_category=2):
        """Generate rebalancing signals based on category momentum analysis"""
        signals = []
        
        print(f"\n🔄 REBALANCING SIGNALS (Momentum Threshold: {momentum_threshold})")
        print("=" * 60)
        
        for category_name, category_data in category_results.items():
            scores = category_data['scores']
            target_alloc = category_data['target_allocation']
            
            if not scores:
                continue
                
            category_signals = []
            
            # Top momentum picks for the category
            top_picks = scores[:top_n_per_category]
            weak_positions = [s for s in scores if s['composite_score'] < momentum_threshold]
            
            print(f"\n📊 {category_name} ({target_alloc*100:.0f}% allocation):")
            
            # Recommend top momentum positions
            for pick in top_picks:
                if pick['composite_score'] >= 60:  # Strong momentum
                    signal = {
                        'action': 'BUY/OVERWEIGHT',
                        'ticker': pick['ticker'],
                        'category': category_name,
                        'score': pick['composite_score'],
                        'rating': pick['rating'],
                        'reason': f"Strong momentum in {category_name}"
                    }
                    category_signals.append(signal)
                    print(f"  🟢 BUY/OVERWEIGHT {pick['ticker']} - Score: {pick['composite_score']:.1f} ({pick['rating']})")
            
            # Flag weak positions for reduction/selling
            for weak in weak_positions:
                signal = {
                    'action': 'SELL/UNDERWEIGHT',
                    'ticker': weak['ticker'],
                    'category': category_name,
                    'score': weak['composite_score'],
                    'rating': weak['rating'],
                    'reason': f"Weak momentum below threshold ({momentum_threshold})"
                }
                category_signals.append(signal)
                print(f"  🔴 SELL/UNDERWEIGHT {weak['ticker']} - Score: {weak['composite_score']:.1f} ({weak['rating']})")
            
            if not category_signals:
                print(f"  ⚪ HOLD current positions - No strong signals")
            
            signals.extend(category_signals)
        
        return signals
    
    def get_category_summary_df(self, category_results):
        """Create DataFrame summary of category performance"""
        summary_data = []
        
        for category_name, category_data in category_results.items():
            scores = category_data['scores']
            
            summary_row = {
                'Category': category_name,
                'Target_Allocation_%': category_data['target_allocation'] * 100,
                'Benchmark': category_data['benchmark'],
                'Securities_Count': len(scores),
                'Avg_Momentum_Score': category_data['avg_score'],
                'Top_Pick': scores[0]['ticker'] if scores else 'N/A',
                'Top_Pick_Score': scores[0]['composite_score'] if scores else 0,
                'Category_Strength': self.get_rating(category_data['avg_score'])
            }
            summary_data.append(summary_row)
        
        return pd.DataFrame(summary_data)

# Example usage
if __name__ == "__main__":
    # Initialize AlphaVelocity engine
    av = AlphaVelocity()
    
    print("🚀 AlphaVelocity 0.2 - AI Supply Chain Momentum Analysis")
    print("=" * 60)
    
    # NEW: Categorized Portfolio Analysis
    print("\n🔍 Running Categorized AI Supply Chain Analysis...")
    category_results = av.analyze_categorized_portfolio()
    
    # Display results by category
    portfolio_score = av.display_categorized_results(category_results)
    
    # Generate rebalancing signals
    signals = av.generate_rebalancing_signals(category_results, momentum_threshold=45)
    
    # Category summary DataFrame
    print(f"\n📊 CATEGORY SUMMARY DATAFRAME:")
    summary_df = av.get_category_summary_df(category_results)
    print(summary_df.to_string(index=False))
    
    # Export signals to DataFrame for analysis
    if signals:
        signals_df = pd.DataFrame(signals)
        print(f"\n💡 REBALANCING SIGNALS SUMMARY:")
        print(f"Total Signals: {len(signals)}")
        buy_signals = len([s for s in signals if 'BUY' in s['action']])
        sell_signals = len([s for s in signals if 'SELL' in s['action']])
        print(f"Buy/Overweight: {buy_signals} | Sell/Underweight: {sell_signals}")
        
    print(f"\n🎯 PORTFOLIO METRICS:")
    print(f"Overall Momentum Score: {portfolio_score:.1f}")
    print(f"Categories Analyzed: {len(category_results)}")
    total_securities = sum(len(cat_data['scores']) for cat_data in category_results.values())
    print(f"Total Securities: {total_securities}")
    
    # Legacy analysis for comparison
    print(f"\n" + "="*60)
    print("📈 LEGACY ANALYSIS (For Comparison)")
    print("="*60)
    
    # Example REIT Analysis
    print(f"\nREIT-Specific Analysis:")
    data_center_reits = [
        'DLR', 'EQIX', 'AMT', 'IRM', 'BIP', 'PLD', 'CCI', 'UNIT',
        'DBRG'
        ]
    
    # Analyze REITs with proper benchmarks
    reit_results = av.analyze_reit_portfolio(
        data_center_reits, 
        benchmark='SPY',        # Primary benchmark
        reit_benchmark='VNQ'    # REIT sector benchmark
    )

    # Get top momentum picks
    #print(f"\nTop 5 Momentum Stocks:")
    #top_stocks = av.get_top_momentum_stocks(ai_stocks, top_n=15)
    #print(top_stocks[['ticker', 'composite_score', 'rating']].to_string(index=False))
    
    print("Data Center REITs vs VNQ (REIT Index) & SPY:")
    print(reit_results[['ticker', 'composite_score', 'rating', 'benchmark', 'sector_benchmark']].to_string(index=False))
    
    # Compare different REIT benchmarks
    print(f"\nBenchmark Options for REITs:")
    benchmarks = {
        'VNQ': 'Vanguard Real Estate ETF (Broad REITs)',
        'SRVR': 'Pacer Data Center ETF (Data Center Focus)', 
        'FREL': 'Fidelity MSCI Real Estate ETF',
        'IYR': 'iShares US Real Estate ETF',
        'XLRE': 'Real Estate Select Sector SPDR'
    }
    
    for ticker, description in benchmarks.items():
        print(f"  {ticker}: {description}")
    
    # Show how to get sector-specific benchmarks
    print(f"\nSector Benchmark Helper:")
    print(f"REIT Benchmark: {av.get_sector_benchmarks('reit')}")
    print(f"Data Center Benchmark: {av.get_sector_benchmarks('datacenter')}")
    print(f"Tech Benchmark: {av.get_sector_benchmarks('tech')}")
    print(f"AI Infrastructure Benchmark: {av.get_sector_benchmarks('ai_infra')}")

    # Analyze country momentum opportunities
    country_analysis, top_countries = av.analyze_international_rotation(top_n=4)

    # Show detailed analysis
    print(f"\nDetailed Country Momentum Scores:")
    display_cols = ['country', 'composite_score', 'relative_vs_spy', 'relative_vs_global', 'technical_momentum', 'rating']
    print(country_analysis[display_cols].round(3).to_string(index=False))
    
    # Calculate allocation weights
    allocations = av.get_international_allocation_weights(top_countries, total_allocation=0.12)
    print(f"\nRecommended 12% International Allocation:")
    total_check = 0
    for country, weight in allocations.items():
        percentage = weight * 100
        print(f"  {country}: {percentage:.1f}%")
        total_check += weight
    print(f"  Total: {total_check*100:.1f}%")
    
    # Rotation signals example
    current_international_holdings = ['EWJ', 'INDA', 'EWT']  # Example current holdings
    rotation_signals = av.check_country_rotation_signals(current_international_holdings, country_analysis)
    
    if rotation_signals:
        print(f"\nRotation Signals:")
        for signal in rotation_signals:
            print(f"  {signal['action']} {signal['country']}: {signal['reason']}")
    else:
        print(f"\nNo rotation signals - maintain current international allocation")
        
    print(f"\nCountry Selection Methodology:")
    print("- 30% weight: Relative performance vs SPY (US market)")  
    print("- 25% weight: Relative performance vs VEA (global developed)")
    print("- 25% weight: Technical momentum indicators")
    print("- 15% weight: Absolute price momentum")
    print("- 5% weight: ETF liquidity/volume")

    # MODEL PORTFOLIO ANALYSIS
    print(f"\n" + "="*80)
    print("🎯 MODEL PORTFOLIO ANALYSIS")
    print("="*80)

    # Analyze the specific model portfolio with position sizes
    portfolio_df, total_portfolio_value, avg_momentum = analyze_model_portfolio(model_portfolio, av)

    # Display the portfolio table
    print(f"\nModel Portfolio Holdings (sorted by momentum score):")
    print("-" * 100)
    print(portfolio_df.to_string(index=False))

    # Top momentum positions
    top_3 = portfolio_df.head(3)
    print(f"\n🏆 Top 3 Momentum Positions:")
    for i, (_, row) in enumerate(top_3.iterrows(), 1):
        emoji = "🟢" if row['Momentum_Score'] >= 60 else "🟡" if row['Momentum_Score'] >= 40 else "🔴"
        print(f"{emoji} {i}. {row['Ticker']} - {row['Portfolio_%']} of portfolio - Score: {row['Momentum_Score']:.1f} ({row['Rating']})")

    # Weak positions alert
    weak_positions = portfolio_df[portfolio_df['Momentum_Score'] < 40]
    if not weak_positions.empty:
        print(f"\n⚠️  Weak Momentum Positions (Score < 40):")
        for _, row in weak_positions.iterrows():
            print(f"🔴 {row['Ticker']} - {row['Portfolio_%']} - Score: {row['Momentum_Score']:.1f} ({row['Rating']})")

    # Portfolio composition by category
    print(f"\n📊 Portfolio Composition by Strategy Category:")
    print("-" * 50)

    # Map tickers to categories
    category_mapping = {
        'Large-Cap Anchors': ['NVDA', 'AVGO', 'MSFT', 'META', 'NOW'],
        'Small-Cap Specialists': ['VRT', 'MOD', 'BE', 'UI'],
        'Data Center Infrastructure': ['DLR', 'SRVR', 'IRM'],
        'International Tech/Momentum': ['EWJ', 'EWT'],
        'Tactical Fixed Income': ['SHY'],
        'Sector Momentum Rotation': ['XLI'],
        'Critical Metals & Mining': ['MP']
    }

    for category, tickers in category_mapping.items():
        category_positions = portfolio_df[portfolio_df['Ticker'].isin(tickers)]
        if not category_positions.empty:
            category_total = 0
            for _, pos in category_positions.iterrows():
                # Extract numeric value from formatted string
                value_str = pos['Market_Value'].replace('$', '').replace(',', '')
                category_total += float(value_str)

            category_pct = (category_total / total_portfolio_value) * 100
            avg_cat_momentum = category_positions['Momentum_Score'].mean()

            # Get category emoji based on average momentum
            cat_emoji = "🟢" if avg_cat_momentum >= 60 else "🟡" if avg_cat_momentum >= 40 else "🔴"
            print(f"{cat_emoji} {category}: {category_pct:.1f}% (${category_total:,.0f}) - Avg Momentum: {avg_cat_momentum:.1f}")

    # Portfolio summary metrics
    print(f"\n📈 Portfolio Summary:")
    print(f"Total Value: ${total_portfolio_value:,.2f}")
    print(f"Positions: {len(portfolio_df)}")
    print(f"Average Momentum Score: {avg_momentum:.1f}")

    # Generate portfolio signals
    strong_positions = len(portfolio_df[portfolio_df['Momentum_Score'] >= 60])
    neutral_positions = len(portfolio_df[(portfolio_df['Momentum_Score'] >= 40) & (portfolio_df['Momentum_Score'] < 60)])
    weak_positions_count = len(portfolio_df[portfolio_df['Momentum_Score'] < 40])

    print(f"Strong Momentum (≥60): {strong_positions} positions")
    print(f"Neutral Momentum (40-59): {neutral_positions} positions")
    print(f"Weak Momentum (<40): {weak_positions_count} positions")

    if avg_momentum >= 60:
        print(f"✅ Portfolio Status: Strong momentum - maintain allocation")
    elif avg_momentum >= 45:
        print(f"⚠️  Portfolio Status: Mixed momentum - consider rebalancing weak positions")
    else:
        print(f"🔴 Portfolio Status: Weak momentum - significant rebalancing recommended")
