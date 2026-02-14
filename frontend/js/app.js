// AlphaVelocity Frontend Application
class AlphaVelocityApp {
    constructor() {
        this.currentView = 'dashboard';
        this.portfolioMode = 'default'; // 'default' or 'custom'
        this.databaseMode = false; // Enable database-backed portfolio management
        this.currentPortfolioId = 1; // Default portfolio ID for database mode
        this.customPortfolio = {};
        this.authManager = null; // Will be initialized in init()
        this.transactionPage = 1; // Current page for transaction history pagination
        this.init();
    }

    init() {
        // Initialize auth manager
        this.authManager = new AuthManager(window.ALPHAVELOCITY_API_URL || window.location.origin);
        this.authManager.initAuthUI();
        this.authManager.setupEventListeners();

        // Initialize portfolio manager
        this.portfolioManager = new PortfolioManager(window.ALPHAVELOCITY_API_URL || window.location.origin, this.authManager);

        // Set auth manager on API instance
        api.setAuthManager(this.authManager);

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
            case 'portfolio-builder':
                this.loadPortfolioBuilderData();
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

            // Load user portfolio dashboard if logged in
            if (this.authManager && this.authManager.isLoggedIn()) {
                await this.loadUserPortfolioDashboard();
            }

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

    async loadUserPortfolioDashboard() {
        const section = document.getElementById('portfolio-dashboard-section');
        const defaultSection = document.getElementById('default-dashboard-section');

        if (!section) {
            console.error('Portfolio dashboard section not found');
            return;
        }

        try {
            section.style.display = 'block';
            if (defaultSection) defaultSection.style.display = 'none';

            await this.portfolioManager.renderPortfolioDashboard('portfolio-dashboard');

            // Load selected portfolio holdings if one is selected
            const selectedId = this.portfolioManager.getSelectedPortfolioId();
            if (selectedId) {
                await this.loadSelectedPortfolioHoldings(selectedId);
            }
        } catch (error) {
            console.error('Error loading user portfolio dashboard:', error);
            if (section) {
                section.innerHTML = `<div class="error">Failed to load portfolios: ${error.message}</div>`;
            }
        }
    }

    async loadSelectedPortfolioHoldings(portfolioId) {
        const detailsSection = document.getElementById('selected-portfolio-details');
        const holdingsContainer = document.getElementById('selected-portfolio-holdings');
        const portfolioNameHeader = document.getElementById('selected-portfolio-name');

        if (!detailsSection || !holdingsContainer) return;

        try {
            // Get portfolio details
            const portfolioResult = await this.portfolioManager.getPortfolio(portfolioId);
            if (!portfolioResult.success) {
                console.error('Failed to get portfolio:', portfolioResult.error);
                detailsSection.style.display = 'none';
                return;
            }

            const portfolio = portfolioResult.portfolio;
            console.log('Portfolio loaded:', portfolio);

            // Update header with portfolio name and Edit Targets button
            if (portfolioNameHeader) {
                portfolioNameHeader.innerHTML = `
                    ${portfolio.name} - Holdings
                    <button class="btn-edit-targets" onclick="app.showEditTargetsModal(${portfolioId})">
                        Edit Targets
                    </button>
                `;
            }

            // Get holdings
            const holdings = portfolio.holdings || [];

            // Debug: Log holdings data to check category field
            console.log('Portfolio holdings data:', holdings);
            if (holdings.length > 0) {
                console.log('Sample holding with category:', holdings[0]);
            }

            if (holdings.length === 0) {
                detailsSection.style.display = 'block';
                holdingsContainer.innerHTML = `
                    <div class="empty-state">
                        <p>No holdings in this portfolio yet.</p>
                        <p>Go to the <strong>Builder</strong> tab to add transactions.</p>
                    </div>
                `;
                return;
            }

            // Fetch momentum scores and current prices for all holdings
            const momentumScores = {};
            const currentPrices = {};
            await Promise.all(holdings.map(async (h) => {
                try {
                    const score = await api.getMomentumScore(h.ticker);
                    momentumScores[h.ticker] = score;
                    // Extract current price from momentum data
                    if (score && score.current_price) {
                        currentPrices[h.ticker] = score.current_price;
                    }
                } catch (error) {
                    console.warn(`Failed to fetch momentum score for ${h.ticker}:`, error);
                }
            }));

            // Helper function to get score color
            const getScoreColor = (score) => {
                if (score >= 80) return '#10b981'; // Green
                if (score >= 70) return '#3b82f6'; // Blue
                if (score >= 60) return '#f59e0b'; // Yellow
                if (score >= 50) return '#ef4444'; // Orange
                return '#dc2626'; // Red
            };

            // Helper function to get rating color
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

            // Get portfolio-specific category targets
            const targetsResponse = await api.getPortfolioCategoryTargets(portfolioId);
            const categoryMap = {};
            targetsResponse.targets.forEach(target => {
                categoryMap[target.category_name] = {
                    target_allocation: target.target_allocation_pct / 100,  // Convert to decimal
                    benchmark: target.benchmark
                };
            });

            // Group holdings by category and calculate values (using current prices)
            const holdingsByCategory = {};
            let totalPortfolioValue = 0;

            holdings.forEach(h => {
                const category = h.category || 'Uncategorized';
                if (!holdingsByCategory[category]) {
                    holdingsByCategory[category] = {
                        holdings: [],
                        totalValue: 0
                    };
                }
                // Use current price if available, otherwise fall back to cost basis
                const currentPrice = currentPrices[h.ticker];
                const holdingValue = currentPrice ? currentPrice * h.shares : (h.average_cost_basis || 0) * h.shares;
                holdingsByCategory[category].holdings.push(h);
                holdingsByCategory[category].totalValue += holdingValue;
                totalPortfolioValue += holdingValue;
            });

            // Display holdings grouped by category
            detailsSection.style.display = 'block';
            let holdingsHTML = '';

            // Sort categories by total value (descending)
            const sortedCategories = Object.keys(holdingsByCategory).sort((a, b) => {
                return holdingsByCategory[b].totalValue - holdingsByCategory[a].totalValue;
            });

            sortedCategories.forEach(categoryName => {
                const categoryData = holdingsByCategory[categoryName];
                const categoryInfo = categoryMap[categoryName] || { target_allocation: 0 };
                const actualAllocation = totalPortfolioValue > 0 ? categoryData.totalValue / totalPortfolioValue : 0;
                const targetAllocation = categoryInfo.target_allocation;

                const actualPercent = (actualAllocation * 100).toFixed(1);
                const targetPercent = (targetAllocation * 100).toFixed(1);
                const isOverweight = actualAllocation > targetAllocation;
                const isUnderweight = actualAllocation < targetAllocation && targetAllocation > 0;

                let allocationClass = '';
                let allocationIndicator = '';
                if (isOverweight) {
                    allocationClass = 'overweight';
                    allocationIndicator = '▲';
                } else if (isUnderweight) {
                    allocationClass = 'underweight';
                    allocationIndicator = '▼';
                }

                holdingsHTML += `
                    <div class="category-section">
                        <div class="category-header">
                            <h3>${categoryName}</h3>
                            <div class="category-allocation">
                                <span class="allocation-actual ${allocationClass}">${actualPercent}%</span>
                                <span class="allocation-separator">/</span>
                                <span class="allocation-target">${targetPercent}%</span>
                                ${allocationIndicator ? `<span class="allocation-indicator ${allocationClass}">${allocationIndicator}</span>` : ''}
                            </div>
                        </div>
                        <div class="holdings-table-wrapper">
                            <table class="holdings-table">
                                <thead>
                                    <tr>
                                        <th>Ticker</th>
                                        <th>Shares</th>
                                        <th>Avg Cost</th>
                                        <th>Total Cost</th>
                                        <th>Current Price</th>
                                        <th>Current Value</th>
                                        <th>Gain/Loss</th>
                                        <th>Momentum</th>
                                        <th>Rating</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${categoryData.holdings.map(h => {
                                        const momentum = momentumScores[h.ticker];
                                        const score = momentum ? momentum.composite_score : null;
                                        const rating = momentum ? momentum.rating : null;
                                        const scoreColor = score ? getScoreColor(score) : '#6b7280';
                                        const ratingColor = rating ? getRatingColor(rating) : '#6b7280';

                                        // Calculate current value
                                        const currentPrice = currentPrices[h.ticker];
                                        const currentValue = currentPrice ? currentPrice * h.shares : null;
                                        const costBasis = h.total_cost_basis || 0;
                                        const gainLoss = currentValue ? currentValue - costBasis : null;
                                        const gainLossPercent = (costBasis > 0 && gainLoss !== null) ? (gainLoss / costBasis) * 100 : null;
                                        const gainLossColor = gainLoss !== null ? (gainLoss >= 0 ? '#10b981' : '#ef4444') : '#6b7280';

                                        return `
                                            <tr>
                                                <td class="ticker-cell">${h.ticker}</td>
                                                <td>${h.shares.toFixed(2)}</td>
                                                <td>$${h.average_cost_basis ? h.average_cost_basis.toFixed(2) : '—'}</td>
                                                <td>$${h.total_cost_basis ? h.total_cost_basis.toFixed(2) : '—'}</td>
                                                <td>
                                                    ${currentPrice !== null ?
                                                        `$${currentPrice.toFixed(2)}`
                                                        : '<span style="color: #6b7280;">—</span>'}
                                                </td>
                                                <td>
                                                    ${currentValue !== null ?
                                                        `<strong>$${currentValue.toFixed(2)}</strong>`
                                                        : '<span style="color: #6b7280;">—</span>'}
                                                </td>
                                                <td style="color: ${gainLossColor}; font-weight: 600;">
                                                    ${gainLoss !== null ?
                                                        `$${gainLoss.toFixed(2)} (${gainLossPercent.toFixed(1)}%)`
                                                        : '<span style="color: #6b7280;">—</span>'}
                                                </td>
                                                <td>
                                                    ${score !== null && score !== undefined ?
                                                        `<span class="momentum-score" style="color: ${scoreColor}; font-weight: 600;">${Number(score).toFixed(1)}</span>`
                                                        : '<span style="color: #6b7280;">—</span>'}
                                                </td>
                                                <td>
                                                    ${rating ?
                                                        `<span class="rating-badge" style="background: ${ratingColor}20; color: ${ratingColor}; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 600;">${rating}</span>`
                                                        : '<span style="color: #6b7280;">—</span>'}
                                                </td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
            });

            holdingsContainer.innerHTML = holdingsHTML;
        } catch (error) {
            console.error('Error loading portfolio holdings:', error);
            detailsSection.style.display = 'none';
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
                // Use file-based portfolio analysis (categorized)
                portfolio = await api.getPortfolioAnalysisByCategories();
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
                api.getPortfolioAnalysisByCategories(),
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
            const response = await api.getAllCategoriesManagement();
            const categories = response.categories;

            container.innerHTML = categories.map(category => `
                <div class="category-card" data-category="${category.name}" data-category-id="${category.id}">
                    <div class="category-header">
                        <div class="category-title-row">
                            <h3>${category.name}</h3>
                            <span class="allocation" title="Target allocation for this category">Target: ${formatPercentage(category.target_allocation_pct)}</span>
                        </div>
                        <div class="category-meta">
                            <span class="meta-item"><strong>Benchmark:</strong> ${category.benchmark}</span>
                            <span class="meta-divider">|</span>
                            <span class="meta-item"><strong>Tickers:</strong> ${category.ticker_count}</span>
                        </div>
                    </div>
                    <div class="category-info">
                        <div class="ticker-list-container">
                            <table class="ticker-momentum-table">
                                <thead>
                                    <tr>
                                        <th>Ticker</th>
                                        <th>Score</th>
                                        <th>Rating</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${category.ticker_details.map(detail => {
                                        const scoreColor = getScoreColor(detail.momentum_score || 0);
                                        const ratingColor = getRatingColor(detail.rating || 'N/A');
                                        return `
                                            <tr>
                                                <td class="ticker-cell">
                                                    <strong>${detail.ticker}</strong>
                                                </td>
                                                <td class="score-cell">
                                                    <span class="momentum-score" style="color: ${scoreColor}; font-weight: bold;">
                                                        ${(detail.momentum_score || 0).toFixed(1)}
                                                    </span>
                                                </td>
                                                <td class="rating-cell">
                                                    <span class="rating-badge" style="background-color: ${ratingColor};">
                                                        ${detail.rating || 'N/A'}
                                                    </span>
                                                </td>
                                                <td class="action-cell">
                                                    <button class="remove-ticker-btn-table" onclick="app.removeTicker(${category.id}, '${detail.ticker}')" title="Remove">×</button>
                                                </td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="category-actions">
                        <button class="add-ticker-btn" onclick="app.showAddTickerModal(${category.id}, '${category.name}')">
                            + Add Ticker
                        </button>
                    </div>
                </div>
            `).join('');

            loading.style.display = 'none';
        } catch (error) {
            loading.textContent = 'Failed to load categories';
            console.error('Failed to load categories:', error);
        }
    }

    async showAddTickerModal(categoryId, categoryName) {
        const modalHTML = `
            <div class="modal-overlay" id="add-ticker-modal">
                <div class="modal add-ticker-modal" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h3>Add Ticker to ${categoryName}</h3>
                        <button class="close-btn" onclick="document.getElementById('add-ticker-modal').remove()">×</button>
                    </div>
                    <div class="modal-content">
                        <div class="input-group">
                            <label for="new-ticker-input">Ticker Symbol:</label>
                            <input type="text" id="new-ticker-input" placeholder="e.g., AAPL" maxlength="10" style="text-transform: uppercase;">
                        </div>
                        <div class="modal-actions">
                            <button class="btn-secondary" onclick="document.getElementById('add-ticker-modal').remove()">Cancel</button>
                            <button class="btn-primary" onclick="app.addTicker(${categoryId})">Add Ticker</button>
                        </div>
                        <div id="add-ticker-message" class="message"></div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.getElementById('new-ticker-input').focus();

        // Allow Enter key to submit
        document.getElementById('new-ticker-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.addTicker(categoryId);
            }
        });
    }

    async addTicker(categoryId) {
        const input = document.getElementById('new-ticker-input');
        const messageDiv = document.getElementById('add-ticker-message');
        const ticker = input.value.trim().toUpperCase();

        if (!ticker) {
            messageDiv.innerHTML = '<span class="error">Please enter a ticker symbol</span>';
            return;
        }

        try {
            messageDiv.innerHTML = '<span class="info">Adding...</span>';
            const result = await api.addTickerToCategory(categoryId, ticker);

            if (result.success) {
                messageDiv.innerHTML = '<span class="success">Ticker added successfully!</span>';
                setTimeout(() => {
                    document.getElementById('add-ticker-modal').remove();
                    this.loadCategoriesData(); // Reload to show new ticker
                }, 1000);
            } else {
                messageDiv.innerHTML = `<span class="error">${result.error || 'Failed to add ticker'}</span>`;
            }
        } catch (error) {
            messageDiv.innerHTML = '<span class="error">Failed to add ticker. Please try again.</span>';
            console.error('Error adding ticker:', error);
        }
    }

    async removeTicker(categoryId, ticker) {
        if (!confirm(`Remove ${ticker} from this category?`)) {
            return;
        }

        try {
            const result = await api.removeTickerFromCategory(categoryId, ticker);

            if (result.success) {
                // Remove the pill from UI
                this.loadCategoriesData(); // Reload to update display
            } else {
                alert(result.error || 'Failed to remove ticker');
            }
        } catch (error) {
            alert('Failed to remove ticker. Please try again.');
            console.error('Error removing ticker:', error);
        }
    }

    showCreateCategoryModal() {
        const modalHTML = `
            <div class="modal-overlay" id="create-category-modal">
                <div class="modal create-category-modal" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h3>Create New Category</h3>
                        <button class="close-btn" onclick="document.getElementById('create-category-modal').remove()">×</button>
                    </div>
                    <div class="modal-content">
                        <div class="input-group">
                            <label for="category-name-input">Category Name: <span class="required">*</span></label>
                            <input type="text" id="category-name-input" placeholder="e.g., Technology Giants" maxlength="100">
                        </div>
                        <div class="input-group">
                            <label for="category-description-input">Description:</label>
                            <textarea id="category-description-input" placeholder="Brief description of this category" rows="3"></textarea>
                        </div>
                        <div class="input-group">
                            <label for="category-allocation-input">Target Allocation (%): <span class="required">*</span></label>
                            <input type="number" id="category-allocation-input" placeholder="e.g., 15" min="0" max="100" step="0.1">
                        </div>
                        <div class="input-group">
                            <label for="category-benchmark-input">Benchmark Ticker: <span class="required">*</span></label>
                            <input type="text" id="category-benchmark-input" placeholder="e.g., SPY" maxlength="20" style="text-transform: uppercase;">
                        </div>
                        <div class="modal-actions">
                            <button class="btn-secondary" onclick="document.getElementById('create-category-modal').remove()">Cancel</button>
                            <button class="btn-primary" onclick="app.createCategory()">Create Category</button>
                        </div>
                        <div id="create-category-message" class="message"></div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.getElementById('category-name-input').focus();
    }

    async createCategory() {
        const messageDiv = document.getElementById('create-category-message');

        // Get form values
        const name = document.getElementById('category-name-input').value.trim();
        const description = document.getElementById('category-description-input').value.trim();
        const allocationInput = document.getElementById('category-allocation-input').value.trim();
        const benchmark = document.getElementById('category-benchmark-input').value.trim().toUpperCase();

        // Validation
        if (!name) {
            messageDiv.innerHTML = '<span class="error">Category name is required</span>';
            return;
        }

        if (!allocationInput || isNaN(allocationInput)) {
            messageDiv.innerHTML = '<span class="error">Target allocation must be a number</span>';
            return;
        }

        const targetAllocationPct = parseFloat(allocationInput);
        if (targetAllocationPct < 0 || targetAllocationPct > 100) {
            messageDiv.innerHTML = '<span class="error">Target allocation must be between 0 and 100</span>';
            return;
        }

        if (!benchmark) {
            messageDiv.innerHTML = '<span class="error">Benchmark ticker is required</span>';
            return;
        }

        try {
            messageDiv.innerHTML = '<span class="info">Creating category...</span>';
            const result = await api.createCategory(name, description || '', targetAllocationPct, benchmark);

            if (result.success) {
                messageDiv.innerHTML = '<span class="success">Category created successfully!</span>';
                setTimeout(() => {
                    document.getElementById('create-category-modal').remove();
                    this.loadCategoriesData(); // Reload categories to show new one
                }, 1000);
            } else {
                messageDiv.innerHTML = `<span class="error">${result.error || 'Failed to create category'}</span>`;
            }
        } catch (error) {
            messageDiv.innerHTML = '<span class="error">Failed to create category. Please try again.</span>';
            console.error('Error creating category:', error);
        }
    }

    async showEditTargetsModal(portfolioId) {
        try {
            // Fetch current targets (includes category info, so we don't need a separate call)
            const targetsResponse = await api.getPortfolioCategoryTargets(portfolioId);
            const targets = targetsResponse.targets;

            // Use the targets array directly - it already has category names and IDs
            const allCategories = targets.map(t => ({
                id: t.category_id,
                name: t.category_name,
                target_allocation_pct: t.target_allocation_pct
            }));

            // Create a map of category_id -> target_pct
            const targetMap = {};
            targets.forEach(t => {
                targetMap[t.category_id] = t.target_allocation_pct;
            });

            // Create modal element
            const modal = document.createElement('div');
            modal.className = 'modal modal-large';
            modal.id = 'edit-targets-modal';
            modal.style.display = 'flex';
            modal.innerHTML = `
                <div class="modal-content">
                    <span class="close">&times;</span>
                    <h2>Edit Category Targets</h2>
                    <div class="form-section">
                        <p class="form-help">Adjust target allocation percentages for each category in this portfolio</p>
                        <div class="allocation-total-display">
                            <span id="edit-allocation-total">Total: 0%</span>
                        </div>
                        <div class="allocation-grid" id="edit-allocation-inputs">
                            ${allCategories.filter(cat => cat.name !== 'Uncategorized').map(cat => `
                                <div class="allocation-item">
                                    <label for="edit-alloc-${cat.id}">${cat.name}</label>
                                    <div class="input-with-unit">
                                        <input
                                            type="number"
                                            id="edit-alloc-${cat.id}"
                                            data-category-id="${cat.id}"
                                            min="0"
                                            max="100"
                                            step="0.1"
                                            value="${(targetMap[cat.id] || 0).toFixed(1)}"
                                            class="allocation-input">
                                        <span class="unit">%</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="modal-actions">
                        <button class="btn-secondary" id="reset-targets-btn">Reset to Defaults</button>
                        <button class="submit-btn" id="save-targets-btn">Save Changes</button>
                    </div>
                    <div id="edit-targets-message" class="message"></div>
                </div>
            `;

            document.body.appendChild(modal);

            // Update total when allocations change
            const updateTotal = () => {
                const inputs = modal.querySelectorAll('.allocation-input');
                let total = 0;
                inputs.forEach(input => {
                    total += parseFloat(input.value) || 0;
                });
                const totalEl = modal.querySelector('#edit-allocation-total');
                totalEl.textContent = `Total: ${total.toFixed(1)}%`;

                // Color code based on total
                if (Math.abs(total - 100) < 0.1) {
                    totalEl.style.color = '#10b981'; // Green at 100%
                } else if (total > 100) {
                    totalEl.style.color = '#ef4444'; // Red if over
                } else {
                    totalEl.style.color = '#f59e0b'; // Yellow if under
                }
            };

            // Add event listeners to all inputs
            modal.querySelectorAll('.allocation-input').forEach(input => {
                input.addEventListener('input', updateTotal);
            });

            // Initialize total
            updateTotal();

            // Close modal
            modal.querySelector('.close').addEventListener('click', () => {
                modal.remove();
            });

            // Handle save
            modal.querySelector('#save-targets-btn').addEventListener('click', async () => {
                await this.savePortfolioTargets(portfolioId);
            });

            // Handle reset
            modal.querySelector('#reset-targets-btn').addEventListener('click', async () => {
                await this.resetToDefaultTargets(portfolioId);
            });

        } catch (error) {
            console.error('Error showing edit targets modal:', error);
            alert('Failed to load targets. Please try again.');
        }
    }

    async savePortfolioTargets(portfolioId) {
        const modal = document.getElementById('edit-targets-modal');
        const messageDiv = document.getElementById('edit-targets-message');

        if (!modal || !messageDiv) return;

        try {
            messageDiv.innerHTML = '<span class="info">Saving targets...</span>';

            // Get all allocation inputs
            const inputs = modal.querySelectorAll('.allocation-input');
            const updates = [];

            inputs.forEach(input => {
                const categoryId = input.dataset.categoryId;
                const targetPct = parseFloat(input.value) || 0;
                updates.push(
                    api.setPortfolioCategoryTarget(portfolioId, categoryId, targetPct)
                );
            });

            await Promise.all(updates);

            messageDiv.innerHTML = '<span class="success">Targets updated successfully!</span>';

            setTimeout(() => {
                modal.remove();
                // Reload the portfolio holdings to show updated targets
                this.loadSelectedPortfolioHoldings(portfolioId);
            }, 1000);

        } catch (error) {
            console.error('Error saving targets:', error);
            messageDiv.innerHTML = '<span class="error">Failed to save targets. Please try again.</span>';
        }
    }

    async resetToDefaultTargets(portfolioId) {
        if (!confirm('Reset this portfolio to use global default targets? This will overwrite any custom targets.')) {
            return;
        }

        const modal = document.getElementById('edit-targets-modal');
        const messageDiv = document.getElementById('edit-targets-message');

        if (!modal || !messageDiv) return;

        try {
            messageDiv.innerHTML = '<span class="info">Resetting to defaults...</span>';

            await api.resetPortfolioTargets(portfolioId);

            messageDiv.innerHTML = '<span class="success">Reset to default targets!</span>';

            setTimeout(() => {
                modal.remove();
                // Reload the portfolio holdings to show updated targets
                this.loadSelectedPortfolioHoldings(portfolioId);
            }, 1000);

        } catch (error) {
            console.error('Error resetting targets:', error);
            messageDiv.innerHTML = '<span class="error">Failed to reset targets. Please try again.</span>';
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
            const analysis = await api.analyzeCustomPortfolioByCategories(this.customPortfolio);

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

        // Check if analysis has categories (new format)
        if (analysis.categories) {
            this.displayCategorizedPortfolio(analysis);
            return;
        }

        // Old format - single table for all holdings
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

    displayCategorizedPortfolio(analysis) {
        const container = document.getElementById('portfolio-table');

        // Build HTML with portfolio summary and categorized tables
        let portfolioHTML = `
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
        `;

        // Add each category as a separate table
        for (const [categoryName, categoryData] of Object.entries(analysis.categories)) {
            const actualPercent = (categoryData.actual_allocation * 100).toFixed(1);
            const targetPercent = (categoryData.target_allocation * 100).toFixed(1);
            const isOverweight = categoryData.actual_allocation > categoryData.target_allocation;
            const isUnderweight = categoryData.actual_allocation < categoryData.target_allocation;

            let allocationClass = '';
            let allocationIndicator = '';
            if (isOverweight) {
                allocationClass = 'overweight';
                allocationIndicator = '▲';
            } else if (isUnderweight) {
                allocationClass = 'underweight';
                allocationIndicator = '▼';
            }

            portfolioHTML += `
                <div class="category-section">
                    <div class="category-header">
                        <h3>${categoryData.name}</h3>
                        <div class="category-allocation">
                            <span class="allocation-label">Allocation:</span>
                            <span class="allocation-actual ${allocationClass}">${actualPercent}%</span>
                            <span class="allocation-separator">/</span>
                            <span class="allocation-target">${targetPercent}%</span>
                            <span class="allocation-indicator ${allocationClass}">${allocationIndicator}</span>
                        </div>
                    </div>
                    <table class="data-table category-table">
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
        }

        container.innerHTML = portfolioHTML;

        // Show and render charts
        const chartsSection = document.getElementById('portfolio-charts');
        chartsSection.style.display = 'block';

        // Create charts with categorized data
        chartManager.createAllocationChart('allocation-chart', analysis);

        // Flatten holdings for momentum chart
        const allHoldings = [];
        for (const categoryData of Object.values(analysis.categories)) {
            allHoldings.push(...categoryData.holdings);
        }
        chartManager.createMomentumChart('momentum-chart', allHoldings);
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
            const response = await fetch(`${window.ALPHAVELOCITY_API_URL || window.location.origin}/historical/performance/${portfolioId}?days=${days}`);

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

        // Setup period selector (guard against duplicate listeners)
        const periodSelector = document.getElementById('analytics-period');
        if (!this._analyticsPeriodListenerAttached) {
            this._analyticsPeriodListenerAttached = true;
            periodSelector.addEventListener('change', (e) => {
                const days = parseInt(e.target.value);
                this.loadPerformanceAnalytics('default', days);
            });
        }
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

    // Portfolio Builder functionality
    async loadPortfolioBuilderData() {
        // Initialize portfolio selector if user is logged in
        if (this.authManager && this.authManager.isLoggedIn()) {
            await this.portfolioManager.initBuilderPortfolioSelector();
        }

        // Set today's date as default
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('transaction-date').value = today;

        // Setup event listeners
        this.setupPortfolioBuilderEventListeners();

        // Load transaction history and portfolio summary
        await this.loadTransactionHistory();
        await this.updateBuilderPortfolioSummary();
    }

    setupPortfolioBuilderEventListeners() {
        // Prevent duplicate listeners when view is re-entered
        if (this._builderListenersAttached) return;
        this._builderListenersAttached = true;

        const addTransactionBtn = document.getElementById('add-transaction-btn');
        const clearFormBtn = document.getElementById('clear-form-btn');

        if (addTransactionBtn) {
            addTransactionBtn.addEventListener('click', () => this.addTransaction());
        }

        if (clearFormBtn) {
            clearFormBtn.addEventListener('click', () => this.clearTransactionForm());
        }

        // Enter key support for form fields
        const formInputs = ['transaction-ticker', 'transaction-shares', 'transaction-price'];
        formInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') this.addTransaction();
                });
            }
        });

        // Toggle UI when transaction type changes (SPLIT hides price/fees)
        const typeSelect = document.getElementById('transaction-type');
        if (typeSelect) {
            typeSelect.addEventListener('change', () => this.onTransactionTypeChange());
        }
    }

    onTransactionTypeChange() {
        const type = document.getElementById('transaction-type').value;
        const sharesLabel = document.querySelector('label[for="transaction-shares"]');
        const priceGroup = document.getElementById('transaction-price').closest('.form-group');
        const feesGroup = document.getElementById('transaction-fees').closest('.form-group');

        if (type === 'SPLIT') {
            if (sharesLabel) sharesLabel.textContent = 'Split Ratio (e.g., 4 for 4:1)';
            if (priceGroup) priceGroup.style.display = 'none';
            if (feesGroup) feesGroup.style.display = 'none';
        } else {
            if (sharesLabel) sharesLabel.textContent = 'Shares';
            if (priceGroup) priceGroup.style.display = '';
            if (feesGroup) feesGroup.style.display = '';
        }
    }

    async addTransaction() {
        const ticker = document.getElementById('transaction-ticker').value.trim().toUpperCase();
        const type = document.getElementById('transaction-type').value;
        const shares = parseFloat(document.getElementById('transaction-shares').value);
        const price = parseFloat(document.getElementById('transaction-price').value);
        const date = document.getElementById('transaction-date').value;
        const fees = parseFloat(document.getElementById('transaction-fees').value) || 0;
        const notes = document.getElementById('transaction-notes').value.trim();

        const isSplit = type === 'SPLIT';

        // Validation
        if (!ticker) {
            this.showError('Please enter a stock ticker');
            return;
        }

        if (!shares || shares <= 0) {
            this.showError(isSplit ? 'Please enter a valid split ratio' : 'Please enter a valid number of shares');
            return;
        }

        if (!isSplit && (!price || price <= 0)) {
            this.showError('Please enter a valid price per share');
            return;
        }

        if (!date) {
            this.showError('Please select a transaction date');
            return;
        }

        const transactionData = {
            ticker: ticker,
            transaction_type: type,
            shares: shares,
            price_per_share: isSplit ? 0 : price,
            transaction_date: date,
            fees: isSplit ? 0 : fees,
            notes: notes || null
        };

        try {
            this.showLoading('Adding transaction...');

            // Get selected portfolio ID
            const portfolioId = this.portfolioManager.getSelectedPortfolioId();
            if (!portfolioId) {
                this.showError('Please select a portfolio first');
                return;
            }

            const result = await api.addTransaction(portfolioId, transactionData);

            // If we get here, the request was successful (api.request already handled HTTP errors)
            this.showSuccess('Transaction added successfully!');
            this.clearTransactionForm();
            await this.loadTransactionHistory();
            await this.updateBuilderPortfolioSummary();
        } catch (error) {
            console.error('Error adding transaction:', error);
            this.showError(`Error adding transaction: ${error.message || error}. Please try again.`);
        }
    }

    clearTransactionForm() {
        document.getElementById('transaction-ticker').value = '';
        document.getElementById('transaction-type').value = 'BUY';
        document.getElementById('transaction-shares').value = '';
        document.getElementById('transaction-price').value = '';
        document.getElementById('transaction-fees').value = '';
        document.getElementById('transaction-notes').value = '';

        // Set today's date as default
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('transaction-date').value = today;

        // Reset split UI toggle
        this.onTransactionTypeChange();
    }

    async loadTransactionHistory() {
        const historyContainer = document.getElementById('transaction-history');

        // Get selected portfolio ID
        const portfolioId = this.portfolioManager.getSelectedPortfolioId();
        if (!portfolioId) {
            historyContainer.innerHTML = '<div class="no-transactions">Please select a portfolio first.</div>';
            return;
        }

        try {
            const data = await api.getTransactionHistoryPaginated(portfolioId, {
                page: this.transactionPage,
                pageSize: 20
            });
            const transactions = data.items || [];
            const metadata = data.metadata || {};

            if (transactions.length === 0 && this.transactionPage === 1) {
                historyContainer.innerHTML = '<div class="no-transactions">No transactions yet. Add your first transaction above!</div>';
                return;
            }

            const historyHTML = `
                <div class="transaction-list">
                    ${transactions.map(txn => `
                        <div class="transaction-item ${txn.transaction_type.toLowerCase()}" data-transaction-id="${txn.id}">
                            <div class="transaction-main">
                                <div class="transaction-ticker">${txn.ticker}</div>
                                <div class="transaction-type-badge ${txn.transaction_type.toLowerCase()}">${txn.transaction_type}</div>
                                <div class="transaction-amount">${txn.transaction_type === 'SPLIT' ? `${txn.shares}:1 split` : `${txn.shares} shares @ $${txn.price_per_share.toFixed(2)}`}</div>
                                <div class="transaction-total">${txn.transaction_type === 'SPLIT' ? '-' : `$${txn.total_amount.toFixed(2)}`}</div>
                            </div>
                            <div class="transaction-details">
                                <span class="transaction-date">${new Date(txn.transaction_date).toLocaleDateString()}</span>
                                ${txn.fees > 0 ? `<span class="transaction-fees">Fees: $${txn.fees.toFixed(2)}</span>` : ''}
                                ${txn.notes ? `<span class="transaction-notes">${txn.notes}</span>` : ''}
                            </div>
                            <div class="transaction-actions">
                                <button class="btn-delete-transaction" onclick="window.app.deleteTransaction(${txn.id}, ${portfolioId})">Delete</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <div id="transaction-pagination"></div>
            `;

            historyContainer.innerHTML = historyHTML;

            // Render pagination controls
            if (metadata.total_pages > 1) {
                this.renderPaginationControls('transaction-pagination', metadata, (newPage) => {
                    this.transactionPage = newPage;
                    this.loadTransactionHistory();
                });
            }
        } catch (error) {
            console.error('Error loading transaction history:', error);
            historyContainer.innerHTML = '<div class="error">Error loading transaction history</div>';
        }
    }

    renderPaginationControls(containerId, metadata, onPageChange) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const { page, total_pages, total_items, page_size, has_previous, has_next } = metadata;
        const startItem = (page - 1) * page_size + 1;
        const endItem = Math.min(page * page_size, total_items);

        container.innerHTML = `
            <div class="pagination-controls">
                <button class="pagination-btn pagination-prev" ${!has_previous ? 'disabled' : ''}>Previous</button>
                <div class="pagination-info">
                    <span class="pagination-page">Page ${page} of ${total_pages}</span>
                    <span class="pagination-items">Showing ${startItem}-${endItem} of ${total_items}</span>
                </div>
                <button class="pagination-btn pagination-next" ${!has_next ? 'disabled' : ''}>Next</button>
            </div>
        `;

        const prevBtn = container.querySelector('.pagination-prev');
        const nextBtn = container.querySelector('.pagination-next');

        if (has_previous) {
            prevBtn.addEventListener('click', () => onPageChange(page - 1));
        }
        if (has_next) {
            nextBtn.addEventListener('click', () => onPageChange(page + 1));
        }
    }

    async deleteTransaction(transactionId, portfolioId) {
        if (!confirm('Are you sure you want to delete this transaction? This will update your portfolio holdings.')) {
            return;
        }

        try {
            this.showLoading('Deleting transaction...');
            console.log('Deleting transaction:', transactionId, 'from portfolio:', portfolioId);
            const result = await api.deleteTransaction(portfolioId, transactionId);
            console.log('Delete result:', result);
            this.showSuccess('Transaction deleted successfully!');

            // Reload transaction history and portfolio summary
            await this.loadTransactionHistory();
            await this.updateBuilderPortfolioSummary();

            // Also refresh Dashboard holdings if they're being displayed
            const selectedPortfolioDetails = document.getElementById('selected-portfolio-details');
            if (selectedPortfolioDetails && selectedPortfolioDetails.style.display !== 'none') {
                await this.loadSelectedPortfolioHoldings(portfolioId);
            }

            // Refresh portfolio dashboard if visible
            if (this.portfolioManager) {
                await this.portfolioManager.renderPortfolioDashboard('portfolio-dashboard');
            }
        } catch (error) {
            console.error('Error deleting transaction:', error);
            this.showError(`Failed to delete transaction: ${error.message}`);
        }
    }

    async updateBuilderPortfolioSummary() {
        const summaryContainer = document.getElementById('builder-portfolio-summary');

        try {
            const response = await api.request(`/database/portfolio/${this.currentPortfolioId}/categories-detailed`);

            if (response.ok) {
                const data = await response.json();

                if (!data.categories || data.categories.length === 0) {
                    summaryContainer.innerHTML = '<div class="empty-portfolio">No holdings yet. Add transactions to build your portfolio!</div>';
                    return;
                }

                const totalValue = data.total_portfolio_value || 0;
                const totalPositions = data.total_positions || 0;

                // Calculate total cost basis
                let totalCostBasis = 0;
                data.categories.forEach(category => {
                    totalCostBasis += category.total_cost_basis || 0;
                });

                const totalGainLoss = totalValue - totalCostBasis;
                const totalGainLossPercent = totalCostBasis > 0 ? (totalGainLoss / totalCostBasis) * 100 : 0;
                const gainLossColor = totalGainLoss >= 0 ? '#10b981' : '#ef4444';

                const summaryHTML = `
                    <div class="builder-summary-stats">
                        <div class="builder-stat">
                            <div class="stat-label">Total Value</div>
                            <div class="stat-value">${formatCurrency(totalValue)}</div>
                        </div>
                        <div class="builder-stat">
                            <div class="stat-label">Total Cost</div>
                            <div class="stat-value">${formatCurrency(totalCostBasis)}</div>
                        </div>
                        <div class="builder-stat">
                            <div class="stat-label">Gain/Loss</div>
                            <div class="stat-value" style="color: ${gainLossColor}">
                                ${formatCurrency(totalGainLoss)} (${totalGainLossPercent.toFixed(1)}%)
                            </div>
                        </div>
                        <div class="builder-stat">
                            <div class="stat-label">Positions</div>
                            <div class="stat-value">${totalPositions}</div>
                        </div>
                    </div>
                `;

                summaryContainer.innerHTML = summaryHTML;
            } else {
                summaryContainer.innerHTML = '<div class="error">Failed to load portfolio summary</div>';
            }
        } catch (error) {
            console.error('Error updating portfolio summary:', error);
            summaryContainer.innerHTML = '<div class="error">Error loading portfolio summary</div>';
        }
    }

    showLoading(message) {
        // You can enhance this with a better loading indicator
        console.log(message);
    }

    showSuccess(message) {
        // You can enhance this with a better success notification
        alert(message);
    }

    showError(message) {
        // You can enhance this with a better error notification
        alert(message);
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