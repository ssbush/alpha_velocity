// AlphaVelocity Frontend Application
class AlphaVelocityApp {
    constructor() {
        this.currentView = 'dashboard';
        this.portfolioMode = 'default'; // 'default' or 'custom'
        this.databaseMode = false; // Enable database-backed portfolio management
        this.currentPortfolioId = parseInt(localStorage.getItem('selected_portfolio_id')) || null;
        this.customPortfolio = {};
        this.authManager = null; // Will be initialized in init()
        this.transactionPage = 1; // Current page for transaction history pagination
        this._showWatchlist = false; // Whether to show watchlist candidates in dashboard
        this._watchlistSort = 'score'; // 'score' | 'alpha'
        this.initTheme();
        this.init();
    }

    initUIVersion() {
        const V1_THEMES = ['dark', 'forest', 'slate', 'crt'];
        const V2_THEMES = ['obsidian', 'carbon', 'void'];
        const saved = localStorage.getItem('av_ui_version') || 'v2';
        this._applyUIVersion(saved);

        const v1Btn = document.getElementById('ui-v1-btn');
        const v2Btn = document.getElementById('ui-v2-btn');
        if (v1Btn) v1Btn.addEventListener('click', () => { this._applyUIVersion('v1'); localStorage.setItem('av_ui_version', 'v1'); });
        if (v2Btn) v2Btn.addEventListener('click', () => { this._applyUIVersion('v2'); localStorage.setItem('av_ui_version', 'v2'); });
    }

    _applyUIVersion(version) {
        const isV2 = version === 'v2';
        document.body.classList.toggle('v2', isV2);

        // Sync toggle button active state
        document.getElementById('ui-v1-btn')?.classList.toggle('active', !isV2);
        document.getElementById('ui-v2-btn')?.classList.toggle('active', isV2);

        // Switch to a sensible default theme if crossing the version boundary
        const currentTheme = localStorage.getItem('av_theme') || (isV2 ? 'obsidian' : 'dark');
        const V1_THEMES = ['dark', 'forest', 'slate', 'crt'];
        const V2_THEMES = ['obsidian', 'carbon', 'void'];
        const inWrongGroup = isV2 ? V1_THEMES.includes(currentTheme) : V2_THEMES.includes(currentTheme);
        const newTheme = inWrongGroup ? (isV2 ? 'obsidian' : 'dark') : currentTheme;
        this._applyTheme(newTheme);
        const select = document.getElementById('theme-select');
        if (select) select.value = newTheme;
    }

    initTheme() {
        const ALL_THEMES = ['dark', 'forest', 'slate', 'crt', 'obsidian', 'carbon', 'void'];
        const isV2 = localStorage.getItem('av_ui_version') !== 'v1';
        const defaultTheme = isV2 ? 'obsidian' : 'dark';
        let saved = localStorage.getItem('av_theme') || defaultTheme;
        if (!ALL_THEMES.includes(saved)) saved = defaultTheme;
        this._applyTheme(saved);
        const select = document.getElementById('theme-select');
        if (select) {
            select.value = saved;
            select.addEventListener('change', (e) => {
                this._applyTheme(e.target.value);
                localStorage.setItem('av_theme', e.target.value);
            });
        }
        this.initUIVersion();
    }

