// AlphaVelocity API Client
class AlphaVelocityAPI {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;

        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    // Get API health status
    async getHealth() {
        return this.request('/');
    }

    // Get momentum score for a ticker
    async getMomentumScore(ticker) {
        return this.request(`/momentum/${ticker.toUpperCase()}`);
    }

    // Get portfolio analysis
    async getPortfolioAnalysis() {
        return this.request('/portfolio/analysis');
    }

    // Get all categories
    async getCategories() {
        return this.request('/categories');
    }

    // Get category analysis
    async getCategoryAnalysis(categoryName) {
        const encoded = encodeURIComponent(categoryName);
        return this.request(`/categories/${encoded}/analysis`);
    }

    // Get top momentum stocks
    async getTopMomentumStocks(limit = 10) {
        return this.request(`/momentum/top/${limit}`);
    }

    // Get category tickers
    async getCategoryTickers(categoryName) {
        const encoded = encodeURIComponent(categoryName);
        return this.request(`/categories/${encoded}/tickers`);
    }

    // Get watchlist of potential portfolio additions
    async getWatchlist(minScore = 70.0) {
        return this.request(`/watchlist?min_score=${minScore}`);
    }

    // Analyze custom portfolio
    async analyzeCustomPortfolio(portfolio) {
        return this.request('/portfolio/analyze', {
            method: 'POST',
            body: JSON.stringify({ holdings: portfolio })
        });
    }

    // ========================================
    // DATABASE ENDPOINTS
    // ========================================

    // Get database status
    async getDatabaseStatus() {
        return this.request('/database/status');
    }

    // Get user portfolios from database
    async getUserPortfolios(userId = 1) {
        return this.request(`/database/portfolios?user_id=${userId}`);
    }

    // Get portfolio holdings from database
    async getPortfolioHoldings(portfolioId) {
        return this.request(`/database/portfolio/${portfolioId}/holdings`);
    }

    // Get portfolio category analysis from database
    async getPortfolioCategoryAnalysis(portfolioId) {
        return this.request(`/database/portfolio/${portfolioId}/categories`);
    }

    // Get portfolio holdings organized by categories
    async getPortfolioByCategories(portfolioId) {
        return this.request(`/database/portfolio/${portfolioId}/categories-detailed`);
    }

    // Add transaction to portfolio
    async addTransaction(portfolioId, transactionData) {
        return this.request(`/database/portfolio/${portfolioId}/transaction`, {
            method: 'POST',
            body: JSON.stringify(transactionData)
        });
    }

    // Get transaction history
    async getTransactionHistory(portfolioId, limit = 50) {
        return this.request(`/database/portfolio/${portfolioId}/transactions?limit=${limit}`);
    }

    // Run database migration
    async runDatabaseMigration() {
        return this.request('/database/migrate', {
            method: 'POST'
        });
    }

    // Get watchlist for custom portfolio
    async getCustomWatchlist(portfolio, minScore = 70.0) {
        return this.request(`/watchlist/custom?min_score=${minScore}`, {
            method: 'POST',
            body: JSON.stringify({ holdings: portfolio })
        });
    }

    // Compare portfolios
    async comparePortfolios(portfolio) {
        return this.request('/compare/portfolios', {
            method: 'POST',
            body: JSON.stringify({ holdings: portfolio })
        });
    }
}

// Utility functions for data formatting
const formatCurrency = (value) => {
    if (typeof value === 'string') {
        // If already formatted, return as is
        if (value.includes('$')) return value;
        value = parseFloat(value.replace(/[,$]/g, ''));
    }

    if (value >= 1000000) {
        return `$${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
        return `$${(value / 1000).toFixed(1)}K`;
    } else {
        return `$${value.toFixed(2)}`;
    }
};

const formatPercentage = (value) => {
    if (typeof value === 'string' && value.includes('%')) {
        return value;
    }
    return `${parseFloat(value).toFixed(1)}%`;
};

const formatScore = (score) => {
    return parseFloat(score).toFixed(1);
};

const getRatingColor = (rating) => {
    const colors = {
        'Strong Buy': '#10b981',
        'Buy': '#3b82f6',
        'Hold': '#f59e0b',
        'Weak Hold': '#ef4444',
        'Sell': '#dc2626'
    };
    return colors[rating] || '#6b7280';
};

const getScoreColor = (score) => {
    if (score >= 80) return '#10b981'; // Green
    if (score >= 70) return '#3b82f6'; // Blue
    if (score >= 60) return '#f59e0b'; // Yellow
    if (score >= 50) return '#ef4444'; // Orange
    return '#dc2626'; // Red
};

// Export API instance
const api = new AlphaVelocityAPI();