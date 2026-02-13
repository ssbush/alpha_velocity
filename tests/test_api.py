import unittest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

class TestAPI(unittest.TestCase):
    """Test cases for FastAPI endpoints"""

    def setUp(self):
        """Set up test client"""
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("version", data)

    @patch('backend.services.momentum_engine.MomentumEngine.calculate_momentum_score')
    def test_momentum_endpoint(self, mock_calculate):
        """Test momentum score endpoint"""
        mock_calculate.return_value = {
            'ticker': 'NVDA',
            'composite_score': 85.5,
            'rating': 'Strong Buy',
            'price_momentum': 90.0,
            'technical_momentum': 80.0,
            'fundamental_momentum': 85.0,
            'relative_momentum': 87.0
        }

        response = self.client.get("/momentum/NVDA")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['ticker'], 'NVDA')
        self.assertEqual(data['composite_score'], 85.5)
        self.assertEqual(data['rating'], 'Strong Buy')

    def test_categories_endpoint(self):
        """Test categories endpoint"""
        response = self.client.get("/categories")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Check structure of first category
        category = data[0]
        self.assertIn('name', category)
        self.assertIn('tickers', category)
        self.assertIn('target_allocation', category)
        self.assertIn('benchmark', category)

    def test_category_tickers_endpoint(self):
        """Test category tickers endpoint"""
        response = self.client.get("/categories/Large-Cap Anchors/tickers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('category', data)
        self.assertIn('tickers', data)
        self.assertIsInstance(data['tickers'], list)

    def test_category_tickers_invalid(self):
        """Test category tickers endpoint with invalid category"""
        response = self.client.get("/categories/Invalid Category/tickers")
        self.assertEqual(response.status_code, 404)

    @patch('backend.services.portfolio_service.PortfolioService.analyze_portfolio')
    def test_portfolio_analysis_endpoint(self, mock_analyze):
        """Test portfolio analysis endpoint"""
        # Mock portfolio analysis response
        mock_df = pd.DataFrame({
            'Ticker': ['NVDA', 'MSFT'],
            'Shares': [10, 5],
            'Price': ['$500.00', '$300.00'],
            'Market_Value': ['$5,000.00', '$1,500.00'],
            'Portfolio_%': ['76.9%', '23.1%'],
            'Momentum_Score': [85.0, 75.0],
            'Rating': ['Strong Buy', 'Buy'],
            'Price_Momentum': [90.0, 80.0],
            'Technical_Momentum': [80.0, 70.0]
        })

        mock_analyze.return_value = (mock_df, 6500.0, 80.0)

        response = self.client.get("/portfolio/analysis")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('holdings', data)
        self.assertIn('total_value', data)
        self.assertIn('average_momentum_score', data)

    def test_top_momentum_endpoint(self):
        """Test top momentum stocks endpoint"""
        response = self.client.get("/momentum/top/5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

if __name__ == '__main__':
    unittest.main()