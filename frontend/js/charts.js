// AlphaVelocity Chart Utilities
class ChartManager {
    constructor() {
        this.charts = {};
        this.initializeChartDefaults();
    }

    initializeChartDefaults() {
        Chart.defaults.font.family = 'Inter, sans-serif';
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
        this._setChartDefaults();
    }

    _setChartDefaults() {
        const t = this._themeTokens();
        Chart.defaults.color = t.tickColor;
        Chart.defaults.borderColor = t.gridColor;
        Chart.defaults.backgroundColor = t.primaryBg;
    }

    // Single source of truth for all chart colors — reads live CSS vars
    _themeTokens() {
        const s = getComputedStyle(document.documentElement);
        const get = v => s.getPropertyValue(v).trim();
        return {
            primary:     get('--chart-primary')     || '#6366f1',
            primaryBg:   get('--chart-primary-bg')  || 'rgba(99,102,241,0.1)',
            secondary:   get('--chart-secondary')   || '#7c3aed',
            secondaryBg: get('--chart-secondary-bg')|| 'rgba(124,58,237,0.08)',
            gridColor:   (get('--border') || '#e5e7eb') + '55',
            tickColor:   get('--text-muted') || '#6b7280',
        };
    }

    // Kept for backwards compatibility
    _chartPrimary() {
        const t = this._themeTokens();
        return { line: t.primary, bg: t.primaryBg, secondary: t.secondary, secondaryBg: t.secondaryBg };
    }

    // Re-color all live chart instances when the theme changes (no data reload needed)
    updateChartColors() {
        this._setChartDefaults();
        const t = this._themeTokens();

        Object.entries(this.charts).forEach(([id, chart]) => {
            if (!chart) return;

            // Update dataset colors for portfolio line charts
            const ds0 = chart.data.datasets[0];
            if (ds0 && ds0.label && ds0.label.startsWith('Portfolio')) {
                const isValueChart = id === 'portfolio-value-chart';
                ds0.borderColor = isValueChart ? t.primary : t.secondary;
                ds0.backgroundColor = isValueChart ? t.primaryBg : t.secondaryBg;
                if (ds0.pointBackgroundColor !== undefined) ds0.pointBackgroundColor = ds0.borderColor;
            }

            // Update scale grid lines and tick colors on all charts
            const scales = chart.options && chart.options.scales;
            if (scales) {
                Object.values(scales).forEach(scale => {
                    if (scale.grid) scale.grid.color = t.gridColor;
                    if (scale.ticks) scale.ticks.color = t.tickColor;
                });
            }

            chart.update('none');
        });
    }

    // Create portfolio allocation pie chart
    createAllocationChart(containerId, portfolioData) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return null;

        // Destroy existing chart if it exists
        if (this.charts[containerId]) {
            this.charts[containerId].destroy();
        }

        // Calculate category allocations
        const categoryData = this.calculateCategoryAllocations(portfolioData);

