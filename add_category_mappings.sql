-- Create table for mapping securities to categories
CREATE TABLE IF NOT EXISTS category_securities (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    security_id INTEGER NOT NULL REFERENCES security_master(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    created_by INTEGER,
    UNIQUE(category_id, security_id)
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_category_securities_category ON category_securities(category_id);
CREATE INDEX IF NOT EXISTS idx_category_securities_security ON category_securities(security_id);
CREATE INDEX IF NOT EXISTS idx_category_securities_ticker ON category_securities(ticker);

-- Insert initial category-ticker mappings based on hardcoded portfolio structure
-- Large-Cap Anchors (category_id = 1)
INSERT INTO category_securities (category_id, ticker, security_id)
SELECT 1, ticker, id FROM security_master
WHERE ticker IN ('NVDA', 'TSM', 'ASML', 'AVGO', 'MSFT', 'META', 'AAPL', 'AMD', 'GOOGL', 'TSLA', 'PLTR', 'CSCO', 'CRWV', 'ORCL', 'DT', 'AUR', 'MBLY', 'NOW')
ON CONFLICT (category_id, security_id) DO NOTHING;

-- Small-Cap Specialists (category_id = 2)
INSERT INTO category_securities (category_id, ticker, security_id)
SELECT 2, ticker, id FROM security_master
WHERE ticker IN ('VRT', 'MOD', 'BE', 'CIEN', 'ATKR', 'UI', 'APLD', 'SMCI', 'GDS', 'VNET')
ON CONFLICT (category_id, security_id) DO NOTHING;

-- Data Center Infrastructure (category_id = 3)
INSERT INTO category_securities (category_id, ticker, security_id)
SELECT 3, ticker, id FROM security_master
WHERE ticker IN ('SRVR', 'DLR', 'EQIX', 'AMT', 'CCI', 'COR', 'IRM', 'ACM', 'JCI', 'IDGT', 'DTCR')
ON CONFLICT (category_id, security_id) DO NOTHING;

-- International Tech/Momentum (category_id = 4)
INSERT INTO category_securities (category_id, ticker, security_id)
SELECT 4, ticker, id FROM security_master
WHERE ticker IN ('EWJ', 'EWT', 'INDA', 'EWY')
ON CONFLICT (category_id, security_id) DO NOTHING;

-- Tactical Fixed Income (category_id = 5)
INSERT INTO category_securities (category_id, ticker, security_id)
SELECT 5, ticker, id FROM security_master
WHERE ticker IN ('SHY', 'VCIT', 'IPE')
ON CONFLICT (category_id, security_id) DO NOTHING;

-- Sector Momentum Rotation (category_id = 6 - need to insert category first)
INSERT INTO categories (name, description, target_allocation_pct, benchmark_ticker, is_active, created_at)
VALUES ('Sector Momentum Rotation', 'Sector rotation based on momentum signals', 10.00, 'SPY', true, NOW())
ON CONFLICT (name) DO NOTHING;

INSERT INTO category_securities (category_id, ticker, security_id)
SELECT c.id, sm.ticker, sm.id
FROM security_master sm
CROSS JOIN categories c
WHERE sm.ticker IN ('XLE', 'XLF', 'XLI', 'XLU', 'XLB')
AND c.name = 'Sector Momentum Rotation'
ON CONFLICT (category_id, security_id) DO NOTHING;

-- Critical Metals & Mining (category_id = 7)
INSERT INTO categories (name, description, target_allocation_pct, benchmark_ticker, is_active, created_at)
VALUES ('Critical Metals & Mining', 'Rare earth and critical metals mining companies', 7.00, 'XLB', true, NOW())
ON CONFLICT (name) DO NOTHING;

INSERT INTO category_securities (category_id, ticker, security_id)
SELECT c.id, sm.ticker, sm.id
FROM security_master sm
CROSS JOIN categories c
WHERE sm.ticker IN ('MP', 'LYC', 'ARA', 'ALB', 'SQM', 'LAC', 'FCX', 'SCCO', 'TECK')
AND c.name = 'Critical Metals & Mining'
ON CONFLICT (category_id, security_id) DO NOTHING;

-- Specialized Materials ETFs (category_id = 8)
INSERT INTO categories (name, description, target_allocation_pct, benchmark_ticker, is_active, created_at)
VALUES ('Specialized Materials ETFs', 'ETFs focused on specialized materials and metals', 5.00, 'XLB', true, NOW())
ON CONFLICT (name) DO NOTHING;

INSERT INTO category_securities (category_id, ticker, security_id)
SELECT c.id, sm.ticker, sm.id
FROM security_master sm
CROSS JOIN categories c
WHERE sm.ticker IN ('REMX', 'LIT', 'XMET')
AND c.name = 'Specialized Materials ETFs'
ON CONFLICT (category_id, security_id) DO NOTHING;
