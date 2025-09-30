# AlphaVelocity

AI Supply Chain Momentum Scoring Engine - A systematic approach to momentum-based stock analysis and portfolio management.

## Overview

AlphaVelocity generates comprehensive momentum scores for stocks using multiple factors:
- **Price Momentum (40%)**: Multi-timeframe returns and moving average signals
- **Technical Momentum (25%)**: RSI, volume confirmation, rate of change
- **Fundamental Momentum (25%)**: P/E ratios, growth metrics, analyst ratings
- **Relative Momentum (10%)**: Performance vs. market benchmarks

## Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **PostgreSQL 13+** installed (optional, for database mode)
3. **Git** for cloning the repository

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd alpha_velocity
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

### Running AlphaVelocity

#### Option 1: File Mode (Simplest)
Run the application with file-based storage:

```bash
# Terminal 1: Start the backend server
python -m backend.main

# Terminal 2: Start the frontend server
python frontend_server.py

# Access the application
# Frontend: http://localhost:3000/
# API docs: http://localhost:8000/docs
```

#### Option 2: Database Mode (Recommended)
For full features including portfolio persistence and transaction tracking:

1. **Install and start PostgreSQL**:
```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# On macOS with Homebrew
brew install postgresql
brew services start postgresql

# On Windows, download from: https://www.postgresql.org/download/windows/
```

2. **Setup PostgreSQL database**:
```bash
# Method 1: Use the provided setup script
sudo -u postgres psql -f setup_db.sql

# Method 2: Manual setup
sudo -u postgres psql
# Then run these commands in psql:
# CREATE DATABASE alphavelocity;
# CREATE USER alphavelocity WITH PASSWORD 'alphavelocity_secure_password';
# GRANT ALL PRIVILEGES ON DATABASE alphavelocity TO alphavelocity;
# \q
```

3. **Verify environment variables** (`.env` file should already be configured):
```bash
# Check that .env contains:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=alphavelocity
# DB_USER=alphavelocity
# DB_PASSWORD=alphavelocity_secure_password
```

4. **Test database connection**:
```bash
python -c "
import sys
sys.path.insert(0, 'backend')
from database.config import db_config
print('Testing connection...')
if db_config.test_connection():
    print('✅ Database connection successful')
else:
    print('❌ Database connection failed')
"
```

5. **Run database migration**:
```bash
python simple_db_migration.py
```

6. **Populate initial data**:
```bash
# Setup portfolio categories
python setup_portfolio_categories.py

# Populate market data (optional)
python populate_market_data.py
```

7. **Start the servers**:
```bash
# Terminal 1: Start the backend server
python -m backend.main

# Terminal 2: Start the frontend server
python frontend_server.py
```

#### Accessing the Application

Once both servers are running, you can access:
- **Web Interface**: http://localhost:3000/
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/
- **Portfolio Analysis**: http://localhost:8000/portfolio/analysis
- **Momentum Score**: http://localhost:8000/momentum/NVDA

### Switching from File Mode to Database Mode

If your app is showing "File Mode" in the header, it means PostgreSQL is not running or not accessible. To switch to database mode:

**1. Check if PostgreSQL is running:**
```bash
# Check PostgreSQL service status
sudo systemctl status postgresql    # Linux
brew services list | grep postgresql    # macOS

# If not running, start it:
sudo systemctl start postgresql    # Linux
brew services start postgresql    # macOS
```

**2. Test database connection:**
```bash
python -c "
import sys
sys.path.insert(0, 'backend')
from simple_db_service import get_database_service
db_service = get_database_service()
if db_service.test_connection():
    print('✅ Database ready - restart backend to enable database mode')
else:
    print('❌ Database connection still failing')
"
```

**3. Restart the backend server:**
```bash
# Stop the current backend (Ctrl+C)
# Then restart:
python -m backend.main
```

**4. Refresh the frontend:**
The frontend will automatically detect database mode and show "Database Mode" in the header.

### Database Troubleshooting

#### Common Issues:

**1. PostgreSQL not running:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql    # Linux
brew services list | grep postgresql    # macOS

# Start PostgreSQL
sudo systemctl start postgresql    # Linux
brew services start postgresql    # macOS
```

**2. Connection refused errors:**
```bash
# Check PostgreSQL is listening on correct port
sudo netstat -plunt | grep 5432

# Edit PostgreSQL config if needed
sudo nano /etc/postgresql/*/main/postgresql.conf
# Ensure: listen_addresses = 'localhost'
# Ensure: port = 5432
```

**3. Authentication failed:**
```bash
# Reset PostgreSQL user password
sudo -u postgres psql
# \password alphavelocity
# (enter new password)
# \q

# Update .env file with new password
```

**4. Database doesn't exist:**
```bash
# List databases
sudo -u postgres psql -l

# Recreate database if needed
sudo -u postgres psql -f setup_db.sql
```

**5. Permission denied:**
```bash
# Grant proper permissions
sudo -u postgres psql
# GRANT ALL PRIVILEGES ON DATABASE alphavelocity TO alphavelocity;
# GRANT ALL ON SCHEMA public TO alphavelocity;
# \q
```

### Alternative Server Commands

```bash
# Using uvicorn directly
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Development mode with auto-reload
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

#### Core Endpoints
- `GET /` - Health check
- `GET /momentum/{ticker}` - Get momentum score for a ticker
- `GET /portfolio/analysis` - Analyze default portfolio
- `GET /categories` - List all portfolio categories
- `GET /categories/{name}/analysis` - Analyze specific category
- `GET /momentum/top/{limit}` - Get top momentum stocks

#### Example Response
```json
{
  "ticker": "NVDA",
  "composite_score": 85.2,
  "rating": "Strong Buy",
  "price_momentum": 92.1,
  "technical_momentum": 78.5,
  "fundamental_momentum": 85.0,
  "relative_momentum": 88.3
}
```

## Architecture

```
backend/
├── main.py              # FastAPI application
├── services/            # Business logic
│   ├── momentum_engine.py
│   └── portfolio_service.py
├── models/              # Pydantic data models
├── utils/               # Data providers
└── api/                 # API endpoints (future)
```

## Portfolio Categories

The system organizes investments into 8 strategic categories:

1. **Large-Cap Anchors (20%)** - NVDA, MSFT, META, etc.
2. **Small-Cap Specialists (15%)** - VRT, MOD, BE, etc.
3. **Data Center Infrastructure (15%)** - DLR, SRVR, IRM, etc.
4. **International Tech/Momentum (12%)** - EWJ, EWT, etc.
5. **Tactical Fixed Income (8%)** - SHY, VCIT, etc.
6. **Sector Momentum Rotation (10%)** - XLI, XLE, etc.
7. **Critical Metals & Mining (7%)** - MP, ALB, etc.
8. **Specialized Materials ETFs (5%)** - REMX, LIT, etc.

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Legacy Code
Original implementation files are preserved in `legacy/` directory.

### Next Steps
- Implement Alpha Vantage data provider
- Add mobile app (React Native/Flutter)
- Add user authentication
- Implement portfolio persistence
- Add real-time updates

## API Documentation

When running the server, visit http://localhost:8000/docs for interactive API documentation.