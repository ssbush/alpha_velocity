"""
Tests for stock split transaction support.

Covers:
- SPLIT transaction processing in UserPortfolioService
- Split validation (ratio > 0, price == 0, holding must exist)
- _recalculate_holding replays splits correctly
- /splits/{ticker} API endpoint
"""

import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock, PropertyMock

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.models.database import Base, Portfolio, Holding, Transaction, SecurityMaster, User
from backend.services.user_portfolio_service import UserPortfolioService
from backend.main import app


# ============================================================================
# Database fixtures (SQLite in-memory)
# ============================================================================

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")

    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def service(db_session):
    """Create a UserPortfolioService with a test DB session."""
    return UserPortfolioService(db_session)


@pytest.fixture
def portfolio_with_holding(db_session):
    """Create a portfolio with a BUY holding for AAPL (100 shares @ $50)."""
    user = User(id=1, username="testuser", email="test@test.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()

    portfolio = Portfolio(id=1, user_id=1, name="Test Portfolio", is_active=True)
    db_session.add(portfolio)
    db_session.flush()

    security = SecurityMaster(id=1, ticker="AAPL", security_type="STOCK", is_active=True)
    db_session.add(security)
    db_session.flush()

    holding = Holding(
        portfolio_id=1,
        security_id=1,
        shares=Decimal("100"),
        average_cost_basis=Decimal("50.0000"),
        total_cost_basis=Decimal("5000.00"),
    )
    db_session.add(holding)

    # Add the BUY transaction that created this holding
    txn = Transaction(
        portfolio_id=1,
        security_id=1,
        transaction_type="BUY",
        transaction_date=date(2025, 1, 1),
        shares=Decimal("100"),
        price_per_share=Decimal("50.0000"),
        total_amount=Decimal("5000.00"),
        fees=Decimal("0"),
    )
    db_session.add(txn)
    db_session.commit()

    return portfolio


# ============================================================================
# SPLIT transaction — holding updates
# ============================================================================


class TestSplitHoldingUpdate:
    """SPLIT transactions should multiply shares and divide avg cost."""

    def test_split_updates_holding_correctly(self, service, portfolio_with_holding, db_session):
        """4:1 split: 100 shares @ $50 → 400 shares @ $12.50, total cost $5000 unchanged."""
        service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SPLIT", shares=Decimal("4"),
            price_per_share=Decimal("0"), transaction_date=date(2025, 6, 1),
        )

        holding = db_session.query(Holding).filter_by(portfolio_id=1, security_id=1).first()
        assert holding.shares == Decimal("400")
        assert holding.average_cost_basis == Decimal("12.5000")
        assert holding.total_cost_basis == Decimal("5000.00")

    def test_split_stores_positive_ratio(self, service, portfolio_with_holding, db_session):
        """SPLIT transaction stores the ratio as a positive number (not negated like SELL)."""
        service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SPLIT", shares=Decimal("4"),
            price_per_share=Decimal("0"), transaction_date=date(2025, 6, 1),
        )

        txn = db_session.query(Transaction).filter_by(
            portfolio_id=1, transaction_type="SPLIT"
        ).first()
        assert txn.shares == Decimal("4")
        assert txn.shares > 0

    def test_reverse_split(self, service, portfolio_with_holding, db_session):
        """Reverse split (0.5 ratio): 100 shares @ $50 → 50 shares @ $100."""
        service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SPLIT", shares=Decimal("0.5"),
            price_per_share=Decimal("0"), transaction_date=date(2025, 6, 1),
        )

        holding = db_session.query(Holding).filter_by(portfolio_id=1, security_id=1).first()
        assert holding.shares == Decimal("50")
        assert holding.total_cost_basis == Decimal("5000.00")

    def test_multiple_splits_in_sequence(self, service, portfolio_with_holding, db_session):
        """Two sequential splits: 100 → 4:1 → 400 → 2:1 → 800 shares."""
        service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SPLIT", shares=Decimal("4"),
            price_per_share=Decimal("0"), transaction_date=date(2025, 6, 1),
        )
        service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SPLIT", shares=Decimal("2"),
            price_per_share=Decimal("0"), transaction_date=date(2025, 9, 1),
        )

        holding = db_session.query(Holding).filter_by(portfolio_id=1, security_id=1).first()
        assert holding.shares == Decimal("800")
        assert holding.total_cost_basis == Decimal("5000.00")


# ============================================================================
# SPLIT validation
# ============================================================================


