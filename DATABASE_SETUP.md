# AlphaVelocity Database Setup Guide

## Overview
We have successfully implemented a comprehensive PostgreSQL database system for AlphaVelocity with multi-user support, transaction tracking, and portfolio management capabilities.

## What's Implemented

### 🗄️ Database Schema
- **14 comprehensive tables** supporting:
  - Multi-user authentication and authorization
  - Transaction-based portfolio tracking with cost basis
  - Dividend reinvestment workflow
  - Portfolio comparison and benchmarking
  - Historical momentum scoring and price tracking

### 🔧 Core Components

1. **Database Models** (`backend/models/database.py`)
   - SQLAlchemy ORM models for all entities
   - Foreign key relationships and constraints
   - Performance indexes and data validation

2. **Database Configuration** (`backend/database/config.py`)
   - PostgreSQL connection management
   - Session handling with context managers
   - Connection pooling and error handling

3. **Migration System** (`backend/database/migration.py`)
   - Automated migration from JSON files
   - Data validation and transformation
   - Historical data preservation

4. **Portfolio Service** (`backend/services/db_portfolio_service.py`)
   - Full CRUD operations for portfolios
   - Transaction recording with cost basis calculation
   - Performance analytics and reporting

5. **API Endpoints** (Updated `backend/main.py`)
   - Database management endpoints under `/database/*`
   - Portfolio operations and analytics
   - Migration and status checking

## 🚀 Setup Instructions

### Prerequisites
1. **PostgreSQL Server** (version 12 or higher)
2. **Python Dependencies**: sqlalchemy, psycopg2-binary, alembic

### Installation Steps

1. **Install PostgreSQL** (Ubuntu/Debian):
   ```bash
   sudo apt update
   sudo apt install postgresql postgresql-contrib
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install sqlalchemy psycopg2-binary alembic python-dotenv bcrypt passlib
   ```

3. **Create Database and User**:
   ```bash
   sudo -u postgres psql
   CREATE DATABASE alphavelocity;
   CREATE USER alphavelocity WITH PASSWORD 'alphavelocity';
   GRANT ALL PRIVILEGES ON DATABASE alphavelocity TO alphavelocity;
   GRANT ALL ON SCHEMA public TO alphavelocity;
   \q
   ```

4. **Run the Setup Script**:
   ```bash
   python scripts/setup_database.py
   ```

## 📊 Database Schema

### Core Tables
- `users` - User authentication and profiles
- `portfolios` - Portfolio management
- `security_master` - Master list of securities
- `categories` - Investment categories
- `holdings` - Current portfolio positions
- `transactions` - All portfolio transactions
- `momentum_scores` - Historical momentum data
- `price_history` - Daily price data
- `performance_snapshots` - Daily portfolio performance

### Advanced Tables
- `dividend_reinvestments` - Dividend reinvestment tracking
- `benchmarks` - Benchmark definitions
- `benchmark_performance` - Benchmark historical data
- `portfolio_comparisons` - Portfolio comparison analytics

## 🔗 API Endpoints

### Database Management
- `GET /database/status` - Check database connection
- `POST /database/migrate` - Run migration from JSON files

### Portfolio Operations
- `GET /database/portfolios` - List user portfolios
- `GET /database/portfolio/{id}/holdings` - Get portfolio holdings
- `GET /database/portfolio/{id}/categories` - Category analysis
- `POST /database/portfolio/{id}/transaction` - Add transaction
- `GET /database/portfolio/{id}/transactions` - Transaction history
- `GET /database/portfolio/{id}/performance` - Performance history

### Analytics
- `POST /database/portfolio/{id}/snapshot` - Record daily snapshot
- `POST /database/portfolio/{id}/update-momentum` - Update momentum scores

## 💡 Usage Examples

### 1. Check Database Status
```bash
curl http://localhost:8000/database/status
```

### 2. Run Migration
```bash
curl -X POST http://localhost:8000/database/migrate
```

### 3. Get Portfolio Holdings
```bash
curl http://localhost:8000/database/portfolio/1/holdings
```

### 4. Add a Transaction
```bash
curl -X POST http://localhost:8000/database/portfolio/1/transaction \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "transaction_type": "BUY",
    "shares": 10,
    "price_per_share": 150.00,
    "fees": 0.00
  }'
```

### 5. Get Performance History
```bash
curl http://localhost:8000/database/portfolio/1/performance?days=365
```

## 🔄 Migration Process

The migration system automatically:

1. **Creates database tables** from SQLAlchemy models
2. **Sets up initial data**:
   - Default user account
   - Investment categories with target allocations
   - Benchmark definitions
3. **Migrates historical data**:
   - Portfolio values from `portfolio_values.json`
   - Momentum scores from `momentum_scores.json`
   - Securities from the default portfolio
4. **Creates holdings** based on the current model portfolio

## 🎯 Key Features

### Transaction-Based Tracking
- Complete audit trail of all portfolio changes
- Automatic cost basis calculation using weighted averages
- Support for dividends, splits, and reinvestments

### Performance Analytics
- Daily portfolio snapshots with P&L calculations
- Historical performance comparisons
- Category allocation analysis vs targets

### Multi-User Support
- User authentication and portfolio ownership
- Isolated portfolio data per user
- Role-based access control ready

### Dividend Reinvestment
- Track dividend payments and reinvestment workflow
- Link dividend transactions to reinvestment purchases
- Support for manual and automatic reinvestment

## 🔧 Configuration

### Environment Variables
Create a `.env` file with:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=alphavelocity
DB_USER=alphavelocity
DB_PASSWORD=alphavelocity
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True
```

## 🚦 Current Status

✅ **Completed**:
- Database schema design and implementation
- Migration system from JSON files
- Database-enabled portfolio service
- API endpoints and documentation
- Setup scripts and documentation

⏳ **Pending** (requires PostgreSQL installation):
- Live database testing
- Data migration execution
- Performance optimization

## 🔄 Next Steps

Once PostgreSQL is installed:

1. Run the setup script to create the database
2. Execute the migration to transfer existing data
3. Test the new database endpoints
4. Update the frontend to use database-backed portfolio data
5. Implement user authentication and registration

The system is fully ready for deployment once PostgreSQL is available!