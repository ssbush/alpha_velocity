/**
 * Portfolio Manager
 * Handles user portfolio operations (create, read, update, delete)
 */

class PortfolioManager {
    constructor(apiBaseUrl, authManager) {
        this.apiBaseUrl = apiBaseUrl;
        this.authManager = authManager;
        this.currentPortfolio = null;
        this.userPortfolios = [];
    }

    /**
     * Fetch all user portfolios
     */
    async fetchPortfolios() {
        if (!this.authManager.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/user/portfolios`, {
                method: 'GET',
                headers: {
                    ...this.authManager.getAuthHeader()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch portfolios');
            }

            const data = await response.json();
            this.userPortfolios = data.portfolios || [];
            return { success: true, portfolios: this.userPortfolios };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Fetch all user portfolios with summaries
     */
    async fetchPortfolioSummaries() {
        if (!this.authManager.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/user/portfolios/summaries?_=${Date.now()}`, {
                method: 'GET',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    ...this.authManager.getAuthHeader()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch portfolio summaries');
            }

            const data = await response.json();
            return { success: true, portfolios: data.portfolios || [] };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Create a new portfolio
     */
    async createPortfolio(name, description = '') {
        if (!this.authManager.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const params = new URLSearchParams();
            params.append('name', name);
            if (description) {
                params.append('description', description);
            }

            const response = await fetch(`${this.apiBaseUrl}/user/portfolios?${params}`, {
                method: 'POST',
                headers: {
                    ...this.authManager.getAuthHeader()
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create portfolio');
            }

            const data = await response.json();
            await this.fetchPortfolios(); // Refresh list
            return { success: true, portfolio: data.portfolio };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Get portfolio summary
     */
    async getPortfolio(portfolioId) {
        if (!this.authManager.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/user/portfolios/${portfolioId}`, {
                method: 'GET',
                headers: {
                    ...this.authManager.getAuthHeader()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch portfolio');
            }

            const portfolio = await response.json();
            this.currentPortfolio = portfolio;
            return { success: true, portfolio };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Update portfolio details
     */
    async updatePortfolio(portfolioId, name, description) {
        if (!this.authManager.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const params = new URLSearchParams();
            if (name) params.append('name', name);
            if (description) params.append('description', description);

            const response = await fetch(`${this.apiBaseUrl}/user/portfolios/${portfolioId}?${params}`, {
                method: 'PUT',
                headers: {
                    ...this.authManager.getAuthHeader()
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update portfolio');
            }

            const data = await response.json();
            await this.fetchPortfolios(); // Refresh list
            return { success: true, portfolio: data.portfolio };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Delete portfolio
     */
    async deletePortfolio(portfolioId) {
        if (!this.authManager.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/user/portfolios/${portfolioId}`, {
                method: 'DELETE',
                headers: {
                    ...this.authManager.getAuthHeader()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to delete portfolio');
            }

            await this.fetchPortfolios(); // Refresh list
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Add holding to portfolio
     */
    async addHolding(portfolioId, ticker, shares, costBasis = null, categoryName = null) {
        if (!this.authManager.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const params = new URLSearchParams();
            params.append('ticker', ticker);
            params.append('shares', shares);
            if (costBasis) params.append('average_cost_basis', costBasis);
            if (categoryName) params.append('category_name', categoryName);

            const response = await fetch(`${this.apiBaseUrl}/user/portfolios/${portfolioId}/holdings?${params}`, {
                method: 'POST',
                headers: {
                    ...this.authManager.getAuthHeader()
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to add holding');
            }

            const data = await response.json();
            return { success: true, holding: data.holding };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Remove holding from portfolio
     */
    async removeHolding(portfolioId, ticker) {
        if (!this.authManager.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/user/portfolios/${portfolioId}/holdings/${ticker}`, {
                method: 'DELETE',
                headers: {
                    ...this.authManager.getAuthHeader()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to remove holding');
            }

            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Show portfolio selector UI
     */
    showPortfolioSelector() {
        const modal = document.getElementById('portfolio-selector-modal');
        const container = document.getElementById('portfolio-selector-container');
        if (!container || !modal) return;

        // Show modal
        modal.style.display = 'flex';

        // Clear existing content
        container.innerHTML = '';

        // Create selector HTML
        const html = `
            <div class="portfolio-selector">
                <h2>My Portfolios</h2>
                <div class="portfolio-list" id="portfolio-list"></div>
                <button class="create-portfolio-btn" id="create-portfolio-btn">+ Create New Portfolio</button>
            </div>
        `;

        container.innerHTML = html;

        // Populate portfolio list
        this.renderPortfolioList();

        // Setup event listeners
        document.getElementById('create-portfolio-btn').addEventListener('click', () => {
            this.showCreatePortfolioModal();
        });

        // Close button
        const closeBtn = document.getElementById('close-portfolio-selector');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
        }

        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }

    /**
     * Render portfolio list
     */
    async renderPortfolioList() {
        const listContainer = document.getElementById('portfolio-list');
        if (!listContainer) return;

        const result = await this.fetchPortfolios();
        if (!result.success) {
            listContainer.innerHTML = '<p class="error">Failed to load portfolios</p>';
            return;
        }

        if (this.userPortfolios.length === 0) {
            listContainer.innerHTML = '<p class="empty-state">No portfolios yet. Create your first portfolio!</p>';
            return;
        }

        listContainer.innerHTML = this.userPortfolios.map(portfolio => `
            <div class="portfolio-item" data-portfolio-id="${portfolio.id}">
                <div class="portfolio-info">
                    <h4>${portfolio.name}</h4>
                    <p>${portfolio.description || 'No description'}</p>
                    <span class="portfolio-date">Created: ${new Date(portfolio.created_at).toLocaleDateString()}</span>
                </div>
                <div class="portfolio-actions">
                    <button class="select-btn" data-portfolio-id="${portfolio.id}">Select</button>
                    <button class="delete-btn" data-portfolio-id="${portfolio.id}">Delete</button>
                </div>
            </div>
        `).join('');

        // Add event listeners
        document.querySelectorAll('.select-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const portfolioId = e.target.dataset.portfolioId;
                this.selectPortfolio(parseInt(portfolioId));
            });
        });

        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const portfolioId = e.target.dataset.portfolioId;
                if (confirm('Are you sure you want to delete this portfolio?')) {
                    await this.deletePortfolio(parseInt(portfolioId));
                    this.renderPortfolioList();
                }
            });
        });
    }

    /**
     * Select a portfolio
     */
    selectPortfolio(portfolioId) {
        localStorage.setItem('selected_portfolio_id', portfolioId);
        const rows = document.querySelectorAll('.portfolio-row');
        rows.forEach(r => {
            r.classList.toggle('selected', parseInt(r.dataset.portfolioId) === portfolioId);
        });
        if (window.app) window.app.loadSelectedPortfolioHoldings(portfolioId);
    }

    /**
     * Show create portfolio modal
     */
    async showCreatePortfolioModal() {
        // Fetch categories to show allocation inputs
        const categories = await fetch(`${this.apiBaseUrl}/api/v1/categories`).then(r => r.json());

        const modal = document.createElement('div');
        modal.className = 'modal modal-large';
        modal.style.display = 'flex';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>Create New Portfolio</h2>
                <form id="create-portfolio-form">
                    <div class="form-group">
                        <label for="portfolio-name">Portfolio Name *</label>
                        <input type="text" id="portfolio-name" required>
                    </div>
                    <div class="form-group">
                        <label for="portfolio-description">Description</label>
                        <textarea id="portfolio-description" rows="3"></textarea>
                    </div>

                    <div class="form-section">
                        <h3>Target Allocations <span class="allocation-total" id="allocation-total">Total: 0%</span></h3>
                        <p class="form-help">Set target allocation percentages for each category (optional - defaults will be used)</p>
                        <div class="allocation-grid" id="allocation-inputs">
                            ${categories.map(cat => `
                                <div class="allocation-item">
                                    <label for="alloc-${cat.name}">${cat.name}</label>
                                    <div class="input-with-unit">
                                        <input
                                            type="number"
                                            id="alloc-${cat.name}"
                                            data-category-id="${cat.id}"
                                            min="0"
                                            max="100"
                                            step="0.1"
                                            value="${(cat.target_allocation * 100).toFixed(1)}"
                                            class="allocation-input">
                                        <span class="unit">%</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <button type="submit" class="submit-btn">Create Portfolio</button>
                </form>
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
            const totalEl = modal.querySelector('#allocation-total');
            totalEl.textContent = `Total: ${total.toFixed(1)}%`;
            totalEl.style.color = Math.abs(total - 100) < 0.1 ? '#10b981' : (total > 100 ? '#ef4444' : '#f59e0b');
        };

        modal.querySelectorAll('.allocation-input').forEach(input => {
            input.addEventListener('input', updateTotal);
        });
        updateTotal();

        // Close modal
        modal.querySelector('.close').addEventListener('click', () => {
            modal.remove();
        });

        // Handle form submission
        modal.querySelector('form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('portfolio-name').value;
            const description = document.getElementById('portfolio-description').value;

            // Get allocation values
            const allocations = {};
            modal.querySelectorAll('.allocation-input').forEach(input => {
                const categoryId = parseInt(input.dataset.categoryId);
                const value = parseFloat(input.value) || 0;
                allocations[categoryId] = value;
            });

            // Create portfolio
            const result = await this.createPortfolio(name, description);
            if (result.success) {
                const portfolioId = result.portfolio.id;

                // Set custom allocations if different from defaults
                const allocationPromises = [];
                for (const [categoryId, targetPct] of Object.entries(allocations)) {
                    allocationPromises.push(
                        fetch(`${this.apiBaseUrl}/database/portfolio/${portfolioId}/category-targets?category_id=${categoryId}&target_pct=${targetPct}`, {
                            method: 'POST',
                            headers: this.authManager.getAuthHeader()
                        })
                    );
                }

                await Promise.all(allocationPromises);

                modal.remove();
                this.renderPortfolioList();
                if (this.fetchPortfolios) await this.fetchPortfolios();
            } else {
                alert(result.error);
            }
        });
    }

    /**
     * Render portfolio dashboard with summaries
     */
    async renderPortfolioDashboard(containerId = 'portfolio-dashboard') {
        const container = document.getElementById(containerId);
        if (!container) return;

        // Show loading state
        container.innerHTML = '<div class="loading">Loading portfolios...</div>';

        const result = await this.fetchPortfolioSummaries();
        if (!result.success) {
            container.innerHTML = `<div class="error">Failed to load portfolios: ${result.error}</div>`;
            return;
        }

        const portfolios = result.portfolios;
        if (portfolios.length === 0) {
            container.innerHTML = `
                <div class="empty-portfolio-state">
                    <p>No portfolios yet.</p>
                    <button class="create-portfolio-btn" onclick="window.app.portfolioManager.showCreatePortfolioModal()">
                        Create Your First Portfolio
                    </button>
                </div>
            `;
            return;
        }

        // Get selected portfolio ID from localStorage
        const selectedId = parseInt(localStorage.getItem('selected_portfolio_id'));

        // Sort portfolios to put selected one first
        portfolios.sort((a, b) => {
            if (a.portfolio_id === selectedId) return -1;
            if (b.portfolio_id === selectedId) return 1;
            return 0;
        });

        // Render compact portfolio list
        const rows = portfolios.map(p => {
            const isSelected = p.portfolio_id === selectedId;
            const returnClass = p.total_return >= 0 ? 'positive' : 'negative';
            const returnSign = p.total_return >= 0 ? '+' : '';
            const value = '$' + p.total_value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            const ret = `${returnSign}${p.total_return_pct.toFixed(2)}%`;

            return `
                <div class="portfolio-row ${isSelected ? 'selected' : ''}" data-portfolio-id="${p.portfolio_id}">
                    <span class="portfolio-row-name">${p.name}</span>
                    <div class="portfolio-row-stat">
                        <span class="portfolio-row-stat-label">Value</span>
                        <span class="portfolio-row-stat-value">${value}</span>
                    </div>
                    <div class="portfolio-row-stat">
                        <span class="portfolio-row-stat-label">Positions</span>
                        <span class="portfolio-row-stat-value">${p.total_positions}</span>
                    </div>
                    <div class="portfolio-row-stat">
                        <span class="portfolio-row-stat-label">Return</span>
                        <span class="portfolio-row-stat-value ${returnClass}">${ret}</span>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = `<div class="portfolios-list">${rows}</div>`;

        // Wire up click handlers
        container.querySelectorAll('.portfolio-row').forEach(row => {
            row.addEventListener('click', () => {
                const portfolioId = parseInt(row.dataset.portfolioId);
                container.querySelectorAll('.portfolio-row').forEach(r => r.classList.remove('selected'));
                row.classList.add('selected');
                localStorage.setItem('selected_portfolio_id', portfolioId);
                if (window.app) window.app.loadSelectedPortfolioHoldings(portfolioId);
            });
        });
    }

    /**
     * View portfolio details
     */
    async viewPortfolioDetails(portfolioId) {
        const result = await this.getPortfolio(portfolioId);
        if (result.success) {
            // Store the portfolio and trigger a view change
            this.currentPortfolio = result.portfolio;
            // You could emit an event or call a method to show detailed view
            console.log('Portfolio details:', result.portfolio);
            // For now, just select it
            this.selectPortfolio(portfolioId);
        }
    }

    /**
     * Initialize portfolio selector in Builder view
     */
    async initBuilderPortfolioSelector() {
        const selectElement = document.getElementById('builder-portfolio-select');
        const newPortfolioBtn = document.getElementById('builder-new-portfolio-btn');

        if (!selectElement) return;

        // Fetch portfolios
        const result = await this.fetchPortfolios();
        if (!result.success) {
            selectElement.innerHTML = '<option value="">Failed to load portfolios</option>';
            return;
        }

        // Get selected portfolio ID from localStorage
        const selectedId = parseInt(localStorage.getItem('selected_portfolio_id'));

        // Populate dropdown
        if (this.userPortfolios.length === 0) {
            selectElement.innerHTML = '<option value="">No portfolios - Create one below</option>';
        } else {
            selectElement.innerHTML = this.userPortfolios.map(p =>
                `<option value="${p.id}" ${p.id === selectedId ? 'selected' : ''}>${p.name}</option>`
            ).join('');
        }

        // Handle portfolio selection change
        selectElement.addEventListener('change', async (e) => {
            const portfolioId = parseInt(e.target.value);
            if (portfolioId) {
                await this.selectPortfolio(portfolioId);
            }
        });

        // Handle new portfolio button
        if (newPortfolioBtn) {
            newPortfolioBtn.addEventListener('click', () => {
                this.showCreatePortfolioModal();
            });
        }
    }

    /**
     * Get current selected portfolio ID
     */
    getSelectedPortfolioId() {
        return parseInt(localStorage.getItem('selected_portfolio_id')) || null;
    }
}
