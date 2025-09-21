#!/usr/bin/env python3
"""
Simplified HTTP server for AlphaVelocity API
Demonstrates the backend functionality without FastAPI dependencies
"""

import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import os

# Add backend modules to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.momentum_engine import MomentumEngine
from backend.services.portfolio_service import PortfolioService

# Initialize services
momentum_engine = MomentumEngine()
portfolio_service = PortfolioService(momentum_engine)

# Default model portfolio
DEFAULT_PORTFOLIO = {
    "NVDA": 7, "AVGO": 4, "MSFT": 2, "META": 1, "NOW": 1,
    "VRT": 7, "MOD": 10, "BE": 30, "UI": 3,
    "DLR": 6, "SRVR": 58, "IRM": 10,
    "EWJ": 14, "EWT": 17,
    "SHY": 13,
    "XLI": 7,
    "MP": 16
}

class AlphaVelocityHandler(BaseHTTPRequestHandler):
    """HTTP request handler for AlphaVelocity API"""

    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path_parts = parsed_path.path.strip('/').split('/')

            # Route requests
            if parsed_path.path == '/':
                self.handle_root()
            elif len(path_parts) == 2 and path_parts[0] == 'momentum':
                ticker = path_parts[1].upper()
                self.handle_momentum_score(ticker)
            elif parsed_path.path == '/portfolio/analysis':
                self.handle_portfolio_analysis()
            elif parsed_path.path == '/categories':
                self.handle_categories()
            elif len(path_parts) == 3 and path_parts[0] == 'categories' and path_parts[2] == 'analysis':
                category_name = path_parts[1]
                self.handle_category_analysis(category_name)
            elif len(path_parts) == 3 and path_parts[0] == 'momentum' and path_parts[1] == 'top':
                limit = int(path_parts[2]) if path_parts[2].isdigit() else 10
                self.handle_top_momentum(limit)
            else:
                self.send_error(404, "Endpoint not found")

        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")

    def handle_root(self):
        """Handle root endpoint"""
        response = {
            "message": "AlphaVelocity API is running",
            "version": "1.0.0",
            "endpoints": [
                "/momentum/{ticker}",
                "/portfolio/analysis",
                "/categories",
                "/categories/{name}/analysis",
                "/momentum/top/{limit}"
            ]
        }
        self.send_json_response(response)

    def handle_momentum_score(self, ticker):
        """Handle momentum score request"""
        print(f"Calculating momentum score for {ticker}...")
        result = momentum_engine.calculate_momentum_score(ticker)
        self.send_json_response(result)

    def handle_portfolio_analysis(self):
        """Handle portfolio analysis request"""
        print("Analyzing default portfolio...")
        df, total_value, avg_score = portfolio_service.analyze_portfolio(DEFAULT_PORTFOLIO)

        # Convert DataFrame to list of dictionaries
        holdings = []
        for _, row in df.iterrows():
            holdings.append({
                'ticker': row['Ticker'],
                'shares': row['Shares'],
                'price': row['Price'],
                'market_value': row['Market_Value'],
                'portfolio_percent': row['Portfolio_%'],
                'momentum_score': row['Momentum_Score'],
                'rating': row['Rating'],
                'price_momentum': row['Price_Momentum'],
                'technical_momentum': row['Technical_Momentum']
            })

        response = {
            'holdings': holdings,
            'total_value': total_value,
            'average_momentum_score': avg_score,
            'number_of_positions': len(DEFAULT_PORTFOLIO)
        }
        self.send_json_response(response)

    def handle_categories(self):
        """Handle categories list request"""
        categories = portfolio_service.get_all_categories()
        result = []
        for name, info in categories.items():
            result.append({
                'name': name,
                'tickers': info['tickers'],
                'target_allocation': info['target_allocation'],
                'benchmark': info['benchmark']
            })
        self.send_json_response(result)

    def handle_category_analysis(self, category_name):
        """Handle category analysis request"""
        print(f"Analyzing category: {category_name}")
        result = portfolio_service.get_category_analysis(category_name)

        if 'error' in result:
            self.send_error(404, result['error'])
        else:
            self.send_json_response(result)

    def handle_top_momentum(self, limit):
        """Handle top momentum stocks request"""
        print(f"Getting top {limit} momentum stocks...")
        result = portfolio_service.get_top_momentum_stocks(limit=min(limit, 20))
        self.send_json_response(result)

    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # Enable CORS
        self.end_headers()

        json_data = json.dumps(data, indent=2)
        self.wfile.write(json_data.encode('utf-8'))

    def log_message(self, format, *args):
        """Override to customize logging"""
        print(f"[{self.address_string()}] {format % args}")

def run_server(port=8000):
    """Run the HTTP server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, AlphaVelocityHandler)

    print(f"🚀 AlphaVelocity API Server starting on http://localhost:{port}")
    print(f"📊 Available endpoints:")
    print(f"  • http://localhost:{port}/")
    print(f"  • http://localhost:{port}/momentum/NVDA")
    print(f"  • http://localhost:{port}/portfolio/analysis")
    print(f"  • http://localhost:{port}/categories")
    print(f"  • http://localhost:{port}/momentum/top/10")
    print(f"\n⚡ Server ready! Press Ctrl+C to stop.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped.")
        httpd.server_close()

if __name__ == '__main__':
    run_server()