    _applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('av_theme', theme);
        if (typeof chartManager !== 'undefined') {
            chartManager.updateChartColors();
        }
    }

    init() {
        // Initialize auth manager
        this.authManager = new AuthManager(window.ALPHAVELOCITY_API_URL || window.location.origin);
        this.authManager.initAuthUI();
        this.authManager.setupEventListeners();

        // Show session-expired message if the user was timed out
        if (localStorage.getItem('av_session_expired') === '1') {
            localStorage.removeItem('av_session_expired');
            setTimeout(() => this.showToast('Your session expired due to inactivity. Please log in again.', 5000), 500);
        }

        // Start session monitor for logged-in users
        if (this.authManager.isLoggedIn()) {
            this.sessionMonitor = new SessionMonitor(this.authManager);
            this.sessionMonitor.start();
        }

        // Initialize portfolio manager
        this.portfolioManager = new PortfolioManager(window.ALPHAVELOCITY_API_URL || window.location.origin, this.authManager);

        // Set auth manager on API instance
        api.setAuthManager(this.authManager);

        this.setupEventListeners();
        this.setupMobileOptimizations();
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

        // IVR badge click — event delegation so it works for dynamically-rendered badges
        document.addEventListener('click', (e) => {
            const badge = e.target.closest('.ivr-badge--clickable');
            if (badge && badge.dataset.ticker) {
                this.showTermStructureModal(badge.dataset.ticker);
            }
        });

        // Search functionality
        const searchBtn = document.getElementById('search-btn');
        const tickerInput = document.getElementById('ticker-input');

        searchBtn.addEventListener('click', () => this.searchStock());
        tickerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchStock();
        });

        // Dashboard watchlist toggle button — just shows/hides already-rendered rows
        const watchlistToggle = document.getElementById('show-watchlist-toggle');
        if (watchlistToggle) {
            watchlistToggle.addEventListener('click', () => {
                this._showWatchlist = !this._showWatchlist;
                watchlistToggle.classList.toggle('active', this._showWatchlist);
                watchlistToggle.textContent = this._showWatchlist ? 'Hide Watchlist' : 'Show Watchlist';
                const container = document.getElementById('selected-portfolio-holdings');
                if (container) {
                    container.classList.toggle('show-watchlist', this._showWatchlist);
                }
            });
        }

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

        // Portfolio comparison controls
        this.setupComparisonControls();

        // Term structure modal close
        const closeTermStructure = document.getElementById('close-term-structure');
        if (closeTermStructure) {
            closeTermStructure.addEventListener('click', () => {
                const modal = document.getElementById('term-structure-modal');
                if (modal) modal.style.display = 'none';
            });
        }
        const termModal = document.getElementById('term-structure-modal');
        if (termModal) {
            termModal.addEventListener('click', (e) => {
                if (e.target === termModal) termModal.style.display = 'none';
            });
        }
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
        // Apply auth-gated nav visibility immediately — before any async work
        this._applyNavVisibility();

        try {
            // Health + DB check in parallel
            const [, ] = await Promise.all([
                api.getHealth(),
                this.checkDatabaseMode()
            ]);

            // Load everything in parallel: user portfolio dashboard + default dashboard items
            const tasks = [
                this.loadPortfolioSummary(),
                this.loadTopMomentum(),
            ];

            if (this.authManager && this.authManager.isLoggedIn()) {
                tasks.push(this.loadUserPortfolioDashboard());
            }

            await Promise.all(tasks);
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

            // Render portfolio list first, then load holdings for the selected portfolio
            await this.portfolioManager.renderPortfolioDashboard('portfolio-dashboard');

            // Use saved selection, or fall back to first portfolio in the list
            let selectedId = this.portfolioManager.getSelectedPortfolioId();
            if (!selectedId) {
                const firstRow = document.querySelector('#portfolio-dashboard .portfolio-row');
                if (firstRow) {
                    selectedId = parseInt(firstRow.dataset.portfolioId);
                    localStorage.setItem('selected_portfolio_id', selectedId);
                    firstRow.classList.add('selected');
                }
            }
            if (selectedId) {
                this.currentPortfolioId = selectedId;
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

        this.currentPortfolioId = portfolioId;

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

            // Get holdings and cash balance
            const holdings = portfolio.holdings || [];
            const cashBalance = portfolio.cash_balance || 0;

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

            // Fetch momentum, watchlist, and category targets in parallel
            const momentumScores = {};
            const currentPrices = {};
            let watchlistByCategory = {};
            const categoryMap = {};

            const holdingTickers = holdings.map(h => h.ticker);

            // Fetch user watchlist first so its tickers are included in the batch momentum call
            const userWatchlistData = await api.getPortfolioWatchlist(portfolioId).catch(() => null);
            const wlOnlyTickers = (userWatchlistData?.items || [])
                .map(i => i.ticker)
                .filter(t => !holdingTickers.includes(t));
            const tickers = [...new Set([...holdingTickers, ...wlOnlyTickers])];

            // Fire all remaining requests in parallel
            const [batchResult, watchlistData, targetsResponse, valueHistory, returnHistory, drawdownHistory, compositeData] = await Promise.all([
                api.getBatchMomentum(tickers).catch(err => {
                    console.warn('Batch momentum fetch failed:', err);
                    return null;
                }),
                api.getWatchlist(0).catch(err => {
                    console.warn('Failed to fetch watchlist:', err);
                    return null;
                }),
                api.getPortfolioCategoryTargets(portfolioId).catch(err => {
                    console.warn('Failed to fetch category targets:', err);
                    return { targets: [] };
                }),
                fetch(`${api.baseURL}/database/portfolio/${portfolioId}/value-history?days=180`)
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null),
                fetch(`${api.baseURL}/database/portfolio/${portfolioId}/return-history?days=180`)
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null),
                fetch(`${api.baseURL}/database/portfolio/${portfolioId}/drawdown-history?days=180`)
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null),
                fetch(`${api.baseURL}/database/portfolio/${portfolioId}/composite-momentum?days=90`)
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null)
            ]);

            // Render value history chart
            const chartSection = document.getElementById('portfolio-value-chart-section');
            if (valueHistory && valueHistory.labels && valueHistory.labels.length > 1) {
                if (chartSection) chartSection.style.display = 'block';
                chartManager.createPortfolioValueChart(
                    'portfolio-value-chart',
                    valueHistory.labels,
                    valueHistory.values,
                    valueHistory.benchmarks || {}
                );
            } else {
                if (chartSection) chartSection.style.display = 'none';
            }

            // Render return comparison chart
            const returnChartSection = document.getElementById('portfolio-return-chart-section');
            if (returnHistory && returnHistory.labels && returnHistory.labels.length > 1) {
                if (returnChartSection) returnChartSection.style.display = 'block';
                chartManager.createReturnComparisonChart(
                    'portfolio-return-chart',
                    returnHistory.labels,
                    returnHistory.portfolio_twr,
                    returnHistory.benchmarks || {}
                );
            } else {
                if (returnChartSection) returnChartSection.style.display = 'none';
            }

            // Render composite momentum score
            const compositeSection = document.getElementById('portfolio-composite-momentum-section');
            if (compositeData && compositeData.current_score !== null) {
                if (compositeSection) compositeSection.style.display = 'block';
                const score = compositeData.current_score;
                const scoreEl = document.getElementById('composite-score-value');
                const ratingEl = document.getElementById('composite-score-rating');
                const coverageEl = document.getElementById('composite-score-coverage');
                const color = score >= 75 ? '#10b981' : score >= 60 ? '#3b82f6' : score >= 45 ? '#f59e0b' : '#ef4444';
                if (scoreEl) { scoreEl.textContent = score.toFixed(1); scoreEl.style.color = color; }
                if (ratingEl) { ratingEl.textContent = compositeData.current_rating; ratingEl.style.color = color; ratingEl.style.background = color + '20'; }
                if (coverageEl) coverageEl.textContent = `${compositeData.scored_holdings} of ${compositeData.total_holdings} holdings scored`;
                if (compositeData.history.length > 1) {
                    chartManager.createMomentumSparkline('composite-momentum-sparkline', compositeData.history);
                }
            } else {
                if (compositeSection) compositeSection.style.display = 'none';
            }

            // Render drawdown chart
            const drawdownChartSection = document.getElementById('portfolio-drawdown-chart-section');
            if (drawdownHistory && drawdownHistory.labels && drawdownHistory.labels.length > 1) {
                if (drawdownChartSection) drawdownChartSection.style.display = 'block';

                // Build drawdown stats block
                const statsEl = document.getElementById('portfolio-drawdown-stats');
                if (statsEl) {
                    const ddSeries = { 'Portfolio': drawdownHistory.portfolio, ...(drawdownHistory.benchmarks || {}) };
                    const ddColors = { Portfolio: getComputedStyle(document.documentElement).getPropertyValue('--chart-secondary').trim() || '#7c3aed', SPY: '#94a3b8', QQQ: '#10b981', MTUM: '#38bdf8', AIQ: '#f472b6' };
                    const cards = Object.entries(ddSeries).map(([name, series]) => {
                        const valid = series.filter(v => v !== null);
                        if (!valid.length) return '';
                        const maxDD = Math.min(...valid);
                        const currentDD = valid[valid.length - 1];
                        const color = ddColors[name] || '#9ca3af';
                        const fmt = v => v.toFixed(1) + '%';
                        return `<div class="stat-card" style="padding: 0.875rem 1rem; border-top: 3px solid ${color};">
                            <div style="font-size: 0.75rem; font-weight: 600; color: ${color}; margin-bottom: 0.5rem; letter-spacing: 0.05em;">${name}</div>
                            <div style="display: flex; gap: 1.5rem;">
                                <div>
                                    <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.15rem;">Max DD</div>
                                    <div style="font-size: 1rem; font-weight: 700; color: ${maxDD < -10 ? '#ef4444' : maxDD < -5 ? '#f59e0b' : '#10b981'};">${fmt(maxDD)}</div>
                                </div>
                                <div>
                                    <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.15rem;">Current</div>
                                    <div style="font-size: 1rem; font-weight: 700; color: ${currentDD < -10 ? '#ef4444' : currentDD < -5 ? '#f59e0b' : currentDD < -1 ? '#9ca3af' : '#10b981'};">${fmt(currentDD)}</div>
                                </div>
                            </div>
                        </div>`;
                    }).join('');
                    statsEl.innerHTML = `<div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 0;">${cards}</div>`;
                }

                chartManager.createDrawdownChart(
                    'portfolio-drawdown-chart',
                    drawdownHistory.labels,
                    drawdownHistory.portfolio,
                    drawdownHistory.benchmarks || {}
                );
            } else {
                if (drawdownChartSection) drawdownChartSection.style.display = 'none';
            }

            // Process batch momentum results
            if (batchResult && batchResult.data) {
                for (const [ticker, data] of Object.entries(batchResult.data)) {
                    momentumScores[ticker] = data;
                    if (data.current_price) {
                        currentPrices[ticker] = data.current_price;
                    }
                }
            }

            // Process auto-generated watchlist candidates
            if (watchlistData && watchlistData.categories) {
                for (const [catName, catData] of Object.entries(watchlistData.categories)) {
                    if (catData.candidates && catData.candidates.length > 0) {
                        watchlistByCategory[catName] = catData.candidates;
                    }
                }
            }

            // Merge user-saved watchlist tickers (Builder tab) into the category buckets
            if (userWatchlistData && userWatchlistData.items) {
                const holdingTickerSet = new Set(holdingTickers);
                const autoWlTickers = new Set(
                    Object.values(watchlistByCategory).flatMap(cands => cands.map(c => c.ticker))
                );
                for (const item of userWatchlistData.items) {
                    // Skip tickers already in the portfolio (they have their own row)
                    if (holdingTickerSet.has(item.ticker)) continue;
                    const bucket = item.category || 'Watchlist';
                    if (!watchlistByCategory[bucket]) watchlistByCategory[bucket] = [];
                    // Avoid duplicates with auto-generated candidates
                    if (!autoWlTickers.has(item.ticker)) {
                        watchlistByCategory[bucket].push({
                            ticker: item.ticker,
                            composite_score: item.momentum_score,
                            rating: item.rating,
                            current_price: currentPrices[item.ticker] || null,
                        });
                    }
                }
            }

            // Process category targets
            if (targetsResponse && targetsResponse.targets) {
                targetsResponse.targets.forEach(target => {
                    categoryMap[target.category_name] = {
                        target_allocation: target.target_allocation_pct / 100,
                        benchmark: target.benchmark
                    };
                });
            }

            // Helper function to get score color
            const getScoreColor = (score) => {
                const s = getComputedStyle(document.documentElement);
                if (score >= 80) return s.getPropertyValue('--score-strong-buy').trim() || '#10b981';
                if (score >= 70) return s.getPropertyValue('--score-buy').trim() || '#3b82f6';
                if (score >= 60) return s.getPropertyValue('--score-hold').trim() || '#f59e0b';
                if (score >= 50) return s.getPropertyValue('--score-weak-hold').trim() || '#ef4444';
                return s.getPropertyValue('--score-sell').trim() || '#dc2626';
            };

            // Helper function to get rating color
            const getRatingColor = (rating) => {
                const s = getComputedStyle(document.documentElement);
                const colors = {
                    'Strong Buy': s.getPropertyValue('--score-strong-buy').trim() || '#10b981',
                    'Buy': s.getPropertyValue('--score-buy').trim() || '#3b82f6',
                    'Hold': s.getPropertyValue('--score-hold').trim() || '#f59e0b',
                    'Weak Hold': s.getPropertyValue('--score-weak-hold').trim() || '#ef4444',
                    'Sell': s.getPropertyValue('--score-sell').trim() || '#dc2626',
                };
                return colors[rating] || (s.getPropertyValue('--score-neutral').trim() || '#6b7280');
            };

            // Group holdings by category and calculate values (using current prices)
            const holdingsByCategory = {};
            let totalPortfolioValue = cashBalance;  // include cash in total

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

            // Merge watchlist candidates into holdingsByCategory (rendered hidden by default)
            for (const [catName, candidates] of Object.entries(watchlistByCategory)) {
                if (!holdingsByCategory[catName]) {
                    holdingsByCategory[catName] = { holdings: [], totalValue: 0 };
                }
                candidates.forEach(c => {
                    holdingsByCategory[catName].holdings.push({
                        ticker: c.ticker,
                        shares: 0,
                        average_cost_basis: null,
                        total_cost_basis: null,
                        category: catName,
                        _isWatchlist: true,
                        _wlScore: c.composite_score,
                        _wlRating: c.rating,
                        _wlPrice: c.current_price
                    });
                });
            }

            // Display holdings grouped by category
            detailsSection.style.display = 'block';
            let holdingsHTML = '';

            // Sort categories by target allocation (descending)
            const sortedCategories = Object.keys(holdingsByCategory).sort((a, b) => {
                const targetA = (categoryMap[a] || { target_allocation: 0 }).target_allocation;
                const targetB = (categoryMap[b] || { target_allocation: 0 }).target_allocation;
                return targetB - targetA;
            });

            // Attach targetPct to each category bucket (used by v2 renderer)
            sortedCategories.forEach(catName => {
                holdingsByCategory[catName].targetPct =
                    ((categoryMap[catName] || { target_allocation: 0 }).target_allocation * 100).toFixed(1);
            });

            // v2 render path — early return after rendering
            if (this._isV2()) {
                const v2HTML = this._renderHoldingsV2(holdingsByCategory, momentumScores, currentPrices, watchlistByCategory, totalPortfolioValue, cashBalance);
                holdingsContainer.innerHTML = v2HTML;
                this._setupV2CardBehaviors(holdingsContainer);
                holdingsContainer.classList.toggle('show-watchlist', this._showWatchlist);
                // Include user watchlist tickers in IVR population
                const userWlTickers = userWatchlistData?.items?.map(i => i.ticker) || [];
                const allIvrTickers = [...new Set([...tickers, ...userWlTickers])];
                this._populateIVRCells(allIvrTickers);
                // Build ticker→category map from holdings for heatmap grouping
                const tickerCategoryMap = {};
                holdings.forEach(h => { if (h.ticker) tickerCategoryMap[h.ticker] = h.category || 'Uncategorized'; });
                this._loadCorrelationMatrix(portfolioId, null, tickerCategoryMap, sortedCategories);
                return;
            }

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
                                        <th title="IV Rank: measures how elevated implied volatility is vs. the past 52 weeks. ≥50 = sell premium, &lt;30 = cheap hedge.">IVR</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${categoryData.holdings.map(h => {
                                        const isWL = h._isWatchlist;

                                        // For watchlist rows, use embedded data; for holdings, use fetched momentum
                                        const momentum = isWL ? null : momentumScores[h.ticker];
                                        const score = isWL ? h._wlScore : (momentum ? momentum.composite_score : null);
                                        const rating = isWL ? h._wlRating : (momentum ? momentum.rating : null);
                                        const scoreColor = score ? getScoreColor(score) : '#6b7280';
                                        const ratingColor = rating ? getRatingColor(rating) : '#6b7280';

                                        // Calculate current value (not applicable for watchlist)
                                        const currentPrice = isWL ? h._wlPrice : currentPrices[h.ticker];
                                        const currentValue = (!isWL && currentPrice) ? currentPrice * h.shares : null;
                                        const costBasis = h.total_cost_basis || 0;
                                        const gainLoss = currentValue ? currentValue - costBasis : null;
                                        const gainLossPercent = (costBasis > 0 && gainLoss !== null) ? (gainLoss / costBasis) * 100 : null;
                                        const gainLossColor = gainLoss !== null ? (gainLoss >= 0 ? '#10b981' : '#ef4444') : '#6b7280';

                                        const rowClass = isWL ? ' class="watchlist-row"' : '';
                                        const dash = '<span style="color: #6b7280;">—</span>';

                                        return `
                                            <tr${rowClass}>
                                                <td class="ticker-cell">${h.ticker}${isWL ? ' <span class="wl-badge">WL</span>' : ''}</td>
                                                <td>${isWL ? dash : h.shares.toFixed(2)}</td>
                                                <td>${isWL ? dash : ('$' + (h.average_cost_basis ? h.average_cost_basis.toFixed(2) : '—'))}</td>
                                                <td>${isWL ? dash : ('$' + (h.total_cost_basis ? h.total_cost_basis.toFixed(2) : '—'))}</td>
                                                <td>
                                                    ${currentPrice != null ?
                                                        `$${Number(currentPrice).toFixed(2)}`
                                                        : dash}
                                                </td>
                                                <td>
                                                    ${currentValue !== null ?
                                                        `<strong>$${currentValue.toFixed(2)}</strong>`
                                                        : dash}
                                                </td>
                                                <td style="color: ${gainLossColor}; font-weight: 600;">
                                                    ${gainLoss !== null ?
                                                        `$${gainLoss.toFixed(2)} (${gainLossPercent.toFixed(1)}%)`
                                                        : dash}
                                                </td>
                                                <td>
                                                    ${score !== null && score !== undefined ?
                                                        `<span class="momentum-score" style="color: ${scoreColor}; font-weight: 600;">${Number(score).toFixed(1)}</span>`
                                                        : dash}
                                                </td>
                                                <td>
                                                    ${rating ?
                                                        `<span class="rating-badge" style="background: ${ratingColor}20; color: ${ratingColor}; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 600;">${rating}</span>`
                                                        : dash}
                                                </td>
                                                <td class="ivr-cell" data-ticker="${h.ticker}">
                                                    <span style="color: #6b7280; font-size: 0.7rem;">…</span>
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

            // Sync show-watchlist class with current toggle state
            holdingsContainer.classList.toggle('show-watchlist', this._showWatchlist);

            // Async IVR population — fetch per ticker and update cells as results arrive
            this._populateIVRCells(tickers);
        } catch (error) {
            console.error('Error loading portfolio holdings:', error);
            detailsSection.style.display = 'none';
        }
    }

    async loadBuilderWatchlist() {
        const container = document.getElementById('builder-watchlist');
        if (!container) return;
        const portfolioId = this.portfolioManager?.getSelectedPortfolioId() || this.currentPortfolioId;
        if (!portfolioId) {
            container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">Select a portfolio to manage its watchlist.</p>';
            return;
        }
        try {
            const data = await api.getPortfolioWatchlist(portfolioId);
            this._renderBuilderWatchlist(data.items, portfolioId);
        } catch (e) {
            container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">Could not load watchlist.</p>';
        }
    }

    setWatchlistSort(sort) {
        this._watchlistSort = sort;
        document.getElementById('wl-sort-score')?.classList.toggle('active', sort === 'score');
        document.getElementById('wl-sort-alpha')?.classList.toggle('active', sort === 'alpha');
        // Re-render with current items stored on the container
        const container = document.getElementById('builder-watchlist');
        if (container?._watchlistData) {
            this._renderBuilderWatchlist(container._watchlistData.items, container._watchlistData.portfolioId);
        }
    }

    _renderBuilderWatchlist(items, portfolioId) {
        const container = document.getElementById('builder-watchlist');
        if (!container) return;
        // Store data for re-render on sort change
        container._watchlistData = { items, portfolioId };
        if (!items.length) {
            container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem;">No tickers on the watchlist yet. Add one above or use "Populate from Categories".</p>';
            return;
        }
        // Sort
        const sorted = [...items].sort((a, b) => {
            if (this._watchlistSort === 'alpha') return a.ticker.localeCompare(b.ticker);
            // Score descending; nulls last
            const sa = a.momentum_score ?? -1;
            const sb = b.momentum_score ?? -1;
            return sb - sa;
        });
        const dash = '<span style="color: var(--text-muted)">—</span>';
        container.innerHTML = sorted.map(item => {
            const score = item.momentum_score;
            const scoreColor = score ? getScoreColor(score) : 'var(--text-muted)';
            const ratingColor = item.rating ? getRatingColor(item.rating) : 'var(--text-muted)';
            return `
                <div class="wl-builder-item">
                    <strong class="wl-builder-ticker">${item.ticker}</strong>
                    <span class="wl-builder-score" style="color: ${scoreColor}">${score != null ? score.toFixed(1) : dash}</span>
                    <span class="wl-builder-rating" style="background: ${item.rating ? ratingColor + '20' : 'transparent'}; color: ${ratingColor}">${item.rating || dash}</span>
                    <button class="remove-ticker-btn-table" onclick="app.removeFromBuilderWatchlist('${item.ticker}', ${portfolioId})" title="Remove">×</button>
                </div>
            `;
        }).join('');
    }

    async addToBuilderWatchlist() {
        const input = document.getElementById('watchlist-add-input');
        const ticker = input?.value.trim().toUpperCase();
        if (!ticker) return;
        const portfolioId = this.portfolioManager?.getSelectedPortfolioId() || this.currentPortfolioId;
        if (!portfolioId) { this.showError('Select a portfolio first'); return; }
        try {
            const data = await api.addToPortfolioWatchlist(portfolioId, [ticker]);
            input.value = '';
            this._renderBuilderWatchlist(data.items, portfolioId);
        } catch (e) {
            this.showError(`Could not add ${ticker} to watchlist`);
        }
    }

    async removeFromBuilderWatchlist(ticker, portfolioId) {
        try {
            await api.removeFromPortfolioWatchlist(portfolioId, ticker);
            const data = await api.getPortfolioWatchlist(portfolioId);
            this._renderBuilderWatchlist(data.items, portfolioId);
        } catch (e) {
            this.showError(`Could not remove ${ticker}`);
        }
    }

    async populateWatchlistFromCategories() {
        const portfolioId = this.portfolioManager?.getSelectedPortfolioId() || this.currentPortfolioId;
        if (!portfolioId) { this.showError('Select a portfolio first'); return; }
        const btn = document.getElementById('populate-watchlist-btn');
        if (btn) btn.disabled = true;
        try {
            const data = await api.populateWatchlistFromCategories(portfolioId);
            this._renderBuilderWatchlist(data.items, portfolioId);
            this.showSuccess(`Watchlist updated — ${data.count} ticker(s)`);
        } catch (e) {
            this.showError('Could not populate watchlist');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // ─── V2 HOLDINGS RENDER ────────────────────────────────────────────

    _isV2() { return document.body.classList.contains('v2'); }

    _renderHoldingsV2(holdingsByCategory, momentumScores, currentPrices, watchlistByCategory, totalPortfolioValue = 0, cashBalance = 0) {
        const collapseState = JSON.parse(localStorage.getItem('av_v2_collapse') || '{}');
        const cardOrder = JSON.parse(localStorage.getItem('av_v2_order') || '[]');
        const dash = '<span style="color: var(--text-muted)">—</span>';

        // Sort categories by saved order
        let categories = Object.keys(holdingsByCategory);
        if (cardOrder.length) {
            categories = [...cardOrder.filter(c => categories.includes(c)),
                          ...categories.filter(c => !cardOrder.includes(c))];
        }

        const cashPct = cashBalance !== 0 && totalPortfolioValue > 0
            ? (cashBalance / totalPortfolioValue * 100).toFixed(1)
            : null;
        const cashCard = cashBalance !== 0 ? `
            <div class="category-section" data-category="__cash__">
                <div class="v2-card-header" data-category="__cash__">
                    <span class="v2-drag-handle" style="visibility:hidden">⠿</span>
                    <span class="v2-cat-name">Cash</span>
                    <div class="v2-cat-stats">
                        ${cashPct !== null ? `<span class="v2-alloc${cashBalance < 0 ? ' underweight' : ''}"><span class="stat-value">${cashPct}%</span></span>` : ''}
                        <span style="font-size:0.8rem;font-weight:600;color:${cashBalance < 0 ? '#ef4444' : '#10b981'}">$${Math.abs(cashBalance).toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2})}</span>
                    </div>
                </div>
            </div>` : '';

        return categories.map(catName => {
            const catData = holdingsByCategory[catName];
            const isCollapsed = collapseState[catName] ?? false;

            // Aggregate stats
            const scored = catData.holdings.filter(h => !h._isWatchlist && momentumScores[h.ticker]);
            const avgScore = scored.length
                ? (scored.reduce((s, h) => s + (momentumScores[h.ticker]?.composite_score || 0), 0) / scored.length).toFixed(1)
                : null;
            const totalValue = catData.holdings
                .filter(h => !h._isWatchlist && currentPrices[h.ticker])
                .reduce((s, h) => s + currentPrices[h.ticker] * h.shares, 0);
            const target = catData.targetPct != null ? parseFloat(catData.targetPct) : null;
            const actualPct = totalPortfolioValue > 0 ? (totalValue / totalPortfolioValue * 100) : null;

            // Allocation indicator
            let allocClass = '';
            let allocIcon = '';
            if (target !== null && actualPct !== null) {
                if (actualPct > target + 0.5)      { allocClass = 'overweight';  allocIcon = '▲'; }
                else if (actualPct < target - 0.5) { allocClass = 'underweight'; allocIcon = '▼'; }
            }

            const statsHtml = `
                <div class="v2-cat-stats">
                    ${actualPct !== null ? `<span class="tip-label v2-alloc ${allocClass}"><span class="stat-value">${actualPct.toFixed(1)}%</span>${allocIcon ? `<span class="alloc-icon">${allocIcon}</span>` : ''}</span>` : ''}
                    ${target !== null ? `<span class="tip-label v2-alloc-target">/ ${target.toFixed(1)}% target</span>` : ''}
                </div>`;

            const rows = catData.holdings.map(h => {
                const isWL = h._isWatchlist;
                const momentum = isWL ? null : momentumScores[h.ticker];
                const score = isWL ? h._wlScore : (momentum?.composite_score ?? null);
                const rating = isWL ? h._wlRating : (momentum?.rating ?? null);
                const scoreColor = score ? getScoreColor(score) : 'var(--text-muted)';
                const ratingColor = rating ? getRatingColor(rating) : 'var(--text-muted)';
                const currentPrice = isWL ? h._wlPrice : currentPrices[h.ticker];
                const currentValue = (!isWL && currentPrice) ? currentPrice * h.shares : null;
                const costBasis = h.total_cost_basis || 0;
                const gainLoss = currentValue ? currentValue - costBasis : null;
                const gainLossPct = (costBasis > 0 && gainLoss !== null) ? (gainLoss / costBasis) * 100 : null;
                const glColor = gainLoss !== null ? (gainLoss >= 0 ? '#10b981' : '#ef4444') : 'var(--text-muted)';

                const tooltip = !isWL ? `
                    <span class="v2-pos-tooltip">
                        <span class="tip-row"><span class="tip-label">Shares</span><span class="tip-val">${h.shares?.toFixed(4) ?? '—'}</span></span>
                        <span class="tip-row"><span class="tip-label">Avg Cost</span><span class="tip-val">${h.average_cost_basis ? '$' + Number(h.average_cost_basis).toFixed(2) : '—'}</span></span>
                        <span class="tip-row"><span class="tip-label">Total Cost</span><span class="tip-val">${h.total_cost_basis ? '$' + Number(h.total_cost_basis).toFixed(2) : '—'}</span></span>
                    </span>` : '';

                return `
                    <tr class="${isWL ? 'v2-watchlist-row' : ''}">
                        <td class="v2-ticker-cell">
                            <span class="v2-ticker-name">${h.ticker}</span>
                            ${isWL ? '<span class="v2-wl-badge">WL</span>' : ''}
                            ${tooltip}
                        </td>
                        <td>${currentPrice != null ? '$' + Number(currentPrice).toFixed(2) : dash}</td>
                        <td>${currentValue != null ? '<strong>$' + currentValue.toFixed(0) + '</strong>' : dash}</td>
                        <td style="color:${glColor}; font-weight:600">
                            ${gainLoss !== null ? '$' + (Math.abs(gainLoss) < 1 ? gainLoss.toFixed(2) : gainLoss.toFixed(0)) + (gainLossPct !== null ? ' (' + gainLossPct.toFixed(1) + '%)' : '') : dash}
                        </td>
                        <td>${score != null ? `<span style="color:${scoreColor};font-weight:700">${Number(score).toFixed(1)}</span>` : dash}</td>
                        <td>${rating ? `<span class="rating-badge" style="background:${ratingColor}20;color:${ratingColor}">${rating}</span>` : dash}</td>
                        <td class="ivr-cell" data-ticker="${h.ticker}"><span style="color:var(--text-muted);font-size:0.7rem">…</span></td>
                    </tr>`;
            }).join('');

            return `
                <div class="category-section${isCollapsed ? ' collapsed' : ''}"
                     data-category="${catName}"
                     draggable="true">
                    <div class="v2-card-header" data-category="${catName}">
                        <span class="v2-drag-handle">⠿</span>
                        <span class="v2-cat-name">${catName}</span>
                        ${statsHtml}
                        <button class="v2-collapse-btn" title="Collapse">▼</button>
                    </div>
                    <div class="v2-card-body">
                        <table class="v2-holdings-table">
                            <thead>
                                <tr>
                                    <th>Ticker</th>
                                    <th>Price</th>
                                    <th>Value</th>
                                    <th>Gain/Loss</th>
                                    <th>Score</th>
                                    <th>Rating</th>
                                    <th title="IV Rank">IVR</th>
                                </tr>
                            </thead>
                            <tbody>${rows}</tbody>
                            ${(() => {
                                const totalGainLoss = catData.holdings
                                    .filter(h => !h._isWatchlist && currentPrices[h.ticker])
                                    .reduce((s, h) => {
                                        const val = currentPrices[h.ticker] * h.shares;
                                        const cost = h.total_cost_basis || 0;
                                        return s + (val - cost);
                                    }, 0);
                                const glColor = totalGainLoss >= 0 ? '#10b981' : '#ef4444';
                                const scoreColor = avgScore ? getScoreColor(parseFloat(avgScore)) : 'var(--text-muted)';
                                return `<tfoot class="v2-summary-row">
                                    <tr>
                                        <td>Total</td>
                                        <td></td>
                                        <td>${totalValue > 0 ? '<strong>$' + totalValue.toLocaleString('en-US', {maximumFractionDigits: 0}) + '</strong>' : ''}</td>
                                        <td style="color:${glColor};font-weight:600">${totalValue > 0 ? '$' + (Math.abs(totalGainLoss) < 1 ? totalGainLoss.toFixed(2) : totalGainLoss.toFixed(0)) : ''}</td>
                                        <td>${avgScore ? `<span style="color:${scoreColor};font-weight:700">${avgScore}</span>` : ''}</td>
                                        <td></td>
                                        <td></td>
                                    </tr>
                                </tfoot>`;
                            })()}
                        </table>
                    </div>
                </div>`;
        }).join('') + cashCard;
    }

    _setupV2CardBehaviors(container) {
        // Collapsible headers
        container.querySelectorAll('.v2-card-header').forEach(header => {
            header.addEventListener('click', (e) => {
                if (e.target.closest('.v2-drag-handle')) return;
                const card = header.closest('.category-section');
                card.classList.toggle('collapsed');
                const state = JSON.parse(localStorage.getItem('av_v2_collapse') || '{}');
                state[card.dataset.category] = card.classList.contains('collapsed');
                localStorage.setItem('av_v2_collapse', JSON.stringify(state));
            });
        });

        // Drag-to-reorder
        let dragSrc = null;
        container.querySelectorAll('.category-section[draggable]').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                dragSrc = card;
                e.dataTransfer.effectAllowed = 'move';
                setTimeout(() => card.style.opacity = '0.4', 0);
            });
            card.addEventListener('dragend', () => {
                card.style.opacity = '';
                container.querySelectorAll('.category-section').forEach(c => c.classList.remove('drag-over'));
                // Save new order
                const order = [...container.querySelectorAll('.category-section')].map(c => c.dataset.category);
                localStorage.setItem('av_v2_order', JSON.stringify(order));
            });
            card.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                container.querySelectorAll('.category-section').forEach(c => c.classList.remove('drag-over'));
                if (card !== dragSrc) card.classList.add('drag-over');
            });
            card.addEventListener('drop', (e) => {
                e.preventDefault();
                if (!dragSrc || dragSrc === card) return;
                const cards = [...container.querySelectorAll('.category-section')];
                const srcIdx = cards.indexOf(dragSrc);
                const dstIdx = cards.indexOf(card);
                if (srcIdx < dstIdx) card.after(dragSrc);
                else card.before(dragSrc);
            });
        });
    }

    async _populateIVRCells(tickers) {
        // Deduplicate (watchlist rows share tickers with holdings)
        const unique = [...new Set(tickers)];

        // Fetch IVR for each ticker; update the cell as each result arrives
        await Promise.all(unique.map(async ticker => {
            try {
                const data = await api.getIVData(ticker);
                const cells = document.querySelectorAll(`.ivr-cell[data-ticker="${ticker}"]`);
                cells.forEach(cell => {
                    cell.innerHTML = this._renderIVRBadge(data);
                });
            } catch (e) {
                // Leave the placeholder as-is on error
            }
        }));
    }

    _renderIVRBadge(data) {
        const ivPct = data.iv != null ? `IV ${(data.iv * 100).toFixed(0)}%` : '—';
        const earningsNote = data.earnings_dte != null
            ? ` | Earnings in ${data.earnings_dte}d`
            : '';

        // Earnings imminent — override everything with a warning
        if (data.earnings_warning) {
            const title = `Earnings in ${data.earnings_dte} day(s) — IV spike is earnings premium, not a true sell signal. ${ivPct}`;
            return `<span class="ivr-badge" style="background: #f59e0b20; color: #f59e0b; padding: 0.2rem 0.45rem; border-radius: 0.25rem; font-size: 0.72rem; font-weight: 600; cursor: default; white-space: nowrap;" title="${title}">Earn ${data.earnings_dte}d</span>`;
        }

        const MIN_IVR_POINTS = 60;
        if (data.ivr === null || data.ivr === undefined || data.data_points < MIN_IVR_POINTS) {
            const pct = data.data_points > 0
                ? Math.round(data.data_points / MIN_IVR_POINTS * 100)
                : 0;
            const title = `Building IV history — ${data.data_points}/${MIN_IVR_POINTS} snapshots (${pct}%). IVR signal activates at ${MIN_IVR_POINTS} days.${ivPct !== '—' ? ' ' + ivPct : ''}${earningsNote}`;
            return `<span style="color: #6b7280; font-size: 0.72rem; cursor: default; white-space: nowrap;" title="${title}">~${pct}%</span>`;
        }

        const ivr = data.ivr;
        let color, label;
        if (ivr >= 50) {
            color = '#ef4444'; label = 'Sell';
        } else if (ivr < 30) {
            color = '#10b981'; label = 'Hedge';
        } else {
            color = '#f59e0b'; label = 'Neutral';
        }

        const rangeStr = `52w: ${data.iv_52w_low != null ? (data.iv_52w_low*100).toFixed(0)+'%' : '?'}–${data.iv_52w_high != null ? (data.iv_52w_high*100).toFixed(0)+'%' : '?'}`;
        const title = `IVR ${ivr} — ${data.signal}. ${ivPct}. ${rangeStr}${earningsNote}`;

        return `<span class="ivr-badge ivr-badge--clickable" data-ticker="${data.ticker}" style="background: ${color}20; color: ${color}; padding: 0.2rem 0.45rem; border-radius: 0.25rem; font-size: 0.72rem; font-weight: 600; cursor: pointer; white-space: nowrap;" title="${title}">${ivr} ${label}</span>`;
    }

    async _loadCorrelationMatrix(portfolioId, days = null, tickerCategoryMap = {}, categoryOrder = []) {
        const section = document.getElementById('correlation-matrix-section');
        const container = document.getElementById('correlation-matrix-container');
        const select = document.getElementById('correlation-days-select');
        if (!section || !container) return;

        const d = days || (select ? parseInt(select.value, 10) : 90);

        // Wire up the day selector once; preserve category context across day changes
        if (select && !select._wired) {
            select._wired = true;
            select.addEventListener('change', () => {
                this._loadCorrelationMatrix(portfolioId, parseInt(select.value, 10), tickerCategoryMap, categoryOrder);
            });
        }

        section.style.display = 'block';
        const loading = document.createElement('p');
        loading.style.cssText = 'color: var(--text-secondary); font-size: 0.8rem; padding: 0.5rem 0;';
        loading.textContent = 'Loading correlations…';
        container.innerHTML = '';
        container.appendChild(loading);

        try {
            const data = await api.getCorrelationMatrix(portfolioId, d);
            if (data && data.tickers && data.tickers.length >= 2) {

                // --- Reorder tickers by category ---
                // Build sorted ticker list: follow categoryOrder, then alphabetical within each category
                const apiTickerSet = new Set(data.tickers);
                const sortedTickers = [];
                const categoryGroups = [];  // [{name, count}, ...] for divider rendering

                const usedOrder = categoryOrder.length > 0 ? categoryOrder : [...data.tickers].sort();

                usedOrder.forEach(catName => {
                    const inCat = data.tickers.filter(t =>
                        apiTickerSet.has(t) && (tickerCategoryMap[t] || 'Uncategorized') === catName
                    ).sort();
                    if (inCat.length > 0) {
                        inCat.forEach(t => sortedTickers.push(t));
                        categoryGroups.push({ name: catName, count: inCat.length });
                    }
                });

                // Any tickers not matched to a known category go at the end
                const uncategorised = data.tickers.filter(t => !sortedTickers.includes(t)).sort();
                if (uncategorised.length > 0) {
                    uncategorised.forEach(t => sortedTickers.push(t));
                    categoryGroups.push({ name: 'Other', count: uncategorised.length });
                }

                // Remap the matrix to the new ticker order
                const origIdx = {};
                data.tickers.forEach((t, i) => { origIdx[t] = i; });
                const reorderedMatrix = sortedTickers.map(rowT =>
                    sortedTickers.map(colT => data.matrix[origIdx[rowT]][origIdx[colT]])
                );

                // Compute average pairwise correlation on the reordered matrix
                const n = sortedTickers.length;
                let sum = 0, count = 0;
                for (let i = 0; i < n; i++) {
                    for (let j = 0; j < n; j++) {
                        if (i !== j && reorderedMatrix[i][j] !== null) {
                            sum += reorderedMatrix[i][j];
                            count++;
                        }
                    }
                }
                const avgCorr = count > 0 ? sum / count : null;

                // renderCorrelationHeatmap clears the container — call it first,
                // then prepend the stat card and append the footer note.
                chartManager.renderCorrelationHeatmap(container, sortedTickers, reorderedMatrix, categoryGroups);

                // Prepend stat card above heatmap
                if (avgCorr !== null) {
                    let corrLabel, corrColor;
                    if (avgCorr >= 0.7)      { corrLabel = 'High — concentrated factor bet'; corrColor = '#ef4444'; }
                    else if (avgCorr >= 0.4) { corrLabel = 'Moderate — some diversification'; corrColor = '#f59e0b'; }
                    else                     { corrLabel = 'Low — meaningful diversification'; corrColor = '#10b981'; }

                    const statCard = document.createElement('div');
                    statCard.style.cssText = 'display: flex; align-items: baseline; gap: 0.6rem; margin-bottom: 0.75rem; padding: 0.5rem 0.75rem; background: var(--surface-alt); border-radius: 0.3rem; border: 1px solid var(--border-subtle);';
                    const valueSpan = document.createElement('span');
                    valueSpan.style.cssText = `font-size: 1.4rem; font-weight: 700; color: ${corrColor}; line-height: 1;`;
                    valueSpan.textContent = avgCorr.toFixed(2);
                    const labelSpan = document.createElement('span');
                    labelSpan.style.cssText = 'font-size: 0.75rem; color: var(--text-secondary);';
                    labelSpan.textContent = `avg pairwise correlation — ${corrLabel}`;
                    statCard.appendChild(valueSpan);
                    statCard.appendChild(labelSpan);
                    container.insertBefore(statCard, container.firstChild);
                }

                // Append footer note
                const note = document.createElement('p');
                note.style.cssText = 'font-size: 0.65rem; color: var(--text-muted); margin-top: 0.4rem; text-align: right;';
                const sourceLabel = data.source === 'yfinance' ? ' · via yfinance' : data.source === 'mixed' ? ' · DB + yfinance' : '';
                note.textContent = `${data.data_points} trading days · ${data.start_date} → ${data.end_date}${sourceLabel}`;
                container.appendChild(note);
            } else {
                container.innerHTML = '';
                const msg = document.createElement('p');
                msg.style.cssText = 'color: var(--text-secondary); font-size: 0.8rem;';
                msg.textContent = 'Not enough price history for correlation analysis.';
                container.appendChild(msg);
            }
        } catch (e) {
            section.style.display = 'none';
        }
    }

    async showTermStructureModal(ticker) {
        const modal = document.getElementById('term-structure-modal');
        const titleEl = document.getElementById('term-structure-title');
        const loadingEl = document.getElementById('term-structure-loading');
        const canvas = document.getElementById('term-structure-chart');
        if (!modal) return;

        // Reset state
        if (titleEl) titleEl.textContent = ticker;
        if (loadingEl) loadingEl.style.display = 'block';
        if (canvas) canvas.style.display = 'none';
        modal.style.display = 'flex';

        try {
            const data = await api.getTermStructure(ticker);
            if (data && data.points && data.points.length > 0) {
                if (loadingEl) loadingEl.style.display = 'none';
                if (canvas) canvas.style.display = 'block';
                chartManager.createTermStructureChart('term-structure-chart', data.points, ticker);
            } else {
                if (loadingEl) loadingEl.textContent = 'No options data available for ' + ticker;
            }
        } catch (e) {
            if (loadingEl) loadingEl.textContent = 'Failed to load term structure.';
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

            const elTotal = document.getElementById('total-value');
            const elScore = document.getElementById('avg-score');
            const elCount = document.getElementById('positions-count');
            if (elTotal) elTotal.textContent = formatCurrency(portfolio.total_value || 0);
            if (elScore) elScore.textContent = formatScore(portfolio.average_momentum_score || 0);
            if (elCount) elCount.textContent = portfolio.number_of_positions || 0;
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

                // If we have current market data, use it. Otherwise fall back to cost basis.
                if (holding.current_value != null) {
                    totalValue += parseFloat(holding.current_value);
                } else {
                    totalValue += parseFloat(holding.total_cost_basis);
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

    _applyNavVisibility() {
        const loggedIn = this.authManager && this.authManager.isLoggedIn();
        document.querySelectorAll('.auth-nav').forEach(btn => {
            btn.style.display = loggedIn ? '' : 'none';
        });
        // If not logged in and dashboard tab is active, switch to search
        if (!loggedIn) {
            const activeBtn = document.querySelector('.nav-btn.active');
            if (activeBtn && activeBtn.dataset.view !== 'search') {
                activeBtn.classList.remove('active');
                const searchBtn = document.querySelector('[data-view="search"]');
                // Keep dashboard view active (it holds the leaderboard) but don't highlight it in nav
                // — dashboard view stays visible, nav just doesn't show auth tabs
            }
        }
        // Wire the leaderboard CTA to open the login modal (once only)
        const cta = document.getElementById('leaderboard-login-cta');
        if (cta) {
            if (loggedIn) {
                cta.style.display = 'none';
            } else if (!cta._wired) {
                cta._wired = true;
                cta.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (this.authManager) this.authManager.showLoginModal();
                });
            }
        }
    }

    async loadTopMomentum() {
        const loading = document.getElementById('top-momentum-loading');
        const table = document.getElementById('leaderboard-table');
        const thead = document.getElementById('leaderboard-thead');
        const tbody = document.getElementById('leaderboard-tbody');
        if (!table) return;

        try {
            const result = await api.getTopMomentumStocks(20);
            const stocks = result.stocks || result;
            if (!stocks || stocks.length === 0) throw new Error('No data');

            // Normalise field name — top endpoint uses momentum_score, paginated uses composite_score
            const safeNum = (v) => (v != null && isFinite(Number(v))) ? Number(v) : null;
            const rows = stocks.map((s, i) => ({
                rank: i + 1,
                ticker: s.ticker,
                score: safeNum(s.momentum_score ?? s.composite_score) ?? 0,
                rating: s.rating || '—',
                price: safeNum(s.price ?? s.current_price),
            }));

            this._leaderboardRows = rows;
            this._leaderboardSort = { col: 'score', dir: 'desc' };
            this._renderLeaderboard(thead, tbody, rows);

            if (loading) loading.style.display = 'none';
            table.style.display = 'table';
        } catch (error) {
            if (loading) loading.textContent = 'Failed to load momentum data.';
            console.error('Failed to load top momentum:', error);
        }
    }

    _renderLeaderboard(thead, tbody, rows) {
        const { col, dir } = this._leaderboardSort;

        // Sort a copy
        const sorted = [...rows].sort((a, b) => {
            const av = a[col], bv = b[col];
            if (av === null || av === undefined) return 1;
            if (bv === null || bv === undefined) return -1;
            return dir === 'asc' ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1);
        });

        const arrow = (c) => c === col ? (dir === 'asc' ? ' ↑' : ' ↓') : '';
        const cols = [
            { key: 'rank',   label: '#'      },
            { key: 'ticker', label: 'Ticker' },
            { key: 'score',  label: 'Score'  },
            { key: 'rating', label: 'Rating' },
            { key: 'price',  label: 'Price'  },
        ];

        // Header
        thead.innerHTML = '';
        const tr = document.createElement('tr');
        cols.forEach(({ key, label }) => {
            const th = document.createElement('th');
            th.className = 'leaderboard-th';
            th.textContent = label + arrow(key);
            th.style.cursor = 'pointer';
            th.addEventListener('click', () => {
                if (this._leaderboardSort.col === key) {
                    this._leaderboardSort.dir = this._leaderboardSort.dir === 'asc' ? 'desc' : 'asc';
                } else {
                    this._leaderboardSort.col = key;
                    this._leaderboardSort.dir = key === 'ticker' ? 'asc' : 'desc';
                }
                this._renderLeaderboard(thead, tbody, this._leaderboardRows);
            });
            tr.appendChild(th);
        });
        thead.appendChild(tr);

        // Body
        tbody.innerHTML = '';
        sorted.forEach((row, idx) => {
            const tr = document.createElement('tr');
            tr.className = 'leaderboard-row';

            const rankTd = document.createElement('td');
            rankTd.className = 'leaderboard-td leaderboard-rank';
            rankTd.textContent = idx + 1;
            tr.appendChild(rankTd);

            const tickerTd = document.createElement('td');
            tickerTd.className = 'leaderboard-td leaderboard-ticker';
            tickerTd.textContent = row.ticker;
            tr.appendChild(tickerTd);

            const scoreTd = document.createElement('td');
            scoreTd.className = 'leaderboard-td';
            scoreTd.style.color = getScoreColor(row.score);
            scoreTd.style.fontWeight = '700';
            scoreTd.textContent = row.score.toFixed(1);
            tr.appendChild(scoreTd);

            const ratingTd = document.createElement('td');
            ratingTd.className = 'leaderboard-td';
            ratingTd.style.color = getRatingColor(row.rating);
            ratingTd.textContent = row.rating;
            tr.appendChild(ratingTd);

            const priceTd = document.createElement('td');
            priceTd.className = 'leaderboard-td leaderboard-price';
            priceTd.textContent = row.price != null ? `$${Number(row.price).toFixed(2)}` : '—';
            tr.appendChild(priceTd);

            tbody.appendChild(tr);
        });
    }

    async loadCategoriesData() {
        const container = document.getElementById('categories-grid');
        const loading = document.getElementById('categories-loading');

        try {
            loading.style.display = 'block';

            const [response, holdingsData] = await Promise.all([
                api.getAllCategoriesManagement(),
                this.currentPortfolioId
                    ? api.getPortfolioHoldings(this.currentPortfolioId).catch(() => null)
                    : Promise.resolve(null)
            ]);
            const categories = response.categories;
            const ownedTickers = new Set(
                (holdingsData?.holdings || []).map(h => h.ticker)
            );

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
                        <div class="ticker-grid">
                            ${category.ticker_details.map(detail => {
                                const scoreColor = getScoreColor(detail.momentum_score || 0);
                                const ratingColor = getRatingColor(detail.rating || 'N/A');
                                const owned = ownedTickers.has(detail.ticker);
                                return `
                                    <div class="ticker-grid-item${owned ? ' ticker-grid-item--owned' : ''}">
                                        <strong class="ticker-grid-name">${detail.ticker}</strong>
                                        <span class="ticker-grid-score" style="color: ${scoreColor}">${(detail.momentum_score || 0).toFixed(1)}</span>
                                        <span class="ticker-grid-rating" style="background: ${ratingColor}20; color: ${ratingColor}">${detail.rating || 'N/A'}</span>
                                        ${owned ? '<span class="ticker-owned-dot" title="In your portfolio"></span>' : ''}
                                        <button class="remove-ticker-btn-table" onclick="app.removeTicker(${category.id}, '${detail.ticker}')" title="Remove">×</button>
                                    </div>
                                `;
                            }).join('')}
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
        const overlay = document.getElementById('add-ticker-modal');
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) overlay.remove();
        });
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

    async refreshMomentumScore() {
        const btn = document.getElementById('refresh-momentum-btn');
        if (btn) { btn.textContent = 'Refreshing…'; btn.disabled = true; }
        try {
            await api.refreshMomentumCache(true);
            // Reload the composite score display
            const portfolioId = this.currentPortfolioId;
            if (portfolioId) {
                const compositeData = await fetch(
                    `${api.baseURL}/database/portfolio/${portfolioId}/composite-momentum?days=90`
                ).then(r => r.ok ? r.json() : null).catch(() => null);

                if (compositeData && compositeData.current_score !== null) {
                    const score = compositeData.current_score;
                    const color = score >= 75 ? '#10b981' : score >= 60 ? '#3b82f6' : score >= 45 ? '#f59e0b' : '#ef4444';
                    const scoreEl = document.getElementById('composite-score-value');
                    const ratingEl = document.getElementById('composite-score-rating');
                    const coverageEl = document.getElementById('composite-score-coverage');
                    if (scoreEl) { scoreEl.textContent = score.toFixed(1); scoreEl.style.color = color; }
                    if (ratingEl) { ratingEl.textContent = compositeData.current_rating; ratingEl.style.color = color; ratingEl.style.background = color + '20'; }
                    if (coverageEl) coverageEl.textContent = `${compositeData.scored_holdings} of ${compositeData.total_holdings} holdings scored`;
                    if (compositeData.history.length > 1) {
                        chartManager.createMomentumSparkline('composite-momentum-sparkline', compositeData.history);
                    }
                }
            }
        } catch (err) {
            console.error('Failed to refresh momentum score:', err);
        } finally {
            if (btn) { btn.textContent = 'Refresh Score'; btn.disabled = false; }
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
                                <span class="component-label">Price + Accel (50%)</span>
                                <span class="component-value" style="color: ${getScoreColor(result.price_momentum)}">${formatScore(result.price_momentum)}</span>
                            </div>
                            <div class="component">
                                <span class="component-label">Technical (35%)</span>
                                <span class="component-value" style="color: ${getScoreColor(result.technical_momentum)}">${formatScore(result.technical_momentum)}</span>
                            </div>
                            <div class="component">
                                <span class="component-label">Relative (15%)</span>
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

        // Setup offline detection
        this.setupOfflineDetection();

        // Setup background sync
        this.setupBackgroundSync();

        // Poll for new deploys — show banner if server has newer assets
        this.checkForUpdates();
        setInterval(() => this.checkForUpdates(), 5 * 60 * 1000); // every 5 min
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') this.checkForUpdates();
        });
    }

    async checkForUpdates() {
        try {
            const res = await fetch('/api/version', { cache: 'no-store' });
            if (!res.ok) return;
            const { build_hash } = await res.json();
            const stored = localStorage.getItem('av_build_hash');
            if (stored && stored !== build_hash) {
                this.showUpdateAvailable();
            }
            localStorage.setItem('av_build_hash', build_hash);
        } catch {
            // Network unavailable — silent fail
        }
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

        // Load transaction history, portfolio summary, and watchlist
        await this.loadTransactionHistory();
        await this.updateBuilderPortfolioSummary();
        await this.loadBuilderWatchlist();
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

        const backfillSplitsBtn = document.getElementById('backfill-splits-btn');
        if (backfillSplitsBtn) {
            backfillSplitsBtn.addEventListener('click', () => this.backfillSplits());
        }

        const importBtn = document.getElementById('import-transactions-btn');
        const importFileInput = document.getElementById('import-transactions-file');
        if (importBtn && importFileInput) {
            importBtn.addEventListener('click', () => importFileInput.click());
            importFileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) this.importTransactions(file);
                importFileInput.value = '';
            });
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

        // Watchlist controls
        const populateBtn = document.getElementById('populate-watchlist-btn');
        if (populateBtn) {
            populateBtn.addEventListener('click', () => this.populateWatchlistFromCategories());
        }

        const watchlistAddBtn = document.getElementById('watchlist-add-btn');
        const watchlistAddInput = document.getElementById('watchlist-add-input');
        if (watchlistAddBtn) {
            watchlistAddBtn.addEventListener('click', () => this.addToBuilderWatchlist());
        }
        if (watchlistAddInput) {
            watchlistAddInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.addToBuilderWatchlist();
            });
        }
    }

    onTransactionTypeChange() {
        const type = document.getElementById('transaction-type').value;
        const tickerGroup = document.getElementById('transaction-ticker').closest('.form-group');
        const sharesGroup = document.getElementById('transaction-shares').closest('.form-group');
        const sharesLabel = document.querySelector('label[for="transaction-shares"]');
        const priceLabel = document.querySelector('label[for="transaction-price"]');
        const priceGroup = document.getElementById('transaction-price').closest('.form-group');
        const feesGroup = document.getElementById('transaction-fees').closest('.form-group');
        const dividendGroup = document.getElementById('dividend-amount-group');
        const cashAmountGroup = document.getElementById('cash-amount-group');

        const isCash = type === 'DEPOSIT' || type === 'WITHDRAWAL';

        // Reset to defaults
        if (tickerGroup) tickerGroup.style.display = '';
        if (sharesGroup) sharesGroup.style.display = '';
        if (sharesLabel) sharesLabel.textContent = 'Shares';
        if (priceLabel) priceLabel.textContent = 'Price per Share';
        if (priceGroup) priceGroup.style.display = '';
        if (feesGroup) feesGroup.style.display = '';
        if (dividendGroup) dividendGroup.style.display = 'none';
        if (cashAmountGroup) cashAmountGroup.style.display = 'none';

        if (isCash) {
            if (tickerGroup) tickerGroup.style.display = 'none';
            if (sharesGroup) sharesGroup.style.display = 'none';
            if (priceGroup) priceGroup.style.display = 'none';
            if (feesGroup) feesGroup.style.display = 'none';
            if (cashAmountGroup) cashAmountGroup.style.display = '';
        } else if (type === 'SPLIT') {
            if (sharesLabel) sharesLabel.textContent = 'Split Ratio (e.g., 4 for 4:1)';
            if (priceGroup) priceGroup.style.display = 'none';
            if (feesGroup) feesGroup.style.display = 'none';
        } else if (type === 'REINVEST') {
            if (sharesLabel) sharesLabel.textContent = 'Shares Received';
            if (priceLabel) priceLabel.textContent = 'Price per Share (NAV)';
            if (feesGroup) feesGroup.style.display = 'none';
            if (dividendGroup) dividendGroup.style.display = '';
        }
    }

    async addTransaction() {
        const type = document.getElementById('transaction-type').value;
        const isCash = type === 'DEPOSIT' || type === 'WITHDRAWAL';

        // Route cash transactions separately
        if (isCash) {
            return this._addCashTransaction(type);
        }

        const ticker = document.getElementById('transaction-ticker').value.trim().toUpperCase();
        const shares = parseFloat(document.getElementById('transaction-shares').value);
        const price = parseFloat(document.getElementById('transaction-price').value);
        const date = document.getElementById('transaction-date').value;
        const fees = parseFloat(document.getElementById('transaction-fees').value) || 0;
        const dividendAmount = parseFloat(document.getElementById('transaction-dividend-amount').value) || null;
        const notes = document.getElementById('transaction-notes').value.trim();

        const isSplit = type === 'SPLIT';
        const isReinvest = type === 'REINVEST';

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
            fees: isSplit || isReinvest ? 0 : fees,
            notes: notes || null,
            ...(isReinvest && dividendAmount ? { dividend_amount: dividendAmount } : {})
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
            if (type === 'BUY' || type === 'SELL') await this.loadBuilderWatchlist();
        } catch (error) {
            console.error('Error adding transaction:', error);
            this.showError(`Error adding transaction: ${error.message || error}. Please try again.`);
        }
    }

    async _addCashTransaction(type) {
        const amount = parseFloat(document.getElementById('transaction-cash-amount').value);
        const date = document.getElementById('transaction-date').value;
        const notes = document.getElementById('transaction-notes').value.trim();

        if (!amount || amount <= 0) {
            this.showError('Please enter a valid amount');
            return;
        }
        if (!date) {
            this.showError('Please select a date');
            return;
        }

        const portfolioId = this.portfolioManager.getSelectedPortfolioId();
        if (!portfolioId) {
            this.showError('Please select a portfolio first');
            return;
        }

        try {
            this.showLoading(`Recording ${type.toLowerCase()}...`);
            await api.addCashTransaction(portfolioId, {
                transaction_type: type,
                amount,
                transaction_date: date,
                notes: notes || null
            });
            this.showSuccess(`${type === 'DEPOSIT' ? 'Deposit' : 'Withdrawal'} recorded successfully!`);
            this.clearTransactionForm();
            await this.loadTransactionHistory();
            await this.updateBuilderPortfolioSummary();
        } catch (error) {
            console.error('Error recording cash transaction:', error);
            this.showError(`Error: ${error.message || error}`);
        }
    }

    clearTransactionForm() {
        document.getElementById('transaction-ticker').value = '';
        document.getElementById('transaction-type').value = 'BUY';
        document.getElementById('transaction-shares').value = '';
        document.getElementById('transaction-price').value = '';
        document.getElementById('transaction-fees').value = '';
        document.getElementById('transaction-notes').value = '';
        const cashAmountEl = document.getElementById('transaction-cash-amount');
        if (cashAmountEl) cashAmountEl.value = '';

        // Set today's date as default
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('transaction-date').value = today;

        // Reset split UI toggle
        this.onTransactionTypeChange();
    }

    async backfillSplits() {
        const portfolioId = this.portfolioManager.getSelectedPortfolioId();
        if (!portfolioId) {
            this.showError('Please select a portfolio first');
            return;
        }

        try {
            this.showLoading('Detecting and applying historical splits...');
            const result = await api.backfillSplits(portfolioId);

            const appliedCount = result.applied ? result.applied.length : 0;
            const errorCount = result.errors ? result.errors.length : 0;

            if (appliedCount > 0) {
                const details = result.applied.map(s => `${s.ticker} ${s.ratio}:1 on ${s.date}`).join(', ');
                this.showSuccess(`Applied ${appliedCount} split(s): ${details}`);
                await this.loadTransactionHistory();
                await this.updateBuilderPortfolioSummary();
            } else if (errorCount > 0) {
                const errDetails = result.errors.map(e => `${e.ticker}: ${e.error}`).join(', ');
                this.showError(`Backfill errors: ${errDetails}`);
            } else {
                this.showSuccess('No new splits to apply. All holdings are up to date.');
            }
        } catch (error) {
            console.error('Error backfilling splits:', error);
            this.showError(`Error backfilling splits: ${error.message || error}`);
        }
    }

    async importTransactions(file) {
        const portfolioId = this.portfolioManager.getSelectedPortfolioId();
        if (!portfolioId) {
            this.showError('Please select a portfolio first');
            return;
        }

        try {
            this.showLoading(`Importing transactions from ${file.name}...`);
            const result = await api.uploadTransactions(portfolioId, file);

            let msg = `Imported ${result.imported} transaction(s)`;
            if (result.skipped > 0) msg += `, skipped ${result.skipped}`;
            if (result.errors && result.errors.length > 0) {
                const errDetails = result.errors.map(e => `${e.symbol || '?'} (${e.action}): ${e.reason}`).join('; ');
                msg += `. Errors: ${errDetails}`;
                this.showError(msg);
            } else {
                this.showSuccess(msg);
            }

            if (result.imported > 0) {
                await this.loadTransactionHistory();
                await this.updateBuilderPortfolioSummary();
            }
        } catch (error) {
            console.error('Error importing transactions:', error);
            this.showError(`Import failed: ${error.message || error}`);
        }
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
            const [data, cashData] = await Promise.all([
                api.getTransactionHistoryPaginated(portfolioId, {
                    page: this.transactionPage,
                    pageSize: 20
                }),
                fetch(`${api.baseURL}/user/portfolios/${portfolioId}/cash-transactions?limit=100`, {
                    headers: { ...api.authManager.getAuthHeader() }
                }).then(r => r.ok ? r.json() : { transactions: [], cash_balance: 0 }).catch(() => ({ transactions: [], cash_balance: 0 }))
            ]);
            const transactions = data.items || [];
            const metadata = data.metadata || {};
            const cashTransactions = (cashData.transactions || []).map(t => ({ ...t, _isCash: true }));
            const cashBalance = cashData.cash_balance || 0;

            if (transactions.length === 0 && cashTransactions.length === 0 && this.transactionPage === 1) {
                historyContainer.innerHTML = '<div class="no-transactions">No transactions yet. Add your first transaction above!</div>';
                return;
            }

            // On page 1, merge cash transactions into the list, sorted by date desc
            let allItems = [...transactions];
            if (this.transactionPage === 1 && cashTransactions.length > 0) {
                const merged = [...transactions.map(t => ({ ...t, _date: t.transaction_date })),
                                ...cashTransactions.map(t => ({ ...t, _date: t.transaction_date }))];
                merged.sort((a, b) => b._date.localeCompare(a._date));
                allItems = merged;
            }

            const renderItem = txn => txn._isCash
                ? `<div class="transaction-item ${txn.transaction_type.toLowerCase()}" style="border-left:3px solid var(--accent-light)">
                    <div class="transaction-main">
                        <div class="transaction-ticker">CASH</div>
                        <div class="transaction-type-badge ${txn.transaction_type.toLowerCase()}">${txn.transaction_type}</div>
                        <div class="transaction-amount">${txn.transaction_type === 'DEPOSIT' ? '+' : '-'}$${(txn.amount || 0).toFixed(2)}</div>
                        <div class="transaction-total"></div>
                    </div>
                    <div class="transaction-details">
                        <span class="transaction-date">${new Date(txn.transaction_date).toLocaleDateString()}</span>
                        ${txn.notes ? `<span class="transaction-notes">${txn.notes}</span>` : ''}
                    </div>
                    <div class="transaction-actions"></div>
                  </div>`
                : `<div class="transaction-item ${txn.transaction_type.toLowerCase()}" data-transaction-id="${txn.id}">
                    <div class="transaction-main">
                        <div class="transaction-ticker">${txn.ticker}</div>
                        <div class="transaction-type-badge ${txn.transaction_type.toLowerCase()}">${txn.transaction_type}</div>
                        <div class="transaction-amount">${
                            txn.transaction_type === 'SPLIT' ? `${txn.shares}:1 split` :
                            txn.transaction_type === 'DIVIDEND' ? `Dividend` :
                            `${txn.shares} shares @ $${(txn.price_per_share || 0).toFixed(2)}`
                        }</div>
                        <div class="transaction-total">${txn.transaction_type === 'SPLIT' ? '-' : `$${(txn.total_amount || 0).toFixed(2)}`}</div>
                    </div>
                    <div class="transaction-details">
                        <span class="transaction-date">${new Date(txn.transaction_date).toLocaleDateString()}</span>
                        ${txn.fees > 0 ? `<span class="transaction-fees">Fees: $${txn.fees.toFixed(2)}</span>` : ''}
                        ${txn.notes ? `<span class="transaction-notes">${txn.notes}</span>` : ''}
                    </div>
                    <div class="transaction-actions">
                        <button class="btn-delete-transaction" onclick="window.app.deleteTransaction(${txn.id}, ${portfolioId})">Delete</button>
                    </div>
                  </div>`;

            const cashBalanceBar = cashBalance !== 0 ? `
                <div style="padding:0.5rem 0.75rem;font-size:0.8rem;color:var(--text-secondary);border-bottom:1px solid var(--border);display:flex;justify-content:space-between">
                    <span>Cash Balance</span>
                    <strong style="color:${cashBalance < 0 ? '#ef4444' : '#10b981'}">$${cashBalance.toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:2})}</strong>
                </div>` : '';

            const historyHTML = `
                <div class="transaction-list">
                    ${cashBalanceBar}
                    ${allItems.map(renderItem).join('')}
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
            const portfolioId = this.currentPortfolioId;
            const [detailsResp, holdingsResp] = await Promise.all([
                api.request(`/database/portfolio/${portfolioId}/categories-detailed`),
                fetch(`${api.baseURL}/user/portfolios/${portfolioId}/holdings`, {
                    headers: { ...api.authManager.getAuthHeader() }
                }).then(r => r.ok ? r.json() : null).catch(() => null)
            ]);

            const cashBalance = holdingsResp ? (holdingsResp.cash_balance || 0) : 0;

            if (detailsResp.ok) {
                const data = await detailsResp.json();

                if (!data.categories || data.categories.length === 0) {
                    summaryContainer.innerHTML = '<div class="empty-portfolio">No holdings yet. Add transactions to build your portfolio!</div>';
                    return;
                }

                const securitiesValue = data.total_portfolio_value || 0;
                const totalValue = securitiesValue + cashBalance;
                const totalPositions = data.total_positions || 0;

                // Calculate total cost basis
                let totalCostBasis = 0;
                data.categories.forEach(category => {
                    totalCostBasis += category.total_cost_basis || 0;
                });

                const totalGainLoss = securitiesValue - totalCostBasis;
                const totalGainLossPercent = totalCostBasis > 0 ? (totalGainLoss / totalCostBasis) * 100 : 0;
                const gainLossColor = totalGainLoss >= 0 ? '#10b981' : '#ef4444';

                const summaryHTML = `
                    <div class="builder-summary-stats">
                        <div class="builder-stat">
                            <div class="stat-label">Total Value</div>
                            <div class="stat-value">${formatCurrency(totalValue)}</div>
                        </div>
                        <div class="builder-stat">
                            <div class="stat-label">Securities</div>
                            <div class="stat-value">${formatCurrency(securitiesValue)}</div>
                        </div>
                        <div class="builder-stat">
                            <div class="stat-label">Cash</div>
                            <div class="stat-value" style="color: ${cashBalance < 0 ? '#ef4444' : 'inherit'}">${formatCurrency(cashBalance)}</div>
                        </div>
                        <div class="builder-stat">
                            <div class="stat-label">Cost Basis</div>
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