class TestSplitValidation:
    """SPLIT transactions must pass specific validations."""

    def test_rejects_ratio_zero(self, service, portfolio_with_holding):
        with pytest.raises(ValueError, match="Split ratio must be greater than 0"):
            service.add_transaction(
                portfolio_id=1, user_id=1, ticker="AAPL",
                transaction_type="SPLIT", shares=Decimal("0"),
                price_per_share=Decimal("0"), transaction_date=date(2025, 6, 1),
            )

    def test_rejects_negative_ratio(self, service, portfolio_with_holding):
        with pytest.raises(ValueError, match="Split ratio must be greater than 0"):
            service.add_transaction(
                portfolio_id=1, user_id=1, ticker="AAPL",
                transaction_type="SPLIT", shares=Decimal("-2"),
                price_per_share=Decimal("0"), transaction_date=date(2025, 6, 1),
            )

    def test_rejects_nonzero_price(self, service, portfolio_with_holding):
        with pytest.raises(ValueError, match="Price per share must be 0"):
            service.add_transaction(
                portfolio_id=1, user_id=1, ticker="AAPL",
                transaction_type="SPLIT", shares=Decimal("4"),
                price_per_share=Decimal("10"), transaction_date=date(2025, 6, 1),
            )

    def test_rejects_split_without_holding(self, service, db_session):
        """SPLIT requires an existing holding for the ticker."""
        user = User(id=1, username="testuser", email="test@test.com", password_hash="hash")
        db_session.add(user)
        db_session.flush()
        portfolio = Portfolio(id=2, user_id=1, name="Empty Portfolio", is_active=True)
        db_session.add(portfolio)
        db_session.commit()

        with pytest.raises(ValueError, match="No existing holding"):
            service.add_transaction(
                portfolio_id=2, user_id=1, ticker="MSFT",
                transaction_type="SPLIT", shares=Decimal("4"),
                price_per_share=Decimal("0"), transaction_date=date(2025, 6, 1),
            )


# ============================================================================
# _recalculate_holding with splits
# ============================================================================


class TestRecalculateWithSplits:
    """_recalculate_holding should correctly replay SPLIT transactions."""

    def test_recalculate_replays_split(self, service, portfolio_with_holding, db_session):
        """BUY 100 @ $50 → SPLIT 4:1 → SELL 50 → delete SELL → recalculate → 400 shares."""
        # Add split
        service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SPLIT", shares=Decimal("4"),
            price_per_share=Decimal("0"), transaction_date=date(2025, 6, 1),
        )
        # Add sell
        sell_txn = service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SELL", shares=Decimal("50"),
            price_per_share=Decimal("200"), transaction_date=date(2025, 7, 1),
        )

        # Verify post-sell state
        holding = db_session.query(Holding).filter_by(portfolio_id=1, security_id=1).first()
        assert holding.shares == Decimal("350")

        # Delete the sell — triggers _recalculate_holding
        service.delete_transaction(portfolio_id=1, user_id=1, transaction_id=sell_txn.id)

        # After recalculate: BUY 100 → SPLIT 4:1 → 400 shares
        holding = db_session.query(Holding).filter_by(portfolio_id=1, security_id=1).first()
        assert holding.shares == Decimal("400")
        assert holding.total_cost_basis == Decimal("5000.00")

    def test_recalculate_multiple_splits(self, service, portfolio_with_holding, db_session):
        """BUY → SPLIT → SPLIT → SELL → delete SELL → should have both splits applied."""
        service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SPLIT", shares=Decimal("2"),
            price_per_share=Decimal("0"), transaction_date=date(2025, 3, 1),
        )
        service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SPLIT", shares=Decimal("3"),
            price_per_share=Decimal("0"), transaction_date=date(2025, 6, 1),
        )
        sell_txn = service.add_transaction(
            portfolio_id=1, user_id=1, ticker="AAPL",
            transaction_type="SELL", shares=Decimal("100"),
            price_per_share=Decimal("100"), transaction_date=date(2025, 7, 1),
        )

        service.delete_transaction(portfolio_id=1, user_id=1, transaction_id=sell_txn.id)

        holding = db_session.query(Holding).filter_by(portfolio_id=1, security_id=1).first()
        # 100 * 2 * 3 = 600
        assert holding.shares == Decimal("600")
        assert holding.total_cost_basis == Decimal("5000.00")


# ============================================================================
# /splits/{ticker} API endpoint
# ============================================================================


@pytest.fixture
def client():
    return TestClient(app)


class TestSplitsEndpoint:
    """/splits/{ticker} returns split history from PriceService."""

    @patch("backend.main.price_service")
    def test_returns_splits(self, mock_ps, client):
        splits_data = pd.Series(
            [4.0, 2.0],
            index=pd.to_datetime(["2020-08-31", "2024-11-08"]),
        )
        mock_ps.get_split_history.return_value = splits_data

        resp = client.get("/splits/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert len(data["splits"]) == 2
        assert data["splits"][0]["date"] == "2020-08-31"
        assert data["splits"][0]["ratio"] == 4.0

    @patch("backend.main.price_service")
    def test_empty_splits(self, mock_ps, client):
        mock_ps.get_split_history.return_value = None

        resp = client.get("/splits/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["splits"] == []

    @patch("backend.main.price_service")
    def test_invalid_ticker(self, mock_ps, client):
        resp = client.get("/splits/INVALID!!!")
        assert resp.status_code == 400
