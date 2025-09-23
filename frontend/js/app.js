// AlphaVelocity Frontend Application
class AlphaVelocityApp {
    constructor() {
        this.currentView = 'dashboard';
        this.portfolioMode = 'default'; // 'default' or 'custom'
        this.customPortfolio = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadFromLocalStorage();
        this.loadInitialData();
    }

    setupEventListeners() {
        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.target.dataset.view;
                this.switchView(view);
            });
        });

        // Search functionality
        const searchBtn = document.getElementById('search-btn');
        const tickerInput = document.getElementById('ticker-input');

        searchBtn.addEventListener('click', () => this.searchStock());
        tickerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchStock();
        });

        // Portfolio refresh
        document.getElementById('refresh-portfolio').addEventListener('click', () => {
            this.loadPortfolioData();
        });

        // Watchlist controls
        const minScoreSlider = document.getElementById('min-score-slider');
        const minScoreValue = document.getElementById('min-score-value');
        const refreshWatchlist = document.getElementById('refresh-watchlist');

        minScoreSlider.addEventListener('input', (e) => {
            minScoreValue.textContent = e.target.value;
        });

        minScoreSlider.addEventListener('change', (e) => {
            this.loadWatchlistData();
        });

        refreshWatchlist.addEventListener('click', () => {
            this.loadWatchlistData();
        });

        // Portfolio mode controls
        document.querySelectorAll('.mode-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const mode = e.target.dataset.mode;
                this.switchPortfolioMode(mode);
            });
        });

        // Custom portfolio controls
        document.getElementById('add-holding-btn').addEventListener('click', () => {
            this.addHolding();
        });

        document.getElementById('ticker-input-portfolio').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addHolding();
        });

        document.getElementById('shares-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addHolding();
        });

        document.getElementById('clear-portfolio').addEventListener('click', () => {
            this.clearCustomPortfolio();
        });

        document.getElementById('load-sample').addEventListener('click', () => {
            this.loadSamplePortfolio();
        });

        document.getElementById('analyze-custom').addEventListener('click', () => {
            this.analyzeCustomPortfolio();
        });
    }

    switchView(viewName) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-view="${viewName}"]`).classList.add('active');

        // Update views
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });
        document.getElementById(`${viewName}-view`).classList.add('active');

        this.currentView = viewName;

        // Load data for the view
        switch (viewName) {
            case 'portfolio':
                this.loadPortfolioData();
                break;
            case 'categories':
                this.loadCategoriesData();
                break;
            case 'watchlist':
                this.loadWatchlistData();
                break;
        }
    }

    async loadInitialData() {
        try {
            // Check API health
            await api.getHealth();

            // Load dashboard data
            await Promise.all([
                this.loadPortfolioSummary(),
                this.loadTopMomentum()
            ]);
        } catch (error) {
            this.showError('Failed to connect to API. Please ensure the backend server is running.');
        }
    }

    async loadPortfolioSummary() {
        try {
            const portfolio = await api.getPortfolioAnalysis();

            document.getElementById('total-value').textContent = formatCurrency(portfolio.total_value);
            document.getElementById('avg-score').textContent = formatScore(portfolio.average_momentum_score);
            document.getElementById('positions-count').textContent = portfolio.number_of_positions;
        } catch (error) {
            console.error('Failed to load portfolio summary:', error);
        }
    }

    async loadTopMomentum() {
        const container = document.getElementById('top-momentum-grid');
        const loading = document.getElementById('top-momentum-loading');

        try {
            loading.style.display = 'block';
            const topStocks = await api.getTopMomentumStocks(6);

            container.innerHTML = topStocks.map(stock => `
                <div class="momentum-card">
                    <div class="momentum-header">
                        <span class="ticker">${stock.ticker}</span>
                        <span class="rating" style="color: ${getRatingColor(stock.rating)}">${stock.rating}</span>
                    </div>
                    <div class="momentum-score" style="color: ${getScoreColor(stock.composite_score)}">
                        ${formatScore(stock.composite_score)}
                    </div>
                    <div class="momentum-breakdown">
                        <div class="breakdown-item">
                            <span>Price</span>
                            <span>${formatScore(stock.price_momentum)}</span>
                        </div>
                        <div class="breakdown-item">
                            <span>Technical</span>
                            <span>${formatScore(stock.technical_momentum)}</span>
                        </div>
                    </div>
                </div>
            `).join('');

            loading.style.display = 'none';
        } catch (error) {
            loading.textContent = 'Failed to load momentum data';
            console.error('Failed to load top momentum:', error);
        }
    }

    async loadPortfolioData() {
        const container = document.getElementById('portfolio-table');
        const loading = document.getElementById('portfolio-loading');

        try {
            loading.style.display = 'block';

            // Load both portfolio and categories data
            const [portfolio, categories] = await Promise.all([
                api.getPortfolioAnalysis(),
                api.getCategories()
            ]);

            // Create category mapping
            const categoryMap = {};
            categories.forEach(category => {
                category.tickers.forEach(ticker => {
                    categoryMap[ticker] = {
                        name: category.name,
                        allocation: category.target_allocation,
                        benchmark: category.benchmark
                    };
                });
            });

            // Group holdings by category
            const groupedHoldings = {};
            const ungroupedHoldings = [];

            portfolio.holdings.forEach(holding => {
                const category = categoryMap[holding.ticker];
                if (category) {
                    if (!groupedHoldings[category.name]) {
                        groupedHoldings[category.name] = {
                            info: category,
                            holdings: [],
                            totalValue: 0,
                            avgScore: 0
                        };
                    }
                    groupedHoldings[category.name].holdings.push(holding);

                    // Parse market value for calculations
                    const marketValue = parseFloat(holding.market_value.replace(/[$,]/g, ''));
                    groupedHoldings[category.name].totalValue += marketValue;
                } else {
                    ungroupedHoldings.push(holding);
                }
            });

            // Calculate category averages
            Object.keys(groupedHoldings).forEach(categoryName => {
                const category = groupedHoldings[categoryName];
                const avgScore = category.holdings.reduce((sum, h) => sum + h.momentum_score, 0) / category.holdings.length;
                category.avgScore = avgScore;
            });

            // Sort categories by total value (descending)
            const sortedCategories = Object.entries(groupedHoldings)
                .sort((a, b) => b[1].totalValue - a[1].totalValue);

            let portfolioHTML = '';

            // Render each category
            sortedCategories.forEach(([categoryName, categoryData]) => {
                portfolioHTML += `
                    <div class="portfolio-category">
                        <div class="category-header-portfolio">
                            <h3>${categoryName}</h3>
                            <div class="category-summary">
                                <span class="category-value">${formatCurrency(categoryData.totalValue)}</span>
                                <span class="category-score" style="color: ${getScoreColor(categoryData.avgScore)}">
                                    Avg: ${formatScore(categoryData.avgScore)}
                                </span>
                                <span class="category-allocation">
                                    Target: ${formatPercentage(categoryData.info.allocation * 100)}
                                </span>
                            </div>
                        </div>
                        <table class="category-table">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Shares</th>
                                    <th>Price</th>
                                    <th>Market Value</th>
                                    <th>Portfolio %</th>
                                    <th>Momentum Score</th>
                                    <th>Rating</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${categoryData.holdings.map(holding => `
                                    <tr>
                                        <td class="ticker-cell">${holding.ticker}</td>
                                        <td>${holding.shares}</td>
                                        <td>${holding.price}</td>
                                        <td>${holding.market_value}</td>
                                        <td>${holding.portfolio_percent}</td>
                                        <td class="score-cell" style="color: ${getScoreColor(holding.momentum_score)}">
                                            ${formatScore(holding.momentum_score)}
                                        </td>
                                        <td class="rating-cell" style="color: ${getRatingColor(holding.rating)}">
                                            ${holding.rating}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            });

            // Add ungrouped holdings if any
            if (ungroupedHoldings.length > 0) {
                portfolioHTML += `
                    <div class="portfolio-category">
                        <div class="category-header-portfolio">
                            <h3>Other Holdings</h3>
                        </div>
                        <table class="category-table">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Shares</th>
                                    <th>Price</th>
                                    <th>Market Value</th>
                                    <th>Portfolio %</th>
                                    <th>Momentum Score</th>
                                    <th>Rating</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${ungroupedHoldings.map(holding => `
                                    <tr>
                                        <td class="ticker-cell">${holding.ticker}</td>
                                        <td>${holding.shares}</td>
                                        <td>${holding.price}</td>
                                        <td>${holding.market_value}</td>
                                        <td>${holding.portfolio_percent}</td>
                                        <td class="score-cell" style="color: ${getScoreColor(holding.momentum_score)}">
                                            ${formatScore(holding.momentum_score)}
                                        </td>
                                        <td class="rating-cell" style="color: ${getRatingColor(holding.rating)}">
                                            ${holding.rating}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            }

            container.innerHTML = portfolioHTML;
            loading.style.display = 'none';
        } catch (error) {
            loading.textContent = 'Failed to load portfolio data';
            console.error('Failed to load portfolio:', error);
        }
    }

    async loadCategoriesData() {
        const container = document.getElementById('categories-grid');
        const loading = document.getElementById('categories-loading');

        try {
            loading.style.display = 'block';
            const categories = await api.getCategories();

            container.innerHTML = categories.map(category => `
                <div class="category-card" data-category="${category.name}">
                    <div class="category-header">
                        <h3>${category.name}</h3>
                        <span class="allocation">${formatPercentage(category.target_allocation * 100)}</span>
                    </div>
                    <div class="category-info">
                        <p><strong>Benchmark:</strong> ${category.benchmark}</p>
                        <p><strong>Tickers:</strong> ${category.tickers.length} stocks</p>
                        <div class="ticker-list">
                            ${category.tickers.slice(0, 6).join(', ')}${category.tickers.length > 6 ? '...' : ''}
                        </div>
                    </div>
                    <button class="analyze-btn" onclick="app.analyzCategory('${category.name}')">
                        Analyze Category
                    </button>
                </div>
            `).join('');

            loading.style.display = 'none';
        } catch (error) {
            loading.textContent = 'Failed to load categories';
            console.error('Failed to load categories:', error);
        }
    }

    async analyzCategory(categoryName) {
        try {
            this.showLoading(true);
            const analysis = await api.getCategoryAnalysis(categoryName);

            // Create modal or detailed view for category analysis
            const modalHTML = `
                <div class="modal-overlay" onclick="this.remove()">
                    <div class="modal" onclick="event.stopPropagation()">
                        <div class="modal-header">
                            <h2>${analysis.category}</h2>
                            <button class="close-btn" onclick="this.closest('.modal-overlay').remove()">×</button>
                        </div>
                        <div class="modal-content">
                            <div class="category-stats">
                                <div class="stat">
                                    <span class="stat-label">Target Allocation:</span>
                                    <span class="stat-value">${formatPercentage(analysis.target_allocation * 100)}</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-label">Average Score:</span>
                                    <span class="stat-value" style="color: ${getScoreColor(analysis.average_score)}">${formatScore(analysis.average_score)}</span>
                                </div>
                                <div class="stat">
                                    <span class="stat-label">Benchmark:</span>
                                    <span class="stat-value">${analysis.benchmark}</span>
                                </div>
                            </div>
                            <div class="category-holdings">
                                <h3>Holdings Analysis</h3>
                                <div class="holdings-grid">
                                    ${analysis.momentum_scores.map(stock => `
                                        <div class="holding-card">
                                            <div class="holding-header">
                                                <span class="ticker">${stock.ticker}</span>
                                                <span class="rating" style="color: ${getRatingColor(stock.rating)}">${stock.rating}</span>
                                            </div>
                                            <div class="holding-score" style="color: ${getScoreColor(stock.composite_score)}">
                                                ${formatScore(stock.composite_score)}
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);
            this.showLoading(false);
        } catch (error) {
            this.showError(`Failed to analyze category: ${categoryName}`);
            this.showLoading(false);
        }
    }

    async searchStock() {
        const ticker = document.getElementById('ticker-input').value.trim().toUpperCase();
        const resultsContainer = document.getElementById('search-results');

        if (!ticker) {
            this.showError('Please enter a ticker symbol');
            return;
        }

        try {
            resultsContainer.innerHTML = '<div class="loading">Analyzing...</div>';
            const result = await api.getMomentumScore(ticker);

            const resultHTML = `
                <div class="stock-analysis">
                    <div class="stock-header">
                        <h2>${result.ticker}</h2>
                        <div class="stock-rating" style="color: ${getRatingColor(result.rating)}">
                            ${result.rating}
                        </div>
                    </div>
                    <div class="score-breakdown">
                        <div class="main-score" style="color: ${getScoreColor(result.composite_score)}">
                            <span class="score-value">${formatScore(result.composite_score)}</span>
                            <span class="score-label">Composite Score</span>
                        </div>
                        <div class="component-scores">
                            <div class="component">
                                <span class="component-label">Price Momentum (40%)</span>
                                <span class="component-value" style="color: ${getScoreColor(result.price_momentum)}">${formatScore(result.price_momentum)}</span>
                            </div>
                            <div class="component">
                                <span class="component-label">Technical Momentum (25%)</span>
                                <span class="component-value" style="color: ${getScoreColor(result.technical_momentum)}">${formatScore(result.technical_momentum)}</span>
                            </div>
                            <div class="component">
                                <span class="component-label">Fundamental Momentum (25%)</span>
                                <span class="component-value" style="color: ${getScoreColor(result.fundamental_momentum)}">${formatScore(result.fundamental_momentum)}</span>
                            </div>
                            <div class="component">
                                <span class="component-label">Relative Momentum (10%)</span>
                                <span class="component-value" style="color: ${getScoreColor(result.relative_momentum)}">${formatScore(result.relative_momentum)}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            resultsContainer.innerHTML = resultHTML;
        } catch (error) {
            resultsContainer.innerHTML = `<div class="error">Failed to analyze ${ticker}. Please check the ticker symbol.</div>`;
        }
    }

    async loadWatchlistData() {
        const summaryContainer = document.getElementById('watchlist-summary');
        const categoriesContainer = document.getElementById('watchlist-categories');
        const minScore = document.getElementById('min-score-slider').value;

        try {
            summaryContainer.innerHTML = '<div class="loading">Loading watchlist...</div>';
            categoriesContainer.innerHTML = '';

            const watchlist = await api.getWatchlist(minScore);

            // Summary section
            const summaryHTML = `
                <div class="watchlist-summary-stats">
                    <div class="summary-card">
                        <div class="summary-value">${watchlist.summary.total_candidates}</div>
                        <div class="summary-label">Total Candidates</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-value">${watchlist.summary.high_priority_categories.length}</div>
                        <div class="summary-label">High Priority Categories</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-value">${watchlist.summary.current_positions}</div>
                        <div class="summary-label">Current Positions</div>
                    </div>
                    <div class="summary-card">
                        <div class="summary-value">${watchlist.summary.recommended_additions}</div>
                        <div class="summary-label">Recommended Additions</div>
                    </div>
                </div>
                ${watchlist.summary.high_priority_categories.length > 0 ? `
                    <div class="priority-alert">
                        <h3>🎯 High Priority Categories</h3>
                        <p>Consider adding positions in: ${watchlist.summary.high_priority_categories.join(', ')}</p>
                    </div>
                ` : ''}
            `;

            summaryContainer.innerHTML = summaryHTML;

            // Categories section
            const categoriesHTML = Object.entries(watchlist.categories)
                .sort((a, b) => {
                    // Sort by priority (High > Medium > Low), then by allocation gap
                    const priorityOrder = { 'High': 3, 'Medium': 2, 'Low': 1 };
                    const priorityDiff = priorityOrder[b[1].priority] - priorityOrder[a[1].priority];
                    if (priorityDiff !== 0) return priorityDiff;
                    return b[1].allocation_gap - a[1].allocation_gap;
                })
                .map(([categoryName, categoryData]) => `
                    <div class="watchlist-category ${categoryData.priority.toLowerCase()}-priority">
                        <div class="watchlist-category-header">
                            <div class="category-info">
                                <h3>${categoryName}</h3>
                                <span class="priority-badge ${categoryData.priority.toLowerCase()}">${categoryData.priority} Priority</span>
                            </div>
                            <div class="allocation-info">
                                <div class="allocation-item">
                                    <span>Target: ${formatPercentage(categoryData.target_allocation * 100)}</span>
                                </div>
                                <div class="allocation-item">
                                    <span>Current: ${formatPercentage(categoryData.current_allocation * 100)}</span>
                                </div>
                                <div class="allocation-item">
                                    <span class="gap ${categoryData.allocation_gap > 0 ? 'positive' : 'negative'}">
                                        Gap: ${categoryData.allocation_gap > 0 ? '+' : ''}${formatPercentage(categoryData.allocation_gap * 100)}
                                    </span>
                                </div>
                            </div>
                        </div>
                        ${categoryData.candidates.length > 0 ? `
                            <div class="watchlist-candidates">
                                <h4>Top Candidates (${categoryData.total_candidates} total)</h4>
                                <div class="candidates-grid">
                                    ${categoryData.candidates.map(candidate => `
                                        <div class="candidate-card">
                                            <div class="candidate-header">
                                                <span class="ticker">${candidate.ticker}</span>
                                                <span class="rating" style="color: ${getRatingColor(candidate.rating)}">${candidate.rating}</span>
                                            </div>
                                            <div class="candidate-score" style="color: ${getScoreColor(candidate.composite_score)}">
                                                ${formatScore(candidate.composite_score)}
                                            </div>
                                            <div class="candidate-breakdown">
                                                <div class="breakdown-item">
                                                    <span>Price</span>
                                                    <span>${formatScore(candidate.price_momentum)}</span>
                                                </div>
                                                <div class="breakdown-item">
                                                    <span>Technical</span>
                                                    <span>${formatScore(candidate.technical_momentum)}</span>
                                                </div>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        ` : `
                            <div class="no-candidates">
                                <p>No candidates meet the minimum score threshold of ${minScore}</p>
                            </div>
                        `}
                    </div>
                `).join('');

            categoriesContainer.innerHTML = categoriesHTML;

        } catch (error) {
            summaryContainer.innerHTML = '<div class="error">Failed to load watchlist data</div>';
            console.error('Failed to load watchlist:', error);
        }
    }

    switchPortfolioMode(mode) {
        this.portfolioMode = mode;

        // Update tab styling
        document.querySelectorAll('.mode-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

        // Show/hide custom portfolio input
        const customInput = document.getElementById('custom-portfolio-input');
        if (mode === 'custom') {
            customInput.style.display = 'block';
            this.renderCustomPortfolio();
        } else {
            customInput.style.display = 'none';
            this.loadPortfolioData(); // Load default portfolio
        }
    }

    addHolding() {
        const tickerInput = document.getElementById('ticker-input-portfolio');
        const sharesInput = document.getElementById('shares-input');

        const ticker = tickerInput.value.trim().toUpperCase();
        const shares = parseInt(sharesInput.value);

        if (!ticker) {
            this.showError('Please enter a ticker symbol');
            return;
        }

        if (!shares || shares <= 0) {
            this.showError('Please enter a valid number of shares');
            return;
        }

        // Add to custom portfolio
        this.customPortfolio[ticker] = shares;

        // Clear inputs
        tickerInput.value = '';
        sharesInput.value = '';

        // Update display
        this.renderCustomPortfolio();
        this.saveToLocalStorage();
    }

    removeHolding(ticker) {
        delete this.customPortfolio[ticker];
        this.renderCustomPortfolio();
        this.saveToLocalStorage();
    }

    clearCustomPortfolio() {
        this.customPortfolio = {};
        this.renderCustomPortfolio();
        this.saveToLocalStorage();
    }

    loadSamplePortfolio() {
        this.customPortfolio = {
            'AAPL': 100,
            'MSFT': 50,
            'GOOGL': 25,
            'NVDA': 30,
            'TSLA': 20
        };
        this.renderCustomPortfolio();
        this.saveToLocalStorage();
    }

    renderCustomPortfolio() {
        const container = document.getElementById('holdings-list');

        if (Object.keys(this.customPortfolio).length === 0) {
            container.innerHTML = '<div class="empty-portfolio">No holdings added yet. Enter a ticker and shares above.</div>';
            return;
        }

        const holdingsHTML = Object.entries(this.customPortfolio).map(([ticker, shares]) => `
            <div class="holding-item">
                <span class="holding-ticker">${ticker}</span>
                <span class="holding-shares">${shares} shares</span>
                <button class="remove-holding" onclick="app.removeHolding('${ticker}')">×</button>
            </div>
        `).join('');

        container.innerHTML = holdingsHTML;
    }

    async analyzeCustomPortfolio() {
        if (Object.keys(this.customPortfolio).length === 0) {
            this.showError('Please add some holdings to analyze');
            return;
        }

        try {
            this.showLoading(true);
            const analysis = await api.analyzeCustomPortfolio(this.customPortfolio);

            // Update the portfolio display with custom data
            this.displayPortfolioAnalysis(analysis);
            this.showLoading(false);
        } catch (error) {
            this.showError('Failed to analyze custom portfolio');
            this.showLoading(false);
        }
    }

    displayPortfolioAnalysis(analysis) {
        const container = document.getElementById('portfolio-table');

        // Group by categories for custom portfolios too
        const portfolioHTML = `
            <div class="portfolio-summary">
                <div class="summary-stats">
                    <div class="stat">
                        <span class="stat-label">Total Value:</span>
                        <span class="stat-value">${formatCurrency(analysis.total_value)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Average Score:</span>
                        <span class="stat-value" style="color: ${getScoreColor(analysis.average_momentum_score)}">${formatScore(analysis.average_momentum_score)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Positions:</span>
                        <span class="stat-value">${analysis.number_of_positions}</span>
                    </div>
                </div>
            </div>
            <div class="simple-portfolio-table">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Shares</th>
                            <th>Price</th>
                            <th>Market Value</th>
                            <th>Portfolio %</th>
                            <th>Momentum Score</th>
                            <th>Rating</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${analysis.holdings.map(holding => `
                            <tr>
                                <td class="ticker-cell">${holding.ticker}</td>
                                <td>${holding.shares}</td>
                                <td>${holding.price}</td>
                                <td>${holding.market_value}</td>
                                <td>${holding.portfolio_percent}</td>
                                <td class="score-cell" style="color: ${getScoreColor(holding.momentum_score)}">
                                    ${formatScore(holding.momentum_score)}
                                </td>
                                <td class="rating-cell" style="color: ${getRatingColor(holding.rating)}">
                                    ${holding.rating}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = portfolioHTML;
    }

    saveToLocalStorage() {
        localStorage.setItem('alphaVelocityCustomPortfolio', JSON.stringify(this.customPortfolio));
    }

    loadFromLocalStorage() {
        const saved = localStorage.getItem('alphaVelocityCustomPortfolio');
        if (saved) {
            this.customPortfolio = JSON.parse(saved);
        }
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = show ? 'flex' : 'none';
    }

    showError(message) {
        // Simple error display - could be enhanced with a proper notification system
        alert(message);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AlphaVelocityApp();
});