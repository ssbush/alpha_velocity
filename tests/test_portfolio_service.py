import unittest
from unittest.mock import Mock, patch
import pandas as pd

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.portfolio_service import PortfolioService
from backend.services.momentum_engine import MomentumEngine

class TestPortfolioService(unittest.TestCase):
    """Test cases for PortfolioService"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_momentum_engine = Mock(spec=MomentumEngine)
        self.service = PortfolioService(self.mock_momentum_engine)

        # Sample portfolio
        self.sample_portfolio = {
            'NVDA': 10,
            'MSFT': 5,
            'AAPL': 8
        }

    def test_get_category_tickers(self):
        """Test getting tickers for a category"""
        tickers = self.service.get_category_tickers('Large-Cap Anchors')
        self.assertIsInstance(tickers, list)
        self.assertIn('NVDA', tickers)
        self.assertIn('MSFT', tickers)

    def test_get_category_tickers_invalid(self):
        """Test getting tickers for invalid category"""
        tickers = self.service.get_category_tickers('Invalid Category')
        self.assertEqual(tickers, [])

    def test_get_all_categories(self):
        """Test getting all categories"""
        categories = self.service.get_all_categories()
        self.assertIsInstance(categories, dict)
        self.assertIn('Large-Cap Anchors', categories)
        self.assertIn('target_allocation', categories['Large-Cap Anchors'])

    @patch('backend.utils.data_providers.YahooFinanceProvider.get_stock_data')
    def test_analyze_portfolio(self, mock_get_data):
        """Test portfolio analysis"""
        # Mock data provider responses
        mock_hist_data = pd.DataFrame({
            'Close': [100.0, 101.0, 102.0]
        })
        mock_get_data.return_value = (mock_hist_data, {})

        # Mock momentum engine responses
        self.mock_momentum_engine.calculate_momentum_score.return_value = {
            'composite_score': 75.0,
            'rating': 'Buy',
            'price_momentum': 80.0,
            'technical_momentum': 70.0,
            'fundamental_momentum': 75.0,
            'relative_momentum': 75.0
        }

        df, total_value, avg_score = self.service.analyze_portfolio(self.sample_portfolio)

        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(total_value, 0)
        self.assertGreaterEqual(avg_score, 0)
        self.assertEqual(len(df), len(self.sample_portfolio))

    def test_get_category_analysis(self):
        """Test category analysis"""
        # Mock momentum engine responses
        self.mock_momentum_engine.calculate_momentum_score.return_value = {
            'composite_score': 80.0,
            'rating': 'Strong Buy',
            'price_momentum': 85.0,
            'technical_momentum': 75.0,
            'fundamental_momentum': 80.0,
            'relative_momentum': 80.0
        }

        result = self.service.get_category_analysis('Large-Cap Anchors')

        self.assertIsInstance(result, dict)
        self.assertEqual(result['category'], 'Large-Cap Anchors')
        self.assertIn('average_score', result)
        self.assertIn('momentum_scores', result)

    def test_get_category_analysis_invalid(self):
        """Test category analysis for invalid category"""
        result = self.service.get_category_analysis('Invalid Category')
        self.assertIn('error', result)

    def test_get_top_momentum_stocks(self):
        """Test getting top momentum stocks"""
        # Mock momentum engine responses
        self.mock_momentum_engine.calculate_momentum_score.return_value = {
            'composite_score': 85.0,
            'rating': 'Strong Buy',
            'price_momentum': 90.0,
            'technical_momentum': 80.0,
            'fundamental_momentum': 85.0,
            'relative_momentum': 85.0
        }

        result = self.service.get_top_momentum_stocks(limit=5)

        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 5)

if __name__ == '__main__':
    unittest.main()