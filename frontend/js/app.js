// AlphaVelocity Frontend Application
class AlphaVelocityApp {
    constructor() {
        this.currentView = 'dashboard';
        this.portfolioMode = 'default'; // 'default' or 'custom'
        this.databaseMode = false; // Enable database-backed portfolio management
        this.currentPortfolioId = 1; // Default portfolio ID for database mode
        this.customPortfolio = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupMobileOptimizations();
        this.loadFromLocalStorage();
        this.loadInitialData();
        this.setupPWA();
    }

    setupMobileOptimizations() {
        // Prevent zoom on input focus for iOS
        this.preventIOSZoom();

        // Add touch-friendly interactions
        this.setupTouchInteractions();

        // Handle orientation changes
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleOrientationChange();
            }, 100);
        });

        // Optimize scroll performance on mobile
        this.optimizeScrolling();
    }

    preventIOSZoom() {
        // Ensure all inputs have font-size 16px to prevent zoom
        const inputs = document.querySelectorAll('input[type="text"], input[type="number"]');
        inputs.forEach(input => {
            if (window.innerWidth <= 768) {
                input.style.fontSize = '16px';
            }
        });
    }

    setupTouchInteractions() {
        // Add haptic feedback simulation for touch devices
        if ('ontouchstart' in window) {
            document.querySelectorAll('button, .nav-btn').forEach(element => {
                element.addEventListener('touchstart', function() {
                    this.style.transform = 'scale(0.98)';
                }, { passive: true });

                element.addEventListener('touchend', function() {
                    this.style.transform = 'scale(1)';
                }, { passive: true });
            });
        }
    }

    handleOrientationChange() {
        // Refresh layout after orientation change
        const currentView = document.querySelector('.view.active');
        if (currentView) {
            // Force a reflow to handle any layout issues
            currentView.style.display = 'none';
            currentView.offsetHeight; // Trigger reflow
            currentView.style.display = 'block';
        }
    }

    optimizeScrolling() {
        // Add smooth scrolling for mobile
        document.documentElement.style.scrollBehavior = 'smooth';

        // Optimize table scrolling on mobile
        const tables = document.querySelectorAll('.data-table, .category-table');
        tables.forEach(table => {
            const container = table.parentElement;
            if (container && window.innerWidth <= 768) {
                container.style.webkitOverflowScrolling = 'touch';
            }
        });
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

        // Portfolio comparison controls
        this.setupComparisonControls();
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
            case 'compare':
                this.setupComparisonView();
                break;
        }
    }

    async loadInitialData() {
        try {
            // Check API health
            await api.getHealth();

            // Check database availability
            await this.checkDatabaseMode();

            // Load dashboard data
            await Promise.all([
                this.loadPortfolioSummary(),
                this.loadTopMomentum(),
                this.loadTrendChart()
            ]);
        } catch (error) {
            this.showError('Failed to connect to API. Please ensure the backend server is running.');
        }
    }

    async checkDatabaseMode() {
        try {
            const dbStatus = await api.getDatabaseStatus();
            this.databaseMode = dbStatus.available && dbStatus.connected;

            if (this.databaseMode) {
                console.log('✅ Database mode enabled - using PostgreSQL backend');
                this.showDatabaseStatus(true);
            } else {
                console.log('📄 Using file-based portfolio management');
                this.showDatabaseStatus(false);
            }
        } catch (error) {
            console.log('📄 Database not available, using file-based mode');
            this.databaseMode = false;
            this.showDatabaseStatus(false);
        }
    }

    showDatabaseStatus(enabled) {
        // Update status indicator in the header
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');

        if (statusIndicator && statusText) {
            if (enabled) {
                statusIndicator.classList.add('connected');
                statusText.textContent = 'Database Mode';
            } else {
                statusIndicator.classList.remove('connected');
                statusText.textContent = 'File Mode';
            }
        }
    }

    async loadPortfolioSummary() {
        try {
            let portfolio;

            if (this.databaseMode) {
                // Use database-backed portfolio data
                const holdings = await api.getPortfolioHoldings(this.currentPortfolioId);

                // Calculate summary from database holdings
                portfolio = this.calculatePortfolioSummary(holdings.holdings);

                console.log('📊 Loaded portfolio from database:', holdings.holdings.length, 'holdings');
            } else {
                // Use file-based portfolio analysis
                portfolio = await api.getPortfolioAnalysis();
                console.log('📊 Loaded portfolio from files');
            }

            document.getElementById('total-value').textContent = formatCurrency(portfolio.total_value || 0);
            document.getElementById('avg-score').textContent = formatScore(portfolio.average_momentum_score || 0);
            document.getElementById('positions-count').textContent = portfolio.number_of_positions || 0;
        } catch (error) {
            console.error('Failed to load portfolio summary:', error);
        }
    }

    calculatePortfolioSummary(holdings) {
        if (!holdings || holdings.length === 0) {
            return {
                total_value: 0,
                average_momentum_score: 0,
                number_of_positions: 0
            };
        }

        // Calculate real portfolio values from database holdings
        let totalValue = 0;
        let totalCostBasis = 0;

        for (const holding of holdings) {
            if (holding.total_cost_basis) {
                totalCostBasis += parseFloat(holding.total_cost_basis);

                // If we have current market data, use it. Otherwise use cost basis as estimate
                if (holding.current_value) {
                    totalValue += parseFloat(holding.current_value);
                } else {
                    // Estimate current value as 10% more than cost basis (placeholder)
                    totalValue += parseFloat(holding.total_cost_basis) * 1.1;
                }
            }
        }

        // Use placeholder momentum score for now (could be enhanced to fetch real scores)
        const averageMomentumScore = 72.5;

        return {
            total_value: totalValue,
            total_cost_basis: totalCostBasis,
            average_momentum_score: averageMomentumScore,
            number_of_positions: holdings.length
        };
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

    async loadTrendChart() {
        try {
            // Create trend chart with sample data
            chartManager.createTrendChart('trend-chart');
        } catch (error) {
            console.error('Failed to load trend chart:', error);
        }
    }

    async loadPortfolioData() {
        const container = document.getElementById('portfolio-table');
        const loading = document.getElementById('portfolio-loading');

        try {
            loading.style.display = 'block';

            if (this.databaseMode) {
                // Use database categorized portfolio data
                await this.loadDatabasePortfolioData(container, loading);
                return;
            }

            // Load both portfolio and categories data (file mode)
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
                                        <td class="data-cell">${holding.shares}</td>
                                        <td class="data-cell">${holding.price}</td>
                                        <td class="data-cell">${holding.market_value}</td>
                                        <td class="data-cell">${holding.portfolio_percent}</td>
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
                                        <td class="data-cell">${holding.shares}</td>
                                        <td class="data-cell">${holding.price}</td>
                                        <td class="data-cell">${holding.market_value}</td>
                                        <td class="data-cell">${holding.portfolio_percent}</td>
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

            // Show and render charts
            const chartsSection = document.getElementById('portfolio-charts');
            chartsSection.style.display = 'block';

            // Create allocation chart
            chartManager.createAllocationChart('allocation-chart', portfolio);

            // Create momentum chart
            chartManager.createMomentumChart('momentum-chart', portfolio.holdings);

            // Load and display performance analytics
            this.loadPerformanceAnalytics('default');

            // Cache portfolio data for offline use
            this.cachePortfolioData(portfolio);

            loading.style.display = 'none';
        } catch (error) {
            loading.textContent = 'Failed to load portfolio data';
            console.error('Failed to load portfolio:', error);
        }
    }

    async loadDatabasePortfolioData(container, loading) {
        try {
            // Load categorized portfolio data from database
            const portfolioData = await api.getPortfolioByCategories(this.currentPortfolioId);

            let portfolioHTML = `
                <div class="portfolio-summary-db">
                    <div class="summary-stats">
                        <div class="stat">
                            <span class="stat-label">Total Portfolio Value:</span>
                            <span class="stat-value">${formatCurrency(portfolioData.total_portfolio_value)}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Categories:</span>
                            <span class="stat-value">${portfolioData.total_categories}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Total Positions:</span>
                            <span class="stat-value">${portfolioData.total_positions}</span>
                        </div>
                    </div>
                </div>
            `;

            // Render each category
            portfolioData.categories.forEach(category => {
                const avgScore = category.holdings.length > 0 ?
                    category.holdings.reduce((sum, h) => sum + (h.momentum_score || 70), 0) / category.holdings.length : 70;

                portfolioHTML += `
                    <div class="portfolio-category">
                        <div class="category-header-portfolio">
                            <h3>${category.category_name}</h3>
                            <div class="category-summary">
                                <span class="category-value">${formatCurrency(category.total_value)}</span>
                                <span class="category-allocation">Target: ${formatPercentage(category.target_allocation_pct)}%</span>
                                <span class="category-benchmark">Benchmark: ${category.benchmark_ticker || 'N/A'}</span>
                                <span class="category-positions">${category.position_count} positions</span>
                            </div>
                            <div class="category-description">${category.description || ''}</div>
                        </div>
                        <table class="category-table">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Company</th>
                                    <th>Sector</th>
                                    <th>Shares</th>
                                    <th>Avg Cost</th>
                                    <th>Total Cost</th>
                                    <th>Current Value</th>
                                    <th>Gain/Loss</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${category.holdings.map(holding => {
                                    const gainLoss = holding.current_value - holding.total_cost_basis;
                                    const gainLossPercent = holding.total_cost_basis > 0 ?
                                        ((gainLoss / holding.total_cost_basis) * 100) : 0;
                                    const gainLossColor = gainLoss >= 0 ? '#10b981' : '#ef4444';

                                    return `
                                        <tr>
                                            <td class="ticker-cell">
                                                <strong>${holding.ticker}</strong>
                                            </td>
                                            <td class="company-cell">${holding.company_name}</td>
                                            <td class="sector-cell">${holding.sector || 'N/A'}</td>
                                            <td class="data-cell">${holding.shares.toFixed(2)}</td>
                                            <td class="data-cell">${formatCurrency(holding.average_cost_basis)}</td>
                                            <td class="data-cell">${formatCurrency(holding.total_cost_basis)}</td>
                                            <td class="data-cell"><strong>${formatCurrency(holding.current_value)}</strong></td>
                                            <td style="color: ${gainLossColor}">
                                                ${formatCurrency(gainLoss)} (${gainLossPercent.toFixed(1)}%)
                                            </td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            });

            container.innerHTML = portfolioHTML;
            loading.style.display = 'none';

        } catch (error) {
            console.error('Failed to load database portfolio data:', error);
            container.innerHTML = '<div class="error">Failed to load portfolio data from database</div>';
            loading.style.display = 'none';
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
                                <td class="data-cell">${holding.shares}</td>
                                <td class="data-cell">${holding.price}</td>
                                <td class="data-cell">${holding.market_value}</td>
                                <td class="data-cell">${holding.portfolio_percent}</td>
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

        // Show and render charts for custom portfolio
        const chartsSection = document.getElementById('portfolio-charts');
        chartsSection.style.display = 'block';

        // Create allocation chart
        chartManager.createAllocationChart('allocation-chart', analysis);

        // Create momentum chart
        chartManager.createMomentumChart('momentum-chart', analysis.holdings);
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

    setupPWA() {
        // Register service worker
        this.registerServiceWorker();

        // Setup PWA installation
        this.setupPWAInstallation();

        // Setup offline detection
        this.setupOfflineDetection();

        // Setup background sync
        this.setupBackgroundSync();
    }

    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/sw.js');
                console.log('[PWA] Service Worker registered:', registration);

                // Listen for updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            // New content available, prompt user to refresh
                            this.showUpdateAvailable();
                        }
                    });
                });
            } catch (error) {
                console.error('[PWA] Service Worker registration failed:', error);
            }
        }
    }

    setupPWAInstallation() {
        let deferredPrompt;

        // Listen for beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('[PWA] beforeinstallprompt event fired');
            e.preventDefault();
            deferredPrompt = e;
            this.showInstallPrompt(deferredPrompt);
        });

        // Listen for app installed event
        window.addEventListener('appinstalled', () => {
            console.log('[PWA] App was installed');
            this.hideInstallPrompt();
            this.showToast('AlphaVelocity installed successfully!');
        });
    }

    showInstallPrompt(deferredPrompt) {
        // Create install button if it doesn't exist
        if (!document.getElementById('pwa-install-banner')) {
            const banner = document.createElement('div');
            banner.id = 'pwa-install-banner';
            banner.className = 'pwa-install-banner';
            banner.innerHTML = `
                <div class="install-content">
                    <div class="install-icon">⚡</div>
                    <div class="install-text">
                        <strong>Install AlphaVelocity</strong>
                        <span>Get the full app experience with offline access</span>
                    </div>
                    <button id="install-button" class="install-button">Install</button>
                    <button id="dismiss-install" class="dismiss-button">×</button>
                </div>
            `;

            document.body.appendChild(banner);

            // Handle install button click
            document.getElementById('install-button').addEventListener('click', async () => {
                if (deferredPrompt) {
                    deferredPrompt.prompt();
                    const { outcome } = await deferredPrompt.userChoice;
                    console.log('[PWA] User response to install prompt:', outcome);
                    deferredPrompt = null;
                    this.hideInstallPrompt();
                }
            });

            // Handle dismiss button
            document.getElementById('dismiss-install').addEventListener('click', () => {
                this.hideInstallPrompt();
            });

            // Auto-hide after 10 seconds
            setTimeout(() => {
                this.hideInstallPrompt();
            }, 10000);
        }
    }

    hideInstallPrompt() {
        const banner = document.getElementById('pwa-install-banner');
        if (banner) {
            banner.remove();
        }
    }

    setupOfflineDetection() {
        // Update UI based on online/offline status
        const updateOnlineStatus = () => {
            if (navigator.onLine) {
                document.body.classList.remove('offline');
                this.hideOfflineBanner();
            } else {
                document.body.classList.add('offline');
                this.showOfflineBanner();
            }
        };

        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);

        // Initial check
        updateOnlineStatus();
    }

    showOfflineBanner() {
        if (!document.getElementById('offline-banner')) {
            const banner = document.createElement('div');
            banner.id = 'offline-banner';
            banner.className = 'offline-banner';
            banner.innerHTML = `
                <div class="offline-content">
                    <span class="offline-icon">🔌</span>
                    <span class="offline-text">You're offline. Some features may be limited.</span>
                    <button id="dismiss-offline" class="dismiss-button">×</button>
                </div>
            `;

            document.body.appendChild(banner);

            document.getElementById('dismiss-offline').addEventListener('click', () => {
                this.hideOfflineBanner();
            });
        }
    }

    hideOfflineBanner() {
        const banner = document.getElementById('offline-banner');
        if (banner) {
            banner.remove();
        }
    }

    setupBackgroundSync() {
        // Register for background sync when online
        if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
            navigator.serviceWorker.ready.then(registration => {
                console.log('[PWA] Background sync available');
                this.syncRegistration = registration;
            });
        }
    }

    // Cache portfolio data for offline use
    cachePortfolioData(portfolioData) {
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
                type: 'CACHE_PORTFOLIO',
                payload: portfolioData
            });
        }
    }

    showUpdateAvailable() {
        const banner = document.createElement('div');
        banner.className = 'update-banner';
        banner.innerHTML = `
            <div class="update-content">
                <span class="update-icon">🔄</span>
                <span class="update-text">New version available!</span>
                <button id="update-button" class="update-button">Update</button>
                <button id="dismiss-update" class="dismiss-button">×</button>
            </div>
        `;

        document.body.appendChild(banner);

        document.getElementById('update-button').addEventListener('click', () => {
            window.location.reload();
        });

        document.getElementById('dismiss-update').addEventListener('click', () => {
            banner.remove();
        });
    }

    showToast(message, duration = 3000) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    async loadPerformanceAnalytics(portfolioId = 'default', days = 30) {
        try {
            const response = await fetch(`http://localhost:8000/historical/performance/${portfolioId}?days=${days}`);

            if (!response.ok) {
                throw new Error('Failed to fetch performance analytics');
            }

            const analytics = await response.json();
            this.displayPerformanceAnalytics(analytics);

        } catch (error) {
            console.error('Failed to load performance analytics:', error);
            // Show analytics section but with a message about insufficient data
            this.displayPerformanceAnalytics(null);
        }
    }

    displayPerformanceAnalytics(analytics) {
        const analyticsSection = document.getElementById('performance-analytics');
        const analyticsGrid = document.getElementById('analytics-grid');

        if (!analytics || analytics.data_points < 2) {
            analyticsGrid.innerHTML = `
                <div class="analytics-card" style="grid-column: 1 / -1; text-align: center;">
                    <div class="analytics-label">Performance Data</div>
                    <div class="analytics-value" style="color: #6b7280;">Insufficient Data</div>
                    <div style="color: #6b7280; font-size: 0.875rem; margin-top: 0.5rem;">
                        Analytics will appear after multiple portfolio snapshots are collected over time.
                    </div>
                </div>
            `;
            analyticsSection.style.display = 'block';
            return;
        }

        // Create analytics cards
        const analyticsHTML = `
            <div class="analytics-card">
                <div class="analytics-label">Total Return</div>
                <div class="analytics-value ${analytics.total_return >= 0 ? 'positive' : 'negative'}">
                    ${analytics.total_return >= 0 ? '+' : ''}${analytics.total_return}%
                </div>
            </div>
            <div class="analytics-card">
                <div class="analytics-label">Daily Return</div>
                <div class="analytics-value ${analytics.daily_return >= 0 ? 'positive' : 'negative'}">
                    ${analytics.daily_return >= 0 ? '+' : ''}${analytics.daily_return}%
                </div>
            </div>
            <div class="analytics-card">
                <div class="analytics-label">Volatility</div>
                <div class="analytics-value">${analytics.volatility}%</div>
            </div>
            <div class="analytics-card">
                <div class="analytics-label">Sharpe Ratio</div>
                <div class="analytics-value ${analytics.sharpe_ratio >= 0 ? 'positive' : 'negative'}">
                    ${analytics.sharpe_ratio}
                </div>
            </div>
            <div class="analytics-card">
                <div class="analytics-label">Max Drawdown</div>
                <div class="analytics-value negative">${analytics.max_drawdown}%</div>
            </div>
            <div class="analytics-card">
                <div class="analytics-label">Momentum Trend</div>
                <div class="analytics-value">${analytics.period_days} Days</div>
                <div class="analytics-trend ${analytics.momentum_trend}">
                    ${analytics.momentum_trend}
                </div>
            </div>
        `;

        analyticsGrid.innerHTML = analyticsHTML;
        analyticsSection.style.display = 'block';

        // Setup period selector
        const periodSelector = document.getElementById('analytics-period');
        periodSelector.addEventListener('change', (e) => {
            const days = parseInt(e.target.value);
            this.loadPerformanceAnalytics('default', days);
        });
    }

    setupComparisonControls() {
        // Compare button
        const compareBtn = document.getElementById('compare-with-model');
        if (compareBtn) {
            compareBtn.addEventListener('click', () => {
                this.performComparison();
            });
        }

        // Portfolio type selection
        const portfolioSelectors = document.querySelectorAll('input[name="compare-portfolio"]');
        portfolioSelectors.forEach(selector => {
            selector.addEventListener('change', (e) => {
                this.handlePortfolioSelectionChange(e.target.value);
            });
        });

        // Custom portfolio builder for comparison
        const addCompareHolding = document.getElementById('add-compare-holding');
        if (addCompareHolding) {
            addCompareHolding.addEventListener('click', () => {
                this.addComparisonHolding();
            });
        }

        const compareTickerInput = document.getElementById('compare-ticker-input');
        const compareSharesInput = document.getElementById('compare-shares-input');
        if (compareTickerInput && compareSharesInput) {
            compareTickerInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.addComparisonHolding();
            });

            compareSharesInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.addComparisonHolding();
            });
        }
    }

    setupComparisonView() {
        // Initialize comparison view when switching to it
        const setupSection = document.getElementById('comparison-setup');
        const resultsSection = document.getElementById('comparison-results');

        // Show setup, hide results
        setupSection.style.display = 'block';
        resultsSection.style.display = 'none';

        // Reset portfolio selection
        const customRadio = document.getElementById('compare-custom');
        if (customRadio) {
            customRadio.checked = true;
            this.handlePortfolioSelectionChange('custom');
        }

        // Initialize comparison portfolio if using custom from main portfolio
        if (Object.keys(this.customPortfolio).length > 0) {
            this.comparisonPortfolio = { ...this.customPortfolio };
            this.renderComparisonPortfolio();
        } else {
            this.comparisonPortfolio = {};
        }
    }

    handlePortfolioSelectionChange(value) {
        const customSection = document.getElementById('custom-portfolio-for-compare');

        if (value === 'custom') {
            customSection.style.display = 'block';
            // Initialize with main custom portfolio if available
            if (!this.comparisonPortfolio || Object.keys(this.comparisonPortfolio).length === 0) {
                this.comparisonPortfolio = { ...this.customPortfolio };
                this.renderComparisonPortfolio();
            }
        } else {
            customSection.style.display = 'none';
            // Use sample portfolio
            this.comparisonPortfolio = {
                'AAPL': 100,
                'MSFT': 50,
                'GOOGL': 25,
                'NVDA': 30,
                'TSLA': 20
            };
        }
    }

    addComparisonHolding() {
        const tickerInput = document.getElementById('compare-ticker-input');
        const sharesInput = document.getElementById('compare-shares-input');

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

        // Initialize comparison portfolio if not exists
        if (!this.comparisonPortfolio) {
            this.comparisonPortfolio = {};
        }

        // Add to comparison portfolio
        this.comparisonPortfolio[ticker] = shares;

        // Clear inputs
        tickerInput.value = '';
        sharesInput.value = '';

        // Update display
        this.renderComparisonPortfolio();
    }

    removeComparisonHolding(ticker) {
        if (this.comparisonPortfolio) {
            delete this.comparisonPortfolio[ticker];
            this.renderComparisonPortfolio();
        }
    }

    renderComparisonPortfolio() {
        const container = document.getElementById('compare-holdings-list');

        if (!container) return;

        if (!this.comparisonPortfolio || Object.keys(this.comparisonPortfolio).length === 0) {
            container.innerHTML = '<div class="empty-portfolio">No holdings added yet. Enter a ticker and shares above.</div>';
            return;
        }

        const holdingsHTML = Object.entries(this.comparisonPortfolio).map(([ticker, shares]) => `
            <div class="holding-item">
                <span class="holding-ticker">${ticker}</span>
                <span class="holding-shares">${shares} shares</span>
                <button class="remove-holding" onclick="app.removeComparisonHolding('${ticker}')">×</button>
            </div>
        `).join('');

        container.innerHTML = holdingsHTML;
    }

    async performComparison() {
        const selectedPortfolioType = document.querySelector('input[name="compare-portfolio"]:checked').value;

        let portfolioToCompare;
        if (selectedPortfolioType === 'custom') {
            if (!this.comparisonPortfolio || Object.keys(this.comparisonPortfolio).length === 0) {
                this.showError('Please add some holdings to your comparison portfolio');
                return;
            }
            portfolioToCompare = this.comparisonPortfolio;
        } else {
            // Use sample portfolio
            portfolioToCompare = {
                'AAPL': 100,
                'MSFT': 50,
                'GOOGL': 25,
                'NVDA': 30,
                'TSLA': 20
            };
        }

        try {
            // Show loading and hide setup
            const setupSection = document.getElementById('comparison-setup');
            const resultsSection = document.getElementById('comparison-results');
            const loadingSection = document.getElementById('comparison-loading');
            const contentSection = document.getElementById('comparison-content');

            setupSection.style.display = 'none';
            resultsSection.style.display = 'block';
            loadingSection.style.display = 'block';
            contentSection.style.display = 'none';

            // Make API call
            const comparison = await api.comparePortfolios(portfolioToCompare);

            // Display results
            this.displayComparisonResults(comparison);

            // Hide loading, show content
            loadingSection.style.display = 'none';
            contentSection.style.display = 'block';

        } catch (error) {
            console.error('Failed to perform comparison:', error);
            this.showError('Failed to perform portfolio comparison. Please try again.');

            // Reset view on error
            const setupSection = document.getElementById('comparison-setup');
            const resultsSection = document.getElementById('comparison-results');
            setupSection.style.display = 'block';
            resultsSection.style.display = 'none';
        }
    }

    displayComparisonResults(comparison) {
        const contentSection = document.getElementById('comparison-content');

        const resultsHTML = `
            <div class="comparison-header">
                <h3>Portfolio Comparison Results</h3>
                <button class="back-to-setup" onclick="app.backToComparisonSetup()">← Back to Setup</button>
            </div>

            <div class="comparison-summary">
                <div class="portfolio-summary-cards">
                    <div class="summary-card">
                        <h4>${comparison.portfolio_a.name}</h4>
                        <div class="summary-stats">
                            <div class="stat-item">
                                <span class="stat-label">Total Value:</span>
                                <span class="stat-value">${formatCurrency(comparison.portfolio_a.total_value)}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Avg Momentum:</span>
                                <span class="stat-value" style="color: ${getScoreColor(comparison.portfolio_a.average_momentum_score)}">
                                    ${formatScore(comparison.portfolio_a.average_momentum_score)}
                                </span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Positions:</span>
                                <span class="stat-value">${comparison.portfolio_a.number_of_positions}</span>
                            </div>
                        </div>
                    </div>

                    <div class="vs-divider">VS</div>

                    <div class="summary-card">
                        <h4>${comparison.portfolio_b.name}</h4>
                        <div class="summary-stats">
                            <div class="stat-item">
                                <span class="stat-label">Total Value:</span>
                                <span class="stat-value">${formatCurrency(comparison.portfolio_b.total_value)}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Avg Momentum:</span>
                                <span class="stat-value" style="color: ${getScoreColor(comparison.portfolio_b.average_momentum_score)}">
                                    ${formatScore(comparison.portfolio_b.average_momentum_score)}
                                </span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Positions:</span>
                                <span class="stat-value">${comparison.portfolio_b.number_of_positions}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="comparison-sections">
                <!-- Performance Comparison -->
                <div class="comparison-section">
                    <h4>Performance Metrics</h4>
                    <div class="performance-table">
                        <table class="comparison-table">
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>${comparison.portfolio_a.name}</th>
                                    <th>${comparison.portfolio_b.name}</th>
                                    <th>Difference</th>
                                    <th>Winner</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${comparison.performance_comparison.map(perf => `
                                    <tr>
                                        <td>${perf.metric}</td>
                                        <td>${this.formatMetricValue(perf.metric, perf.portfolio_a_value)}</td>
                                        <td>${this.formatMetricValue(perf.metric, perf.portfolio_b_value)}</td>
                                        <td class="${perf.difference >= 0 ? 'positive' : 'negative'}">
                                            ${perf.difference >= 0 ? '+' : ''}${this.formatMetricValue(perf.metric, perf.difference)}
                                        </td>
                                        <td>
                                            <span class="winner-badge ${perf.winner}">
                                                ${perf.winner === 'portfolio_a' ? comparison.portfolio_a.name :
                                                  perf.winner === 'portfolio_b' ? comparison.portfolio_b.name : 'Tie'}
                                            </span>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Allocation Comparison -->
                <div class="comparison-section">
                    <h4>Category Allocation Differences</h4>
                    <div class="allocation-comparison">
                        ${comparison.allocation_comparison.slice(0, 8).map(alloc => `
                            <div class="allocation-item">
                                <div class="allocation-header">
                                    <span class="category-name">${alloc.category}</span>
                                    <span class="allocation-difference ${alloc.difference >= 0 ? 'positive' : 'negative'}">
                                        ${alloc.difference >= 0 ? '+' : ''}${alloc.difference.toFixed(1)}%
                                    </span>
                                </div>
                                <div class="allocation-bars">
                                    <div class="allocation-bar">
                                        <span class="bar-label">${comparison.portfolio_a.name}:</span>
                                        <div class="bar-container">
                                            <div class="bar-fill" style="width: ${Math.min(alloc.portfolio_a_percent, 100)}%"></div>
                                            <span class="bar-value">${alloc.portfolio_a_percent.toFixed(1)}%</span>
                                        </div>
                                    </div>
                                    <div class="allocation-bar">
                                        <span class="bar-label">${comparison.portfolio_b.name}:</span>
                                        <div class="bar-container">
                                            <div class="bar-fill" style="width: ${Math.min(alloc.portfolio_b_percent, 100)}%"></div>
                                            <span class="bar-value">${alloc.portfolio_b_percent.toFixed(1)}%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Key Differences -->
                <div class="comparison-section">
                    <h4>Key Differences</h4>
                    <div class="key-differences">
                        ${comparison.key_differences.map(diff => `
                            <div class="difference-item">
                                <span class="difference-icon">📊</span>
                                <span class="difference-text">${diff}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Recommendation -->
                <div class="comparison-section">
                    <h4>Recommendation</h4>
                    <div class="recommendation">
                        <div class="recommendation-text">
                            ${comparison.recommendation}
                        </div>
                    </div>
                </div>

                <!-- Diversification Metrics -->
                <div class="comparison-section">
                    <h4>Diversification Analysis</h4>
                    <div class="diversification-comparison">
                        <div class="diversification-cards">
                            <div class="diversification-card">
                                <h5>${comparison.portfolio_a.name}</h5>
                                <div class="diversification-metrics">
                                    <div class="metric">
                                        <span class="metric-label">Top 5 Concentration:</span>
                                        <span class="metric-value">${comparison.diversification_a.concentration_ratio.toFixed(1)}%</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">Sectors:</span>
                                        <span class="metric-value">${comparison.diversification_a.sector_count}</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">Largest Position:</span>
                                        <span class="metric-value">${comparison.diversification_a.largest_position_percent.toFixed(1)}%</span>
                                    </div>
                                </div>
                            </div>
                            <div class="diversification-card">
                                <h5>${comparison.portfolio_b.name}</h5>
                                <div class="diversification-metrics">
                                    <div class="metric">
                                        <span class="metric-label">Top 5 Concentration:</span>
                                        <span class="metric-value">${comparison.diversification_b.concentration_ratio.toFixed(1)}%</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">Sectors:</span>
                                        <span class="metric-value">${comparison.diversification_b.sector_count}</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">Largest Position:</span>
                                        <span class="metric-value">${comparison.diversification_b.largest_position_percent.toFixed(1)}%</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        contentSection.innerHTML = resultsHTML;
    }

    formatMetricValue(metric, value) {
        if (typeof value !== 'number') return value;

        if (metric.includes('Value')) {
            return formatCurrency(value);
        } else if (metric.includes('Score') || metric.includes('Ratio')) {
            return value.toFixed(2);
        } else if (metric.includes('%') || metric.includes('Return') || metric.includes('Volatility') || metric.includes('Drawdown')) {
            return value.toFixed(2) + '%';
        } else {
            return Math.round(value);
        }
    }

    backToComparisonSetup() {
        const setupSection = document.getElementById('comparison-setup');
        const resultsSection = document.getElementById('comparison-results');

        setupSection.style.display = 'block';
        resultsSection.style.display = 'none';
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AlphaVelocityApp();
});