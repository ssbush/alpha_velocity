import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.momentum_engine import MomentumEngine
from backend.utils.data_providers import DataProvider

class TestMomentumEngine(unittest.TestCase):
    """Test cases for MomentumEngine"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = MomentumEngine()

        # Create sample historical data
        dates = pd.date_range('2023-01-01', periods=300, freq='D')
        np.random.seed(42)  # For reproducible tests
        prices = 100 + np.cumsum(np.random.randn(300) * 0.5)
        volumes = np.random.randint(1000000, 5000000, 300)

        self.sample_hist_data = pd.DataFrame({
            'Close': prices,
            'Volume': volumes
        }, index=dates)

    def test_calculate_price_momentum(self):
        """Test price momentum calculation"""
        score = self.engine.calculate_price_momentum(self.sample_hist_data)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_calculate_technical_momentum(self):
        """Test technical momentum calculation"""
        score = self.engine.calculate_technical_momentum(self.sample_hist_data)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_calculate_fundamental_momentum(self):
        """Test fundamental momentum calculation"""
        sample_info = {
            'forwardPE': 15.5,
            'trailingPE': 18.2,
            'pegRatio': 1.2
        }
        score = self.engine.calculate_fundamental_momentum(sample_info)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_insufficient_data_handling(self):
        """Test handling of insufficient data"""
        short_data = self.sample_hist_data.head(10)
        score = self.engine.calculate_price_momentum(short_data)
        self.assertEqual(score, 0)

    @patch('backend.utils.data_providers.YahooFinanceProvider.get_stock_data')
    def test_calculate_momentum_score_success(self, mock_get_data):
        """Test successful momentum score calculation"""
        mock_get_data.return_value = (self.sample_hist_data, {'forwardPE': 20})

        result = self.engine.calculate_momentum_score('NVDA')

        self.assertIsInstance(result, dict)
        self.assertEqual(result['ticker'], 'NVDA')
        self.assertIn('composite_score', result)
        self.assertIn('rating', result)
        self.assertGreaterEqual(result['composite_score'], 0)
        self.assertLessEqual(result['composite_score'], 100)

    @patch('backend.utils.data_providers.YahooFinanceProvider.get_stock_data')
    def test_calculate_momentum_score_no_data(self, mock_get_data):
        """Test momentum score calculation with no data"""
        mock_get_data.return_value = (None, None)

        result = self.engine.calculate_momentum_score('INVALID')

        self.assertEqual(result['composite_score'], 0)
        self.assertEqual(result['rating'], 'Insufficient Data')

if __name__ == '__main__':
    unittest.main()