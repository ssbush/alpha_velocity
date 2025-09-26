"""
AlphaVelocity Database Models

SQLAlchemy ORM models for PostgreSQL database supporting:
- Multi-user authentication and authorization
- Transaction-based portfolio tracking with dividend reinvestment
- Portfolio comparison and benchmarking
- Historical momentum score tracking
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, Boolean, Text, ForeignKey, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    """User authentication and profile management"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

class Portfolio(Base):
    """Portfolio management with categories and benchmarks"""
    __tablename__ = 'portfolios'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")
    performance_snapshots = relationship("PerformanceSnapshot", back_populates="portfolio", cascade="all, delete-orphan")
    comparisons_as_base = relationship("PortfolioComparison", foreign_keys="PortfolioComparison.base_portfolio_id", back_populates="base_portfolio")
    comparisons_as_compared = relationship("PortfolioComparison", foreign_keys="PortfolioComparison.compared_portfolio_id", back_populates="compared_portfolio")

    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='unique_portfolio_name_per_user'),
        Index('idx_portfolio_user_active', 'user_id', 'is_active'),
    )

    def __repr__(self):
        return f"<Portfolio(name='{self.name}', user_id={self.user_id})>"

class SecurityMaster(Base):
    """Master list of all securities with static information"""
    __tablename__ = 'security_master'

    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), unique=True, nullable=False)
    company_name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))
    security_type = Column(String(50), nullable=False)  # STOCK, ETF, BOND, etc.
    exchange = Column(String(20))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    holdings = relationship("Holding", back_populates="security")
    transactions = relationship("Transaction", back_populates="security")
    momentum_scores = relationship("MomentumScore", back_populates="security")
    price_history = relationship("PriceHistory", back_populates="security")

    __table_args__ = (
        Index('idx_security_ticker', 'ticker'),
        Index('idx_security_type_active', 'security_type', 'is_active'),
    )

    def __repr__(self):
        return f"<SecurityMaster(ticker='{self.ticker}', company_name='{self.company_name}')>"