        const config = {
            type: 'doughnut',
            data: {
                labels: categoryData.labels,
                datasets: [{
                    data: categoryData.values,
                    backgroundColor: [
                        '#6366f1', // Large-Cap Anchors
                        '#8b5cf6', // Small-Cap Specialists
                        '#06b6d4', // Data Center Infrastructure
                        '#10b981', // International Tech
                        '#f59e0b', // Tactical Fixed Income
                        '#ef4444', // Sector Momentum
                        '#f97316', // Critical Metals
                        '#84cc16'  // Specialized Materials
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                return `${label}: ${value.toFixed(1)}%`;
                            }
                        }
                    }
                },
                cutout: '60%',
                layout: {
                    padding: 20
                }
            }
        };

        this.charts[containerId] = new Chart(ctx, config);
        return this.charts[containerId];
    }

    // Create momentum score bar chart for top holdings
    createMomentumChart(containerId, holdings) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return null;

        if (this.charts[containerId]) {
            this.charts[containerId].destroy();
        }

        // Sort by momentum score and take top 10
        const topHoldings = holdings
            .sort((a, b) => b.momentum_score - a.momentum_score)
            .slice(0, 10);

        const config = {
            type: 'bar',
            data: {
                labels: topHoldings.map(h => h.ticker),
                datasets: [{
                    label: 'Momentum Score',
                    data: topHoldings.map(h => h.momentum_score),
                    backgroundColor: topHoldings.map(h => this.getScoreColor(h.momentum_score)),
                    borderColor: topHoldings.map(h => this.getScoreColor(h.momentum_score)),
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Score: ${context.parsed.x.toFixed(1)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            display: true,
                            color: this._themeTokens().gridColor
                        },
                        title: {
                            display: true,
                            text: 'Momentum Score'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                },
                layout: {
                    padding: 10
                }
            }
        };

        this.charts[containerId] = new Chart(ctx, config);
        return this.charts[containerId];
    }

    // Create portfolio value trend chart with real historical data
    async createTrendChart(containerId, portfolioId = 'default', days = 365) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return null;

        if (this.charts[containerId]) {
            this.charts[containerId].destroy();
        }

        // Fetch real historical data
        let chartData;
        try {
            const response = await fetch(`${window.ALPHAVELOCITY_API_URL || window.location.origin}/historical/chart-data/${portfolioId}?days=${days}`);
            if (response.ok) {
                chartData = await response.json();
            } else {
                throw new Error('Failed to fetch historical data');
            }
        } catch (error) {
            console.warn('Using sample data due to API error:', error);
            chartData = this.generateSampleTrendData();
        }

        const config = {
            type: 'line',
            data: {
                labels: chartData.labels,
                datasets: (() => {
                    const c = this._chartPrimary();
                    return [{
                        label: 'Portfolio Value',
                        data: chartData.portfolio_values,
                        borderColor: c.line,
                        backgroundColor: c.bg,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Momentum Score',
                        data: chartData.momentum_scores,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y1'
                    }];
                })()
            },
            options: {
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Portfolio Value ($)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Avg Momentum Score'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                        min: 0,
                        max: 100
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                layout: {
                    padding: 10
                }
            }
        };

        this.charts[containerId] = new Chart(ctx, config);
        return this.charts[containerId];
    }

    // Create portfolio total value history chart
    createPortfolioValueChart(containerId, labels, values, benchmarks = {}) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return null;

        if (this.charts[containerId]) {
            this.charts[containerId].destroy();
        }

        if (!labels.length) return null;

        const BENCHMARK_COLORS = {
            'SPY':  { line: '#94a3b8', bg: 'rgba(148,163,184,0)' },
            'QQQ':  { line: '#10b981', bg: 'rgba(16,185,129,0)' },
            'IWM':  { line: '#ef4444', bg: 'rgba(239,68,68,0)'  },
            'MTUM': { line: '#38bdf8', bg: 'rgba(56,189,248,0)' },
            'AIQ':  { line: '#f472b6', bg: 'rgba(244,114,182,0)'},
        };

        // Portfolio dataset
        const _c1 = this._chartPrimary();
        const datasets = [{
            label: 'Portfolio',
            data: labels.map((label, i) => ({ x: label, y: values[i] })),
            borderColor: _c1.secondary,
            backgroundColor: _c1.secondaryBg,
            borderWidth: 2,
            fill: true,
            tension: 0.35,
            pointRadius: 2,
            pointHoverRadius: 5
        }];

        // Benchmark datasets
        for (const [ticker, bValues] of Object.entries(benchmarks)) {
            const colors = BENCHMARK_COLORS[ticker] || { line: '#9ca3af', bg: 'rgba(0,0,0,0)' };
            datasets.push({
                label: ticker,
                data: labels.map((label, i) => ({ x: label, y: bValues[i] })),
                borderColor: colors.line,
                backgroundColor: colors.bg,
                borderWidth: 1.5,
                borderDash: [4, 3],
                fill: false,
                tension: 0.35,
                pointRadius: 0,
                pointHoverRadius: 4,
            });
        }

        const config = {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => '$' + ctx.parsed.y.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'month', tooltipFormat: 'MMM d, yyyy' },
                        grid: { color: this._themeTokens().gridColor },
                        ticks: { color: this._themeTokens().tickColor, maxTicksLimit: 6 }
                    },
                    y: {
                        grid: { color: this._themeTokens().gridColor },
                        ticks: {
                            color: this._themeTokens().tickColor,
                            callback: v => '$' + v.toLocaleString('en-US', {notation: 'compact'})
                        }
                    }
                }
            }
        };

        this.charts[containerId] = new Chart(ctx, config);
        return this.charts[containerId];
    }

    // Create return vs benchmark comparison chart (TWR %)
    createReturnComparisonChart(containerId, labels, portfolioTwr, benchmarks = {}) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return null;

        if (this.charts[containerId]) {
            this.charts[containerId].destroy();
        }

        if (!labels.length) return null;

        const BENCHMARK_COLORS = {
            'SPY':  '#94a3b8',
            'QQQ':  '#10b981',
            'IWM':  '#ef4444',
            'MTUM': '#38bdf8',
            'AIQ':  '#f472b6',
        };

        const _c2 = this._chartPrimary();
        const datasets = [{
            label: 'Portfolio (TWR)',
            data: labels.map((label, i) => ({ x: label, y: portfolioTwr[i] })),
            borderColor: _c2.secondary,
            backgroundColor: _c2.secondaryBg,
            borderWidth: 2,
            fill: true,
            tension: 0.35,
            pointRadius: 2,
            pointHoverRadius: 5,
        }];

        for (const [ticker, values] of Object.entries(benchmarks)) {
            datasets.push({
                label: ticker,
                data: labels.map((label, i) => ({ x: label, y: values[i] })),
                borderColor: BENCHMARK_COLORS[ticker] || '#9ca3af',
                backgroundColor: 'rgba(0,0,0,0)',
                borderWidth: 1.5,
                borderDash: [4, 3],
                fill: false,
                tension: 0.35,
                pointRadius: 0,
                pointHoverRadius: 4,
            });
        }

        const config = {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: { color: this._themeTokens().tickColor, boxWidth: 20, padding: 12, font: { size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y >= 0 ? '+' : ''}${ctx.parsed.y.toFixed(2)}%`
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'month', tooltipFormat: 'MMM d, yyyy' },
                        grid: { color: this._themeTokens().gridColor },
                        ticks: { color: this._themeTokens().tickColor, maxTicksLimit: 6 }
                    },
                    y: {
                        grid: { color: this._themeTokens().gridColor },
                        ticks: {
                            color: this._themeTokens().tickColor,
                            callback: v => (v >= 0 ? '+' : '') + v.toFixed(1) + '%'
                        }
                    }
                }
            }
        };

        this.charts[containerId] = new Chart(ctx, config);
        return this.charts[containerId];
    }

    // Composite momentum sparkline
    createMomentumSparkline(containerId, history) {
        const ctx = document.getElementById(containerId);
        if (!ctx || !history.length) return null;

        if (this.charts[containerId]) {
            this.charts[containerId].destroy();
        }

        const labels = history.map(h => h.date);
        const values = history.map(h => h.score);
        const latest = values[values.length - 1];
        const lineColor = latest >= 70 ? '#10b981' : latest >= 50 ? '#f59e0b' : '#ef4444';
        const fillColors = { '#10b981': 'rgba(16,185,129,0.12)', '#f59e0b': 'rgba(245,158,11,0.12)', '#ef4444': 'rgba(239,68,68,0.12)' };

        this.charts[containerId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    data: values,
                    borderColor: lineColor,
                    backgroundColor: fillColors[lineColor],
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 3,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: items => items[0].label,
                            label: item => `Score: ${item.parsed.y.toFixed(1)}`
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'day', tooltipFormat: 'MMM d' },
                        grid: { display: false },
                        ticks: {
                            color: this._themeTokens().tickColor,
                            font: { size: 9 },
                            maxTicksLimit: 4,
                            maxRotation: 0,
                        }
                    },
                    y: {
                        display: true,
                        grid: { color: this._themeTokens().gridColor },
                        ticks: {
                            color: this._themeTokens().tickColor,
                            font: { size: 9 },
                            maxTicksLimit: 3,
                            callback: v => v.toFixed(0)
                        },
                        suggestedMin: Math.max(0, Math.min(...values) - 5),
                        suggestedMax: Math.min(100, Math.max(...values) + 5),
                    }
                }
            }
        });
        return this.charts[containerId];
    }

    // Create drawdown chart (portfolio and benchmarks, all at/below 0%)
    createDrawdownChart(containerId, labels, portfolioDrawdown, benchmarks = {}) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return null;

        if (this.charts[containerId]) {
            this.charts[containerId].destroy();
        }

        if (!labels.length) return null;

        const BENCHMARK_COLORS = {
            'SPY':  '#94a3b8',
            'QQQ':  '#10b981',
            'IWM':  '#ef4444',
            'MTUM': '#38bdf8',
            'AIQ':  '#f472b6',
        };

        const _c3 = this._chartPrimary();
        const datasets = [{
            label: 'Portfolio',
            data: labels.map((label, i) => ({ x: label, y: portfolioDrawdown[i] })),
            borderColor: _c3.secondary,
            backgroundColor: _c3.secondaryBg,
            borderWidth: 2,
            fill: true,
            tension: 0.35,
            pointRadius: 2,
            pointHoverRadius: 5,
        }];

        for (const [ticker, values] of Object.entries(benchmarks)) {
            datasets.push({
                label: ticker,
                data: labels.map((label, i) => ({ x: label, y: values[i] })),
                borderColor: BENCHMARK_COLORS[ticker] || '#9ca3af',
                backgroundColor: 'rgba(0,0,0,0)',
                borderWidth: 1.5,
                borderDash: [4, 3],
                fill: false,
                tension: 0.35,
                pointRadius: 0,
                pointHoverRadius: 4,
            });
        }

        const config = {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: { color: this._themeTokens().tickColor, boxWidth: 20, padding: 12, font: { size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}%`
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: { unit: 'month', tooltipFormat: 'MMM d, yyyy' },
                        grid: { color: this._themeTokens().gridColor },
                        ticks: { color: this._themeTokens().tickColor, maxTicksLimit: 6 }
                    },
                    y: {
                        max: 0,
                        grid: { color: this._themeTokens().gridColor },
                        ticks: {
                            color: this._themeTokens().tickColor,
                            callback: v => v.toFixed(1) + '%'
                        }
                    }
                }
            }
        };

        this.charts[containerId] = new Chart(ctx, config);
        return this.charts[containerId];
    }

    // Helper method to calculate category allocations from portfolio data
    calculateCategoryAllocations(portfolioData) {
        if (!portfolioData || !portfolioData.holdings) {
            return { labels: [], values: [] };
        }

        // Category mapping (mirrors PORTFOLIO_CATEGORIES in backend/config/portfolio_config.py)
        const categoryMap = {
            // Large-Cap Anchors
            'NVDA': 'Large-Cap Anchors', 'TSM': 'Large-Cap Anchors', 'ASML': 'Large-Cap Anchors',
            'AVGO': 'Large-Cap Anchors', 'MSFT': 'Large-Cap Anchors', 'META': 'Large-Cap Anchors',
            'AAPL': 'Large-Cap Anchors', 'AMD': 'Large-Cap Anchors', 'GOOGL': 'Large-Cap Anchors',
            'TSLA': 'Large-Cap Anchors', 'PLTR': 'Large-Cap Anchors', 'CSCO': 'Large-Cap Anchors',
            'CRWV': 'Large-Cap Anchors', 'ORCL': 'Large-Cap Anchors', 'DT': 'Large-Cap Anchors',
            'AUR': 'Large-Cap Anchors', 'MBLY': 'Large-Cap Anchors', 'NOW': 'Large-Cap Anchors',
            'INTC': 'Large-Cap Anchors', 'SNDK': 'Large-Cap Anchors', 'COHR': 'Large-Cap Anchors', 'TSEM': 'Large-Cap Anchors',
            // Small-Cap Specialists
            'VRT': 'Small-Cap Specialists', 'MOD': 'Small-Cap Specialists', 'BE': 'Small-Cap Specialists',
            'CIEN': 'Small-Cap Specialists', 'ATKR': 'Small-Cap Specialists', 'UI': 'Small-Cap Specialists',
            'APLD': 'Small-Cap Specialists', 'SMCI': 'Small-Cap Specialists', 'GDS': 'Small-Cap Specialists',
            'VNET': 'Small-Cap Specialists', 'LITE': 'Small-Cap Specialists', 'WYFI': 'Small-Cap Specialists', 'PSIX': 'Small-Cap Specialists',
            // Data Center Infrastructure
            'SRVR': 'Data Center Infrastructure', 'DLR': 'Data Center Infrastructure', 'EQIX': 'Data Center Infrastructure',
            'AMT': 'Data Center Infrastructure', 'CCI': 'Data Center Infrastructure', 'COR': 'Data Center Infrastructure',
            'IRM': 'Data Center Infrastructure', 'ACM': 'Data Center Infrastructure', 'JCI': 'Data Center Infrastructure',
            'IDGT': 'Data Center Infrastructure', 'DTCR': 'Data Center Infrastructure', 'CORZ': 'Data Center Infrastructure', 'KRC': 'Data Center Infrastructure',
            // International Tech/Momentum
            'EWJ': 'International Tech/Momentum', 'EWT': 'International Tech/Momentum', 'INDA': 'International Tech/Momentum',
            'EWY': 'International Tech/Momentum', 'EWU': 'International Tech/Momentum', 'INFY': 'International Tech/Momentum',
            // Tactical Fixed Income
            'SHY': 'Tactical Fixed Income', 'VCIT': 'Tactical Fixed Income', 'TIP': 'Tactical Fixed Income',
            'IEF': 'Tactical Fixed Income', 'BIL': 'Tactical Fixed Income', 'LQD': 'Tactical Fixed Income',
            'FLOT': 'Tactical Fixed Income', 'XHLF': 'Tactical Fixed Income', 'SWVXX': 'Tactical Fixed Income',
            // Sector Momentum Rotation
            'XLE': 'Sector Momentum Rotation', 'XLF': 'Sector Momentum Rotation', 'XLI': 'Sector Momentum Rotation',
            'XLU': 'Sector Momentum Rotation', 'XLB': 'Sector Momentum Rotation', 'LBRT': 'Sector Momentum Rotation', 'PUMP': 'Sector Momentum Rotation',
            // Critical Metals & Mining
            'MP': 'Critical Metals & Mining', 'ALB': 'Critical Metals & Mining', 'SQM': 'Critical Metals & Mining',
            'LAC': 'Critical Metals & Mining', 'FCX': 'Critical Metals & Mining', 'SCCO': 'Critical Metals & Mining', 'TECK': 'Critical Metals & Mining',
            // Specialized Materials ETFs
            'REMX': 'Specialized Materials ETFs', 'LIT': 'Specialized Materials ETFs',
            // AI Power/Energy Infrastructure
            'VST': 'AI Power/Energy Infrastructure', 'CEG': 'AI Power/Energy Infrastructure', 'NRG': 'AI Power/Energy Infrastructure',
            'GEV': 'AI Power/Energy Infrastructure', 'CCJ': 'AI Power/Energy Infrastructure', 'OKLO': 'AI Power/Energy Infrastructure',
            'SMR': 'AI Power/Energy Infrastructure', 'TLN': 'AI Power/Energy Infrastructure', 'IREN': 'AI Power/Energy Infrastructure',
            'CIFR': 'AI Power/Energy Infrastructure', 'EQT': 'AI Power/Energy Infrastructure', 'SEI': 'AI Power/Energy Infrastructure',
            'RIOT': 'AI Power/Energy Infrastructure', 'HUT': 'AI Power/Energy Infrastructure', 'BTDR': 'AI Power/Energy Infrastructure',
            'CLSK': 'AI Power/Energy Infrastructure', 'BITF': 'AI Power/Energy Infrastructure', 'BW': 'AI Power/Energy Infrastructure',
        };

        const categoryTotals = {};
        const totalValue = portfolioData.total_value;

        // Calculate totals for each category
        portfolioData.holdings.forEach(holding => {
            const category = categoryMap[holding.ticker] || 'Other';
            const value = parseFloat(holding.market_value.replace(/[$,]/g, ''));

            if (!categoryTotals[category]) {
                categoryTotals[category] = 0;
            }
            categoryTotals[category] += value;
        });

        // Convert to percentages
        const labels = Object.keys(categoryTotals);
        const values = labels.map(label => (categoryTotals[label] / totalValue) * 100);

        return { labels, values };
    }

    // Generate sample trend data (replace with real API data later)
    generateSampleTrendData() {
        const days = 30;
        const labels = [];
        const portfolio_values = [];
        const momentum_scores = [];

        const baseValue = 20000;
        const baseScore = 70;

        for (let i = days; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));

            // Generate some realistic portfolio growth
            const trend = (days - i) * 15; // Upward trend
            const volatility = (Math.random() - 0.5) * 1000; // Random fluctuation
            portfolio_values.push(baseValue + trend + volatility);

            // Generate momentum score fluctuation
            const scoreVolatility = (Math.random() - 0.5) * 10;
            momentum_scores.push(Math.max(50, Math.min(90, baseScore + scoreVolatility)));
        }

        return { labels, portfolio_values, momentum_scores };
    }

    // Get color based on momentum score (reads from active theme CSS vars)
    getScoreColor(score) {
        const s = getComputedStyle(document.documentElement);
        if (score >= 80) return s.getPropertyValue('--score-strong-buy').trim() || '#10b981';
        if (score >= 70) return s.getPropertyValue('--score-buy').trim() || '#3b82f6';
        if (score >= 60) return s.getPropertyValue('--score-hold').trim() || '#f59e0b';
        if (score >= 50) return s.getPropertyValue('--score-weak-hold').trim() || '#ef4444';
        return s.getPropertyValue('--score-sell').trim() || '#dc2626';
    }

    // Destroy all charts (useful for cleanup)
    destroyAll() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }

    // Resize all charts (useful for responsive design)
    resizeAll() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.resize();
        });
    }

    /**
     * Render a pairwise correlation heatmap into a container element using DOM APIs.
     * All user-derived content is set via textContent to prevent XSS.
     *
     * @param {HTMLElement} container
     * @param {string[]} tickers          Already in desired display order
     * @param {number[][]} matrix         Row-major, same order as tickers
     * @param {Array<{name,count}>} categoryGroups  Optional — drives divider lines
     */
    renderCorrelationHeatmap(container, tickers, matrix, categoryGroups = []) {
        container.innerHTML = '';
        const n = tickers.length;
        if (n === 0) {
            const msg = document.createElement('p');
            msg.style.cssText = 'color: var(--text-secondary); font-size: 0.8rem;';
            msg.textContent = 'No data';
            container.appendChild(msg);
            return;
        }

        const corrColor = (v) => {
            if (v === null) return 'transparent';
            if (v >= 0.7)  return '#ef444430';
            if (v >= 0.4)  return '#f59e0b28';
            if (v >= 0.1)  return '#6b728020';
            if (v >= -0.1) return 'transparent';
            if (v >= -0.4) return '#3b82f620';
            return '#10b98130';
        };

        const cellSize = Math.max(36, Math.min(54, Math.floor(440 / (n + 1))));
        const fs = n > 10 ? '0.6rem' : '0.68rem';
        const dividerColor = 'var(--text-secondary)';

        // Build a set of row/column indices that are the LAST in their category group
        const groupBoundaries = new Set();
        if (categoryGroups.length > 0) {
            let cursor = 0;
            categoryGroups.forEach(g => {
                cursor += g.count;
                groupBoundaries.add(cursor - 1);  // last index in this group
            });
            groupBoundaries.delete(n - 1);  // no divider after the final row
        }

        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'overflow-x: auto; -webkit-overflow-scrolling: touch;';

        const table = document.createElement('table');
        table.style.cssText = `border-collapse: collapse; font-size: ${fs}; white-space: nowrap; margin: 0 auto;`;

        // Header row — category label spans + individual ticker headers
        const thead = document.createElement('thead');

        // Category label row (only when groups provided)
        if (categoryGroups.length > 0) {
            const catLabelRow = document.createElement('tr');
            const cornerTh = document.createElement('th');
            catLabelRow.appendChild(cornerTh);
            let colCursor = 0;
            categoryGroups.forEach((g, gi) => {
                const th = document.createElement('th');
                th.colSpan = g.count;
                th.style.cssText = `text-align: center; font-size: 0.6rem; font-weight: 600; color: var(--text-muted); padding: 0 0.25rem 0.2rem; border-bottom: 1px solid ${dividerColor}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: ${cellSize * g.count}px;`;
                const short = g.name.replace('Large-Cap', 'LC').replace('Small-Cap', 'SC')
                    .replace('Data Center', 'DC').replace('Infrastructure', 'Infra')
                    .replace('International', "Int'l").replace('Specialized', 'Spec.')
                    .replace('Critical', 'Crit.').replace('Sector Momentum', 'Sector')
                    .replace('Rotation', 'Rot.').replace('Tactical Fixed Income', 'Fixed Inc.')
                    .replace(' & ', '/');
                th.textContent = short;
                colCursor += g.count;
                if (gi < categoryGroups.length - 1) {
                    th.style.borderRight = `2px solid ${dividerColor}`;
                }
                catLabelRow.appendChild(th);
            });
            thead.appendChild(catLabelRow);
        }

        // Ticker header row
        const headerRow = document.createElement('tr');
        const emptyTh = document.createElement('th');
        emptyTh.style.width = `${cellSize}px`;
        headerRow.appendChild(emptyTh);
        tickers.forEach((t, j) => {
            const th = document.createElement('th');
            const isBoundary = groupBoundaries.has(j);
            th.style.cssText = `width: ${cellSize}px; padding: 0.15rem 0.1rem; color: var(--text-secondary); font-weight: 600; text-align: center; writing-mode: vertical-rl; transform: rotate(180deg); height: ${cellSize}px; vertical-align: bottom;${isBoundary ? ` border-right: 2px solid ${dividerColor};` : ''}`;
            th.textContent = t;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Body rows
        const tbody = document.createElement('tbody');
        tickers.forEach((rowTicker, i) => {
            const isRowBoundary = groupBoundaries.has(i);
            const tr = document.createElement('tr');
            const labelTd = document.createElement('td');
            labelTd.style.cssText = `padding: 0.1rem 0.25rem 0.1rem 0; color: var(--text-secondary); font-weight: 600; text-align: right; white-space: nowrap;${isRowBoundary ? ` border-bottom: 2px solid ${dividerColor};` : ''}`;
            labelTd.textContent = rowTicker;
            tr.appendChild(labelTd);

            tickers.forEach((_, j) => {
                const v = matrix[i][j];
                const td = document.createElement('td');
                const isHighCorr = Math.abs(v || 0) >= 0.6;
                const isColBoundary = groupBoundaries.has(j);
                td.style.cssText = [
                    `width: ${cellSize}px`,
                    `height: ${cellSize}px`,
                    'text-align: center',
                    `background: ${corrColor(v)}`,
                    `color: var(--text-${isHighCorr ? 'primary' : 'secondary'})`,
                    `border: 1px solid var(--border-subtle)`,
                    `font-weight: ${isHighCorr ? 700 : 400}`,
                    isRowBoundary ? `border-bottom: 2px solid ${dividerColor}` : '',
                    isColBoundary ? `border-right: 2px solid ${dividerColor}` : '',
                ].filter(Boolean).join('; ') + ';';
                td.textContent = i === j ? '1.00' : (v !== null ? v.toFixed(2) : '—');
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        wrapper.appendChild(table);
        container.appendChild(wrapper);
    }

    /**
     * Create / update the volatility term structure line chart.
     */
    createTermStructureChart(canvasId, points, ticker) {
        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
            delete this.charts[canvasId];
        }

        const canvas = document.getElementById(canvasId);
        if (!canvas || points.length === 0) return;

        const t = this._themeTokens();
        const labels = points.map(p => `${p.dte}d`);
        const ivPct = points.map(p => +(p.iv * 100).toFixed(2));

        this.charts[canvasId] = new Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: `${ticker} IV`,
                    data: ivPct,
                    borderColor: t.primary,
                    backgroundColor: t.primaryBg,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: (items) => {
                                const idx = items[0].dataIndex;
                                return `${points[idx].expiry} (${points[idx].dte}d)`;
                            },
                            label: (item) => `IV: ${item.raw.toFixed(1)}%`,
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Days to Expiry', color: t.tickColor, font: { size: 11 } },
                        grid: { color: t.gridColor },
                        ticks: { color: t.tickColor },
                    },
                    y: {
                        title: { display: true, text: 'IV (%)', color: t.tickColor, font: { size: 11 } },
                        grid: { color: t.gridColor },
                        ticks: {
                            color: t.tickColor,
                            callback: v => `${v}%`,
                        },
                    }
                }
            }
        });
    }
}

// Export chart manager instance
const chartManager = new ChartManager();