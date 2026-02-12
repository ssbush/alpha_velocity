// Read a cookie value by name (used for CSRF double-submit pattern)
function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
}

// AlphaVelocity API Client
class AlphaVelocityAPI {
    constructor(baseURL = (window.ALPHAVELOCITY_API_URL || window.location.origin)) {
        this.baseURL = baseURL;
        this.authManager = null;
    }

    setAuthManager(authManager) {
        this.authManager = authManager;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;

        // Add auth header if available
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.authManager && this.authManager.isLoggedIn()) {
            Object.assign(headers, this.authManager.getAuthHeader());
        }

        // Add CSRF token for state-changing requests
        const method = (options.method || 'GET').toUpperCase();
        if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
            const csrfToken = getCookie('_csrf_token');
            if (csrfToken) {
                headers['X-CSRF-Token'] = csrfToken;
            }
        }

        try {
            const response = await fetch(url, {
                headers,
                ...options
            });

            // Auto-refresh on 401 if we have a refresh token
            if (response.status === 401 && this.authManager && this.authManager.refreshToken) {
                const refreshed = await this.authManager.refreshAccessToken();
                if (refreshed) {
                    // Retry with new token
                    const retryHeaders = {
                        ...headers,
                        ...this.authManager.getAuthHeader(),
                    };
                    // Re-read CSRF token (may have been refreshed by the 401 response)
                    const retryCsrf = getCookie('_csrf_token');
                    if (retryCsrf) {
                        retryHeaders['X-CSRF-Token'] = retryCsrf;
                    }
                    const retryResponse = await fetch(url, {
                        headers: retryHeaders,
                        ...options
                    });
                    if (!retryResponse.ok) {
                        throw new Error(`HTTP error! status: ${retryResponse.status}`);
                    }
                    return await retryResponse.json();
                }
            }

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
        return this.request(`/api/v1/momentum/${ticker.toUpperCase()}`);
    }

    // Get portfolio analysis
    async getPortfolioAnalysis() {
        return this.request('/api/v1/portfolio/analysis');
    }

    // Get portfolio analysis grouped by categories
    async getPortfolioAnalysisByCategories() {
        return this.request('/api/v1/portfolio/analysis/by-categories');
    }

    // Analyze custom portfolio grouped by categories
    async analyzeCustomPortfolioByCategories(portfolio) {
        return this.request('/api/v1/portfolio/analyze/by-categories', {
            method: 'POST',
            body: JSON.stringify({ holdings: portfolio })
        });
    }

    // Get all categories
    async getCategories() {
        return this.request('/api/v1/categories');
    }

    // Get category analysis
    async getCategoryAnalysis(categoryName) {
        const encoded = encodeURIComponent(categoryName);
        return this.request(`/api/v1/categories/${encoded}/analysis`);
    }

    // Category Management API methods
    async getAllCategoriesManagement() {
        return this.request('/categories/management/all');
    }

    async getCategoryDetails(categoryId) {
        return this.request(`/categories/management/${categoryId}`);
    }

    async addTickerToCategory(categoryId, ticker) {
        return this.request(`/categories/management/${categoryId}/tickers?ticker=${ticker}`, {
            method: 'POST'
        });
    }

    async removeTickerFromCategory(categoryId, ticker) {
        return this.request(`/categories/management/${categoryId}/tickers/${ticker}`, {
            method: 'DELETE'
        });
    }

    async createCategory(name, description, targetAllocationPct, benchmarkTicker) {
        return this.request(`/categories/management/create?name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}&target_allocation_pct=${targetAllocationPct}&benchmark_ticker=${benchmarkTicker}`, {
            method: 'POST'
        });
    }

    async updateCategory(categoryId, updates) {
        const params = new URLSearchParams();
        if (updates.name) params.append('name', updates.name);
        if (updates.description) params.append('description', updates.description);
        if (updates.target_allocation_pct !== undefined) params.append('target_allocation_pct', updates.target_allocation_pct);
        if (updates.benchmark_ticker) params.append('benchmark_ticker', updates.benchmark_ticker);

        return this.request(`/categories/management/${categoryId}?${params.toString()}`, {
            method: 'PUT'
        });
    }

    // Get top momentum stocks (supports legacy limit or paginated mode)
    async getTopMomentumStocks(options = {}) {
        // Support legacy call: getTopMomentumStocks(10) or getTopMomentumStocks({limit: 10})
        if (typeof options === 'number') {
            return this.request(`/api/v1/momentum/top/${options}`);
        }
        const { limit, page, pageSize, sortBy, sortOrder } = options;
        if (page !== undefined) {
            const params = new URLSearchParams({ page, page_size: pageSize || 20 });
            if (sortBy) params.append('sort_by', sortBy);
            if (sortOrder) params.append('sort_order', sortOrder);
            return this.request(`/api/v1/momentum/top?${params}`);
        }
        return this.request(`/api/v1/momentum/top/${limit || 10}`);
    }

    // Get category tickers
    async getCategoryTickers(categoryName) {
        const encoded = encodeURIComponent(categoryName);
        return this.request(`/api/v1/categories/${encoded}/tickers`);
    }

    // Get watchlist of potential portfolio additions
    async getWatchlist(minScore = 70.0) {
        return this.request(`/watchlist?min_score=${minScore}`);
    }

    // Analyze custom portfolio
    async analyzeCustomPortfolio(portfolio) {
        return this.request('/api/v1/portfolio/analyze', {
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

    // Get portfolio-specific category targets
    async getPortfolioCategoryTargets(portfolioId) {
        return this.request(`/database/portfolio/${portfolioId}/category-targets`);
    }

    // Set portfolio-specific category target
    async setPortfolioCategoryTarget(portfolioId, categoryId, targetPct) {
        return this.request(`/database/portfolio/${portfolioId}/category-targets?category_id=${categoryId}&target_pct=${targetPct}`, {
            method: 'POST'
        });
    }

    // Reset portfolio to use global defaults
    async resetPortfolioTargets(portfolioId) {
        return this.request(`/database/portfolio/${portfolioId}/reset-targets`, {
            method: 'POST'
        });
    }

    // Get portfolio category analysis from database
    async getPortfolioCategoryAnalysis(portfolioId) {
        return this.request(`/database/portfolio/${portfolioId}/categories`);
    }

    // Get portfolio holdings organized by categories
    async getPortfolioByCategories(portfolioId) {
        return this.request(`/database/portfolio/${portfolioId}/categories-detailed`);
    }

    // Add transaction to portfolio (authenticated)
    async addTransaction(portfolioId, transactionData) {
        const params = new URLSearchParams();
        params.append('ticker', transactionData.ticker);
        params.append('transaction_type', transactionData.transaction_type);
        params.append('shares', transactionData.shares);
        params.append('price_per_share', transactionData.price_per_share);
        params.append('transaction_date', transactionData.transaction_date);
        if (transactionData.fees) params.append('fees', transactionData.fees);
        if (transactionData.notes) params.append('notes', transactionData.notes);

        return this.request(`/user/portfolios/${portfolioId}/transactions?${params}`, {
            method: 'POST'
        });
    }

    // Get transaction history (authenticated, legacy)
    async getTransactionHistory(portfolioId, limit = 50) {
        return this.request(`/user/portfolios/${portfolioId}/transactions?limit=${limit}`);
    }

    // Get transaction history with pagination (authenticated, v1)
    async getTransactionHistoryPaginated(portfolioId, options = {}) {
        const { page = 1, pageSize = 20, sortBy = 'transaction_date', sortOrder = 'desc' } = options;
        const params = new URLSearchParams({
            page,
            page_size: pageSize,
            sort_by: sortBy,
            sort_order: sortOrder
        });
        return this.request(`/api/v1/user/portfolios/${portfolioId}/transactions?${params}`);
    }

    // Delete transaction (authenticated)
    async deleteTransaction(portfolioId, transactionId) {
        return this.request(`/user/portfolios/${portfolioId}/transactions/${transactionId}`, {
            method: 'DELETE'
        });
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