class Category(Base):
    """Investment categories for portfolio organization"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    target_allocation_pct = Column(Numeric(5, 2))  # Target allocation percentage
    benchmark_ticker = Column(String(20))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    holdings = relationship("Holding", back_populates="category")

    def __repr__(self):
        return f"<Category(name='{self.name}', target_allocation={self.target_allocation_pct}%)>"

class Holding(Base):
    """Current portfolio holdings with category assignments"""
    __tablename__ = 'holdings'

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    security_id = Column(Integer, ForeignKey('security_master.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    shares = Column(Numeric(15, 6), nullable=False)
    average_cost_basis = Column(Numeric(15, 4))  # Weighted average cost per share
    total_cost_basis = Column(Numeric(15, 2))    # Total amount invested
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
    security = relationship("SecurityMaster", back_populates="holdings")
    category = relationship("Category", back_populates="holdings")

    __table_args__ = (
        UniqueConstraint('portfolio_id', 'security_id', name='unique_holding_per_portfolio'),
        Index('idx_holding_portfolio_category', 'portfolio_id', 'category_id'),
        CheckConstraint('shares >= 0', name='check_shares_non_negative'),
    )

    def __repr__(self):
        return f"<Holding(portfolio_id={self.portfolio_id}, security_id={self.security_id}, shares={self.shares})>"

class Transaction(Base):
    """All portfolio transactions including buys, sells, and dividends"""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    security_id = Column(Integer, ForeignKey('security_master.id'), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # BUY, SELL, DIVIDEND, SPLIT, REINVEST
    transaction_date = Column(Date, nullable=False)
    shares = Column(Numeric(15, 6), nullable=False)  # Can be negative for sells
    price_per_share = Column(Numeric(15, 4))
    total_amount = Column(Numeric(15, 2), nullable=False)  # Total transaction value
    fees = Column(Numeric(10, 2), default=0)
    dividend_rate = Column(Numeric(8, 4))  # For dividend transactions
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")
    security = relationship("SecurityMaster", back_populates="transactions")
    reinvestment = relationship("DividendReinvestment", foreign_keys="DividendReinvestment.dividend_transaction_id", back_populates="dividend_transaction", uselist=False)

    __table_args__ = (
        Index('idx_transaction_portfolio_date', 'portfolio_id', 'transaction_date'),
        Index('idx_transaction_security_date', 'security_id', 'transaction_date'),
        Index('idx_transaction_type_date', 'transaction_type', 'transaction_date'),
        CheckConstraint(
            "transaction_type IN ('BUY', 'SELL', 'DIVIDEND', 'SPLIT', 'REINVEST')",
            name='check_valid_transaction_type'
        ),
    )

    def __repr__(self):
        return f"<Transaction(type='{self.transaction_type}', shares={self.shares}, date={self.transaction_date})>"

class DividendReinvestment(Base):
    """Tracks dividend reinvestment workflow"""
    __tablename__ = 'dividend_reinvestments'

    id = Column(Integer, primary_key=True)
    dividend_transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=False)
    reinvestment_transaction_id = Column(Integer, ForeignKey('transactions.id'))
    dividend_amount = Column(Numeric(15, 2), nullable=False)
    reinvestment_price = Column(Numeric(15, 4))
    reinvestment_shares = Column(Numeric(15, 6))
    reinvestment_date = Column(Date)
    status = Column(String(20), default='PENDING', nullable=False)  # PENDING, COMPLETED, MANUAL
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    dividend_transaction = relationship("Transaction", foreign_keys=[dividend_transaction_id], back_populates="reinvestment")
    reinvestment_transaction = relationship("Transaction", foreign_keys=[reinvestment_transaction_id])

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'COMPLETED', 'MANUAL')",
            name='check_valid_reinvestment_status'
        ),
    )

    def __repr__(self):
        return f"<DividendReinvestment(dividend_amount={self.dividend_amount}, status='{self.status}')>"

class MomentumScore(Base):
    """Historical momentum scores for securities"""
    __tablename__ = 'momentum_scores'

    id = Column(Integer, primary_key=True)
    security_id = Column(Integer, ForeignKey('security_master.id'), nullable=False)
    score_date = Column(Date, nullable=False)
    composite_score = Column(Numeric(5, 2), nullable=False)
    price_momentum = Column(Numeric(5, 2))
    technical_momentum = Column(Numeric(5, 2))
    fundamental_momentum = Column(Numeric(5, 2))
    relative_momentum = Column(Numeric(5, 2))
    rating = Column(String(20))
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    security = relationship("SecurityMaster", back_populates="momentum_scores")

    __table_args__ = (
        UniqueConstraint('security_id', 'score_date', name='unique_momentum_score_per_day'),
        Index('idx_momentum_security_date', 'security_id', 'score_date'),
        Index('idx_momentum_date_score', 'score_date', 'composite_score'),
        CheckConstraint('composite_score >= 0 AND composite_score <= 100', name='check_composite_score_range'),
    )

    def __repr__(self):
        return f"<MomentumScore(security_id={self.security_id}, date={self.score_date}, score={self.composite_score})>"

class PriceHistory(Base):
    """Historical price data for securities"""
    __tablename__ = 'price_history'

    id = Column(Integer, primary_key=True)
    security_id = Column(Integer, ForeignKey('security_master.id'), nullable=False)
    price_date = Column(Date, nullable=False)
    open_price = Column(Numeric(15, 4))
    high_price = Column(Numeric(15, 4))
    low_price = Column(Numeric(15, 4))
    close_price = Column(Numeric(15, 4), nullable=False)
    volume = Column(Integer)
    adjusted_close = Column(Numeric(15, 4))
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    security = relationship("SecurityMaster", back_populates="price_history")

    __table_args__ = (
        UniqueConstraint('security_id', 'price_date', name='unique_price_per_day'),
        Index('idx_price_security_date', 'security_id', 'price_date'),
        Index('idx_price_date', 'price_date'),
        CheckConstraint('close_price > 0', name='check_positive_close_price'),
    )

    def __repr__(self):
        return f"<PriceHistory(security_id={self.security_id}, date={self.price_date}, close={self.close_price})>"

class PerformanceSnapshot(Base):
    """Daily portfolio performance snapshots"""
    __tablename__ = 'performance_snapshots'

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    total_value = Column(Numeric(15, 2), nullable=False)
    total_cost_basis = Column(Numeric(15, 2))
    unrealized_gain_loss = Column(Numeric(15, 2))
    realized_gain_loss = Column(Numeric(15, 2))
    dividend_income = Column(Numeric(15, 2))
    average_momentum_score = Column(Numeric(5, 2))
    number_of_positions = Column(Integer)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="performance_snapshots")

    __table_args__ = (
        UniqueConstraint('portfolio_id', 'snapshot_date', name='unique_snapshot_per_day'),
        Index('idx_performance_portfolio_date', 'portfolio_id', 'snapshot_date'),
        Index('idx_performance_date', 'snapshot_date'),
    )

    def __repr__(self):
        return f"<PerformanceSnapshot(portfolio_id={self.portfolio_id}, date={self.snapshot_date}, value={self.total_value})>"

class Benchmark(Base):
    """Benchmark definitions for portfolio comparison"""
    __tablename__ = 'benchmarks'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    ticker = Column(String(20))  # If benchmark is a tradeable security
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    performance_data = relationship("BenchmarkPerformance", back_populates="benchmark")
    comparisons = relationship("PortfolioComparison", back_populates="benchmark")

    def __repr__(self):
        return f"<Benchmark(name='{self.name}', ticker='{self.ticker}')>"

class BenchmarkPerformance(Base):
    """Historical performance data for benchmarks"""
    __tablename__ = 'benchmark_performance'

    id = Column(Integer, primary_key=True)
    benchmark_id = Column(Integer, ForeignKey('benchmarks.id'), nullable=False)
    performance_date = Column(Date, nullable=False)
    value = Column(Numeric(15, 2), nullable=False)
    return_1d = Column(Numeric(8, 4))
    return_ytd = Column(Numeric(8, 4))
    return_1y = Column(Numeric(8, 4))
    volatility = Column(Numeric(8, 4))
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    benchmark = relationship("Benchmark", back_populates="performance_data")

    __table_args__ = (
        UniqueConstraint('benchmark_id', 'performance_date', name='unique_benchmark_performance_per_day'),
        Index('idx_benchmark_perf_date', 'benchmark_id', 'performance_date'),
    )

    def __repr__(self):
        return f"<BenchmarkPerformance(benchmark_id={self.benchmark_id}, date={self.performance_date}, value={self.value})>"

class PortfolioComparison(Base):
    """Portfolio-to-portfolio and portfolio-to-benchmark comparisons"""
    __tablename__ = 'portfolio_comparisons'

    id = Column(Integer, primary_key=True)
    base_portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    compared_portfolio_id = Column(Integer, ForeignKey('portfolios.id'))
    benchmark_id = Column(Integer, ForeignKey('benchmarks.id'))
    comparison_date = Column(Date, nullable=False)
    base_return = Column(Numeric(8, 4), nullable=False)
    compared_return = Column(Numeric(8, 4))
    benchmark_return = Column(Numeric(8, 4))
    alpha = Column(Numeric(8, 4))  # Excess return vs benchmark
    beta = Column(Numeric(6, 4))   # Correlation with benchmark
    sharpe_ratio = Column(Numeric(6, 4))
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    base_portfolio = relationship("Portfolio", foreign_keys=[base_portfolio_id], back_populates="comparisons_as_base")
    compared_portfolio = relationship("Portfolio", foreign_keys=[compared_portfolio_id], back_populates="comparisons_as_compared")
    benchmark = relationship("Benchmark", back_populates="comparisons")

    __table_args__ = (
        Index('idx_comparison_base_date', 'base_portfolio_id', 'comparison_date'),
        Index('idx_comparison_benchmark_date', 'benchmark_id', 'comparison_date'),
        CheckConstraint(
            "(compared_portfolio_id IS NOT NULL AND benchmark_id IS NULL) OR "
            "(compared_portfolio_id IS NULL AND benchmark_id IS NOT NULL)",
            name='check_comparison_target'
        ),
    )

    def __repr__(self):
        return f"<PortfolioComparison(base={self.base_portfolio_id}, date={self.comparison_date}, alpha={self.alpha})>"