"""
Tests for MomentumCacheService (backend/services/momentum_cache_service.py)

Uses an in-memory SQLite database for Tier 2 tests and mocks for Tier 1/3.
"""

import asyncio
import time
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.database import (
    Base,
    MomentumScore,
    PriceHistory,
    SecurityMaster,
)
from backend.services.momentum_cache_service import MomentumCacheService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeMomentumEngine:
    """Minimal stand-in for MomentumEngine with controllable cache."""

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 86400

    def calculate_momentum_score(self, ticker):
        return {
            "ticker": ticker,
            "composite_score": 72.5,
            "rating": "Buy",
            "price_momentum": 75.0,
            "technical_momentum": 68.0,
            "fundamental_momentum": 70.0,
            "relative_momentum": 80.0,
            "current_price": 150.0,
        }


class FakeDbConfig:
    """Wraps an in-memory SQLite engine behind the same interface as DatabaseConfig."""

    def __init__(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session_context(self):
        session = self._Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@pytest.fixture
def engine():
    return FakeMomentumEngine()


@pytest.fixture
def db():
    return FakeDbConfig()


@pytest.fixture
def service(engine, db):
    return MomentumCacheService(engine, db_config=db)


@pytest.fixture
def service_no_db(engine):
    return MomentumCacheService(engine, db_config=None)


def _seed_security(db, ticker="NVDA"):
    """Insert a SecurityMaster row and return it."""
    with db.get_session_context() as session:
        sec = SecurityMaster(ticker=ticker, security_type="STOCK", is_active=True)
        session.add(sec)
        session.flush()
        sid = sec.id
    return sid


def _seed_score(db, security_id, score_date, composite=85.0, rating="Strong Buy"):
    with db.get_session_context() as session:
        session.add(
            MomentumScore(
                security_id=security_id,
                score_date=score_date,
                composite_score=composite,
                price_momentum=80.0,
                technical_momentum=75.0,
                fundamental_momentum=90.0,
                relative_momentum=70.0,
                rating=rating,
            )
        )


def _seed_price(db, security_id, price_date, close_price=500.0):
    with db.get_session_context() as session:
        session.add(
            PriceHistory(
                security_id=security_id,
                price_date=price_date,
                close_price=close_price,
            )
        )


# ---------------------------------------------------------------------------
# _score_to_rating
# ---------------------------------------------------------------------------


class TestScoreToRating:
    def test_strong_buy(self):
        assert MomentumCacheService._score_to_rating(80) == "Strong Buy"
        assert MomentumCacheService._score_to_rating(95) == "Strong Buy"

    def test_buy(self):
        assert MomentumCacheService._score_to_rating(65) == "Buy"
        assert MomentumCacheService._score_to_rating(79.9) == "Buy"

    def test_hold(self):
        assert MomentumCacheService._score_to_rating(50) == "Hold"
        assert MomentumCacheService._score_to_rating(64.9) == "Hold"

    def test_weak_hold(self):
        assert MomentumCacheService._score_to_rating(35) == "Weak Hold"
        assert MomentumCacheService._score_to_rating(49.9) == "Weak Hold"

    def test_sell(self):
        assert MomentumCacheService._score_to_rating(34.9) == "Sell"
        assert MomentumCacheService._score_to_rating(0) == "Sell"


# ---------------------------------------------------------------------------
# Tier 1 — In-memory cache
# ---------------------------------------------------------------------------


class TestTier1MemoryCache:
    def test_hit_returns_cached_data(self, engine):
        svc = MomentumCacheService(engine)
        cached = {"ticker": "NVDA", "composite_score": 90.0}
        engine._cache["momentum_NVDA"] = (cached, time.time())

        data = {}
        missing = svc._check_memory_cache(["NVDA"], data)

        assert missing == []
        assert "NVDA" in data
        assert data["NVDA"]["composite_score"] == 90.0

    def test_expired_entry_treated_as_miss(self, engine):
        svc = MomentumCacheService(engine)
        old = {"ticker": "NVDA", "composite_score": 90.0}
        engine._cache["momentum_NVDA"] = (old, time.time() - 100000)

        data = {}
        missing = svc._check_memory_cache(["NVDA"], data)

        assert missing == ["NVDA"]
        assert "NVDA" not in data

    def test_miss_returns_ticker(self, engine):
        svc = MomentumCacheService(engine)
        data = {}
        missing = svc._check_memory_cache(["AAPL", "MSFT"], data)

        assert missing == ["AAPL", "MSFT"]
        assert data == {}

    def test_mixed_hit_and_miss(self, engine):
        svc = MomentumCacheService(engine)
        engine._cache["momentum_NVDA"] = (
            {"ticker": "NVDA", "composite_score": 88.0},
            time.time(),
        )

        data = {}
        missing = svc._check_memory_cache(["NVDA", "AAPL"], data)

        assert missing == ["AAPL"]
        assert "NVDA" in data

    def test_returns_copy_not_reference(self, engine):
        svc = MomentumCacheService(engine)
        original = {"ticker": "NVDA", "composite_score": 88.0}
        engine._cache["momentum_NVDA"] = (original, time.time())

        data = {}
        svc._check_memory_cache(["NVDA"], data)
        data["NVDA"]["composite_score"] = 0  # mutate
        assert original["composite_score"] == 88.0  # original unchanged


# ---------------------------------------------------------------------------
# Tier 2 — PostgreSQL (via in-memory SQLite)
# ---------------------------------------------------------------------------


class TestTier2Database:
    def test_hit_returns_db_data(self, service, db):
        sid = _seed_security(db, "NVDA")
        _seed_score(db, sid, date.today(), composite=85.0, rating="Strong Buy")
        _seed_price(db, sid, date.today(), close_price=500.0)

        data = {}
        missing = service._check_database(["NVDA"], data)

        assert missing == []
        assert data["NVDA"]["composite_score"] == 85.0
        assert data["NVDA"]["rating"] == "Strong Buy"
        assert data["NVDA"]["current_price"] == 500.0
        assert data["NVDA"]["price_momentum"] == 80.0

    def test_miss_when_no_score(self, service, db):
        _seed_security(db, "AAPL")
        # No score inserted

        data = {}
        missing = service._check_database(["AAPL"], data)

        assert missing == ["AAPL"]

    def test_miss_when_unknown_ticker(self, service, db):
        data = {}
        missing = service._check_database(["ZZZZ"], data)
        assert missing == ["ZZZZ"]

    def test_backfills_memory_cache(self, service, engine, db):
        sid = _seed_security(db, "NVDA")
        _seed_score(db, sid, date.today())

        data = {}
        service._check_database(["NVDA"], data)

        assert "momentum_NVDA" in engine._cache
        cached_data, _ = engine._cache["momentum_NVDA"]
        assert cached_data["composite_score"] == 85.0

    def test_price_defaults_to_zero_when_no_price_row(self, service, db):
        sid = _seed_security(db, "NVDA")
        _seed_score(db, sid, date.today())
        # No price row

        data = {}
        service._check_database(["NVDA"], data)

        assert data["NVDA"]["current_price"] == 0.0

    def test_mixed_hit_and_miss(self, service, db):
        sid = _seed_security(db, "NVDA")
        _seed_score(db, sid, date.today())
        _seed_security(db, "AAPL")
        # AAPL has no score

        data = {}
        missing = service._check_database(["NVDA", "AAPL"], data)

        assert "NVDA" in data
        assert missing == ["AAPL"]

    def test_rating_fallback_when_null(self, service, db):
        sid = _seed_security(db, "NVDA")
        _seed_score(db, sid, date.today(), composite=72.0, rating=None)

        data = {}
        service._check_database(["NVDA"], data)

        assert data["NVDA"]["rating"] == "Buy"  # 72 → Buy

    def test_db_exception_falls_back_gracefully(self, engine):
        broken_db = MagicMock()
        broken_db.get_session_context.side_effect = RuntimeError("connection failed")
        svc = MomentumCacheService(engine, db_config=broken_db)

        data = {}
        missing = svc._check_database(["NVDA"], data)

        assert missing == ["NVDA"]
        assert data == {}

    def test_latest_score_wins(self, service, db):
        """When multiple score dates exist, the most recent is returned."""
        sid = _seed_security(db, "NVDA")
        _seed_score(db, sid, date(2025, 1, 1), composite=50.0, rating="Hold")
        _seed_score(db, sid, date(2025, 6, 1), composite=90.0, rating="Strong Buy")

        data = {}
        service._check_database(["NVDA"], data)

        assert data["NVDA"]["composite_score"] == 90.0


# ---------------------------------------------------------------------------
# Tier 2 — query helpers directly
# ---------------------------------------------------------------------------


class TestQueryHelpers:
    def test_query_latest_scores_empty(self, service, db):
        with db.get_session_context() as session:
            result = service._query_latest_scores(session, ["ZZZZ"])
        assert result == {}

    def test_query_latest_prices_empty(self, service, db):
        with db.get_session_context() as session:
            result = service._query_latest_prices(session, ["ZZZZ"])
        assert result == {}

    def test_query_latest_scores_returns_most_recent(self, service, db):
        sid = _seed_security(db, "MSFT")
        _seed_score(db, sid, date(2025, 1, 1), composite=40.0)
        _seed_score(db, sid, date(2025, 12, 1), composite=92.0)

        with db.get_session_context() as session:
            result = service._query_latest_scores(session, ["MSFT"])
            # Access attribute inside session to avoid DetachedInstanceError
            assert float(result["MSFT"].composite_score) == 92.0

    def test_query_latest_prices_returns_most_recent(self, service, db):
        sid = _seed_security(db, "MSFT")
        _seed_price(db, sid, date(2025, 1, 1), close_price=300.0)
        _seed_price(db, sid, date(2025, 12, 1), close_price=450.0)

        with db.get_session_context() as session:
            result = service._query_latest_prices(session, ["MSFT"])

        assert float(result["MSFT"]) == 450.0


# ---------------------------------------------------------------------------
# Tier 3 — Live compute
# ---------------------------------------------------------------------------


class TestTier3LiveCompute:
    def test_compute_live_populates_data(self, service):
        data = {}
        asyncio.get_event_loop().run_until_complete(
            service._compute_live(["NVDA"], data)
        )
        assert "NVDA" in data
        assert data["NVDA"]["composite_score"] == 72.5

    def test_compute_live_persists_to_db(self, service, db):
        data = {}
        asyncio.get_event_loop().run_until_complete(
            service._compute_live(["NVDA"], data)
        )

        # Check DB was written
        with db.get_session_context() as session:
            sec = session.query(SecurityMaster).filter_by(ticker="NVDA").first()
            assert sec is not None
            score = (
                session.query(MomentumScore)
                .filter_by(security_id=sec.id)
                .first()
            )
            assert score is not None
            assert float(score.composite_score) == 72.5

    def test_compute_live_creates_security_master(self, service, db):
        data = {}
        asyncio.get_event_loop().run_until_complete(
            service._compute_live(["NEWSTOCK"], data)
        )

        with db.get_session_context() as session:
            sec = session.query(SecurityMaster).filter_by(ticker="NEWSTOCK").first()
            assert sec is not None
            assert sec.security_type == "STOCK"

    def test_compute_live_handles_engine_failure(self, engine, db):
        engine.calculate_momentum_score = MagicMock(side_effect=RuntimeError("boom"))
        svc = MomentumCacheService(engine, db_config=db)

        data = {}
        asyncio.get_event_loop().run_until_complete(
            svc._compute_live(["FAIL"], data)
        )

        assert "FAIL" not in data

    def test_compute_live_skips_db_persist_when_no_db(self, service_no_db):
        data = {}
        asyncio.get_event_loop().run_until_complete(
            service_no_db._compute_live(["NVDA"], data)
        )
        # Should still populate data, just not persist
        assert "NVDA" in data

    def test_compute_live_tolerates_persist_failure(self, engine):
        broken_db = MagicMock()
        broken_db.get_session_context.side_effect = RuntimeError("write failed")
        svc = MomentumCacheService(engine, db_config=broken_db)

        data = {}
        asyncio.get_event_loop().run_until_complete(
            svc._compute_live(["NVDA"], data)
        )

        # Data should still be in result even though persist failed
        assert "NVDA" in data
        assert data["NVDA"]["composite_score"] == 72.5


# ---------------------------------------------------------------------------
# _persist_to_database
# ---------------------------------------------------------------------------


class TestPersistToDatabase:
    def test_insert_new_score_and_price(self, service, db):
        rows = [
            (
                "NVDA",
                {
                    "composite_score": 85.0,
                    "price_momentum": 80.0,
                    "technical_momentum": 75.0,
                    "fundamental_momentum": 90.0,
                    "relative_momentum": 70.0,
                    "rating": "Strong Buy",
                    "current_price": 500.0,
                },
            )
        ]
        service._persist_to_database(rows)

        with db.get_session_context() as session:
            sec = session.query(SecurityMaster).filter_by(ticker="NVDA").first()
            assert sec is not None
            score = session.query(MomentumScore).filter_by(security_id=sec.id).first()
            assert float(score.composite_score) == 85.0
            price = session.query(PriceHistory).filter_by(security_id=sec.id).first()
            assert float(price.close_price) == 500.0

    def test_upsert_updates_existing_score(self, service, db):
        sid = _seed_security(db, "NVDA")
        _seed_score(db, sid, date.today(), composite=50.0)

        rows = [("NVDA", {"composite_score": 99.0, "rating": "Strong Buy", "current_price": 0})]
        service._persist_to_database(rows)

        with db.get_session_context() as session:
            score = (
                session.query(MomentumScore)
                .filter_by(security_id=sid, score_date=date.today())
                .first()
            )
            assert float(score.composite_score) == 99.0

    def test_upsert_updates_existing_price(self, service, db):
        sid = _seed_security(db, "NVDA")
        _seed_price(db, sid, date.today(), close_price=400.0)

        rows = [("NVDA", {"composite_score": 80.0, "current_price": 600.0})]
        service._persist_to_database(rows)

        with db.get_session_context() as session:
            price = (
                session.query(PriceHistory)
                .filter_by(security_id=sid, price_date=date.today())
                .first()
            )
            assert float(price.close_price) == 600.0

    def test_skips_price_when_zero_or_none(self, service, db):
        rows = [("NVDA", {"composite_score": 80.0, "current_price": 0})]
        service._persist_to_database(rows)

        with db.get_session_context() as session:
            sec = session.query(SecurityMaster).filter_by(ticker="NVDA").first()
            price = session.query(PriceHistory).filter_by(security_id=sec.id).first()
            assert price is None

    def test_multiple_tickers_in_one_call(self, service, db):
        rows = [
            ("NVDA", {"composite_score": 85.0, "current_price": 500.0, "rating": "Strong Buy"}),
            ("AAPL", {"composite_score": 60.0, "current_price": 200.0, "rating": "Hold"}),
        ]
        service._persist_to_database(rows)

        with db.get_session_context() as session:
            assert session.query(SecurityMaster).count() == 2
            assert session.query(MomentumScore).count() == 2
            assert session.query(PriceHistory).count() == 2

    def test_reuses_existing_security_master(self, service, db):
        _seed_security(db, "NVDA")
        rows = [("NVDA", {"composite_score": 80.0, "current_price": 500.0})]
        service._persist_to_database(rows)

        with db.get_session_context() as session:
            assert session.query(SecurityMaster).filter_by(ticker="NVDA").count() == 1


# ---------------------------------------------------------------------------
# get_batch_scores — full integration
# ---------------------------------------------------------------------------


class TestGetBatchScores:
    def test_all_from_memory(self, service, engine):
        engine._cache["momentum_NVDA"] = (
            {"ticker": "NVDA", "composite_score": 90.0},
            time.time(),
        )
        engine._cache["momentum_AAPL"] = (
            {"ticker": "AAPL", "composite_score": 70.0},
            time.time(),
        )

        data = asyncio.get_event_loop().run_until_complete(
            service.get_batch_scores(["NVDA", "AAPL"])
        )

        assert len(data) == 2
        assert data["NVDA"]["composite_score"] == 90.0
        assert data["AAPL"]["composite_score"] == 70.0

    def test_all_from_database(self, service, db):
        sid = _seed_security(db, "NVDA")
        _seed_score(db, sid, date.today(), composite=85.0)
        _seed_price(db, sid, date.today(), close_price=500.0)

        data = asyncio.get_event_loop().run_until_complete(
            service.get_batch_scores(["NVDA"])
        )

        assert data["NVDA"]["composite_score"] == 85.0
        assert data["NVDA"]["current_price"] == 500.0

    def test_all_from_live(self, service):
        data = asyncio.get_event_loop().run_until_complete(
            service.get_batch_scores(["UNKNOWN"])
        )

        assert "UNKNOWN" in data
        assert data["UNKNOWN"]["composite_score"] == 72.5

    def test_mixed_tiers(self, service, engine, db):
        # Tier 1: NVDA in memory
        engine._cache["momentum_NVDA"] = (
            {"ticker": "NVDA", "composite_score": 95.0},
            time.time(),
        )
        # Tier 2: AAPL in DB
        sid = _seed_security(db, "AAPL")
        _seed_score(db, sid, date.today(), composite=60.0)
        # Tier 3: MSFT → live

        data = asyncio.get_event_loop().run_until_complete(
            service.get_batch_scores(["NVDA", "AAPL", "MSFT"])
        )

        assert data["NVDA"]["composite_score"] == 95.0  # Tier 1
        assert data["AAPL"]["composite_score"] == 60.0  # Tier 2
        assert data["MSFT"]["composite_score"] == 72.5  # Tier 3

    def test_no_db_skips_tier2(self, service_no_db, engine):
        # With no db_config, should go straight from Tier 1 → Tier 3
        data = asyncio.get_event_loop().run_until_complete(
            service_no_db.get_batch_scores(["NVDA"])
        )
        assert "NVDA" in data
        assert data["NVDA"]["composite_score"] == 72.5

    def test_empty_tickers(self, service):
        data = asyncio.get_event_loop().run_until_complete(
            service.get_batch_scores([])
        )
        assert data == {}
