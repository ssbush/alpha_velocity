// AlphaVelocity Chart Utilities
class ChartManager {
    constructor() {
        this.charts = {};
        this.initializeChartDefaults();
    }

    initializeChartDefaults() {
        // Set Chart.js defaults for consistent styling
        Chart.defaults.font.family = 'Inter, sans-serif';
        Chart.defaults.color = '#374151';
        Chart.defaults.borderColor = 'rgba(156, 163, 175, 0.2)';
        Chart.defaults.backgroundColor = 'rgba(99, 102, 241, 0.1)';

        // Responsive defaults
        Chart.defaults.responsive = true;
        Chart.defaults.maintainAspectRatio = false;
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
                            color: 'rgba(156, 163, 175, 0.2)'
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
                datasets: [{
                    label: 'Portfolio Value',
                    data: chartData.portfolio_values,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
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
                }]
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
    createPortfolioValueChart(containerId, labels, values) {
        const ctx = document.getElementById(containerId);
        if (!ctx) return null;

        if (this.charts[containerId]) {
            this.charts[containerId].destroy();
        }

        if (!labels.length) return null;

        // Build {x: date, y: value} points for time scale
        const dataPoints = labels.map((label, i) => ({ x: label, y: values[i] }));

        const config = {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Portfolio Value',
                    data: dataPoints,
                    borderColor: '#7c3aed',
                    backgroundColor: 'rgba(124, 58, 237, 0.08)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 2,
                    pointHoverRadius: 5
                }]
            },
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
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#9ca3af', maxTicksLimit: 6 }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            color: '#9ca3af',
                            callback: v => '$' + v.toLocaleString('en-US', {notation: 'compact'})
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

        // Category mapping (this should match your backend categories)
        const categoryMap = {
            'NVDA': 'Specialized Materials ETFs', 'BE': 'Specialized Materials ETFs',
            'AAPL': 'Large-Cap Anchors', 'GOOGL': 'Large-Cap Anchors', 'AVGO': 'Large-Cap Anchors',
            'META': 'Large-Cap Anchors', 'MSFT': 'Large-Cap Anchors', 'NOW': 'Large-Cap Anchors',
            'VRT': 'Small-Cap Specialists', 'MOD': 'Small-Cap Specialists', 'UI': 'Small-Cap Specialists',
            'DLR': 'Data Center Infrastructure', 'SRVR': 'Data Center Infrastructure', 'IRM': 'Data Center Infrastructure',
            'EWJ': 'International Tech/Momentum', 'EWT': 'International Tech/Momentum',
            'SHY': 'Tactical Fixed Income',
            'XLI': 'Sector Momentum Rotation',
            'MP': 'Critical Metals & Mining'
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

    // Get color based on momentum score
    getScoreColor(score) {
        if (score >= 80) return '#10b981'; // Green
        if (score >= 70) return '#3b82f6'; // Blue
        if (score >= 60) return '#f59e0b'; // Yellow
        if (score >= 50) return '#ef4444'; // Orange
        return '#dc2626'; // Red
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
}

// Export chart manager instance
const chartManager = new ChartManager();