/**
 * Authentication Manager
 * Handles user login, registration, and session management
 */

class AuthManager {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.currentUser = null;
        this.token = null;
        this.refreshToken = null;
        this.loadSession();
    }

    /**
     * Decode the exp claim from a JWT without verifying the signature.
     * Used only for client-side UX timing — the server always validates signatures.
     * @returns {number|null} Expiry time in milliseconds, or null if unreadable.
     */
    getTokenExpiry(token = this.token) {
        if (!token) return null;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp ? payload.exp * 1000 : null;
        } catch {
            return null;
        }
    }

    /**
     * Load session from localStorage.
     * Clears the session immediately if the access token is expired and there
     * is no refresh token to recover with — prevents the broken logged-in-but-
     * all-API-calls-fail state after returning to the tab days later.
     */
    loadSession() {
        const token = localStorage.getItem('auth_token');
        const refreshToken = localStorage.getItem('refresh_token');
        const userStr = localStorage.getItem('current_user');

        if (token && userStr) {
            const expiry = this.getTokenExpiry(token);
            const isExpired = expiry !== null && Date.now() > expiry;

            if (isExpired && !refreshToken) {
                // Access token dead, no refresh token — clear everything
                localStorage.removeItem('auth_token');
                localStorage.removeItem('refresh_token');
                localStorage.removeItem('current_user');
                return;
            }

            this.token = token;
            this.refreshToken = refreshToken;
            this.currentUser = JSON.parse(userStr);
        }
    }

    /**
     * Save session to localStorage
     */
    saveSession(accessToken, refreshToken, user) {
        this.token = accessToken;
        this.refreshToken = refreshToken;
        this.currentUser = user;
        localStorage.setItem('auth_token', accessToken);
        if (refreshToken) {
            localStorage.setItem('refresh_token', refreshToken);
        }
        localStorage.setItem('current_user', JSON.stringify(user));
    }

    /**
     * Clear session
     */
    clearSession() {
        this.token = null;
        this.refreshToken = null;
        this.currentUser = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('current_user');
    }

    /**
     * Check if user is logged in
     */
    isLoggedIn() {
        return this.token !== null && this.currentUser !== null;
    }

    /**
     * Get authorization header
     */
    getAuthHeader() {
        if (this.token) {
            return { 'Authorization': `Bearer ${this.token}` };
        }
        return {};
    }

    /**
     * Refresh the access token using the stored refresh token
     * @returns {boolean} true if refresh succeeded, false otherwise
     */
    async refreshAccessToken() {
        if (!this.refreshToken) {
            return false;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: this.refreshToken })
            });

            if (!response.ok) {
                this.clearSession();
                return false;
            }

            const data = await response.json();
            this.token = data.access_token;
            localStorage.setItem('auth_token', data.access_token);
            // Save rotated refresh token
            if (data.refresh_token) {
                this.refreshToken = data.refresh_token;
                localStorage.setItem('refresh_token', data.refresh_token);
            }
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            this.clearSession();
            return false;
        }
    }

    /**
     * Register a new user
     */
    async register(username, email, password, firstName = '', lastName = '') {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    email,
                    password,
                    first_name: firstName,
                    last_name: lastName
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Registration failed');
            }

            const data = await response.json();
            this.saveSession(data.token.access_token, data.token.refresh_token, data.user);
            return { success: true, user: data.user };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Login user
     */
    async login(username, password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    password
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Login failed');
            }

            const data = await response.json();
            this.saveSession(data.token.access_token, data.token.refresh_token, data.user);
            return { success: true, user: data.user };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Unregister all service workers and delete their caches, then reload.
     * This ensures the browser fetches fresh HTML/JS directly from the server,
     * bypassing any stale SW cache (e.g. old CACHE_NAME still holding old files).
     */
    async _clearSwAndReload() {
        if ('serviceWorker' in navigator) {
            try {
                const regs = await navigator.serviceWorker.getRegistrations();
                await Promise.all(regs.map(r => r.unregister()));
                const cacheKeys = await caches.keys();
                await Promise.all(cacheKeys.map(k => caches.delete(k)));
            } catch (e) {
                // Ignore errors — we'll reload regardless
            }
        }
        window.location.reload();
    }

    /**
     * Logout user
     */
    logout() {
        this.clearSession();
        window.location.reload();
    }

    /**
     * Get current user profile
     */
    async getProfile() {
        if (!this.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/profile`, {
                method: 'GET',
                headers: {
                    ...this.getAuthHeader()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch profile');
            }

            const user = await response.json();
            this.currentUser = user;
            localStorage.setItem('current_user', JSON.stringify(user));
            return { success: true, user };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Get user statistics
     */
    async getStats() {
        if (!this.isLoggedIn()) {
            return { success: false, error: 'Not logged in' };
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/stats`, {
                method: 'GET',
                headers: {
                    ...this.getAuthHeader()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch stats');
            }

            const stats = await response.json();
            return { success: true, stats };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    /**
     * Show login modal
     */
    showLoginModal() {
        const modal = document.getElementById('auth-modal');
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');

        if (modal && loginForm && registerForm) {
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
            modal.style.display = 'flex';
        }
    }

    /**
     * Show register modal
     */
    showRegisterModal() {
        const modal = document.getElementById('auth-modal');
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');

        if (modal && loginForm && registerForm) {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
            modal.style.display = 'flex';
        }
    }

    /**
     * Hide auth modal
     */
    hideModal() {
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Initialize auth UI
     */
    initAuthUI() {
        const userSection = document.getElementById('user-section');
        const guestSection = document.getElementById('guest-section');
        const usernameDisplay = document.getElementById('username-display');

        if (this.isLoggedIn()) {
            if (userSection) userSection.style.display = 'flex';
            if (guestSection) guestSection.style.display = 'none';
            if (usernameDisplay) usernameDisplay.textContent = this.currentUser.username;
        } else {
            if (userSection) userSection.style.display = 'none';
            if (guestSection) guestSection.style.display = 'flex';
        }
    }

    /**
     * Check whether the stored access token is currently expired.
     */
    isTokenExpired() {
        const exp = this.getTokenExpiry();
        return exp !== null && Date.now() > exp;
    }

    /**
     * Setup auth event listeners
     */
    setupEventListeners() {
        // Login button
        const loginBtn = document.getElementById('show-login-btn');
        if (loginBtn) {
            loginBtn.addEventListener('click', () => this.showLoginModal());
        }

        // Register button
        const registerBtn = document.getElementById('show-register-btn');
        if (registerBtn) {
            registerBtn.addEventListener('click', () => this.showRegisterModal());
        }

        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }

        // Switch to register
        const switchToRegister = document.getElementById('switch-to-register');
        if (switchToRegister) {
            switchToRegister.addEventListener('click', (e) => {
                e.preventDefault();
                this.showRegisterModal();
            });
        }

        // Switch to login
        const switchToLogin = document.getElementById('switch-to-login');
        if (switchToLogin) {
            switchToLogin.addEventListener('click', (e) => {
                e.preventDefault();
                this.showLoginModal();
            });
        }

        // Close modal
        const closeModal = document.getElementById('close-auth-modal');
        if (closeModal) {
            closeModal.addEventListener('click', () => this.hideModal());
        }

        // Close on backdrop click
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal();
                }
            });
        }

        // Login form submit
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const username = document.getElementById('login-username').value;
                const password = document.getElementById('login-password').value;
                const errorDiv = document.getElementById('login-error');

                const result = await this.login(username, password);
                if (result.success) {
                    window.location.reload();
                } else {
                    errorDiv.textContent = result.error;
                    errorDiv.style.display = 'block';
                }
            });
        }

        // Register form submit
        const registerFormElement = document.getElementById('register-form');
        if (registerFormElement) {
            registerFormElement.addEventListener('submit', async (e) => {
                e.preventDefault();
                const username = document.getElementById('register-username').value;
                const email = document.getElementById('register-email').value;
                const password = document.getElementById('register-password').value;
                const confirmPassword = document.getElementById('register-confirm-password').value;
                const firstName = document.getElementById('register-first-name').value;
                const lastName = document.getElementById('register-last-name').value;
                const errorDiv = document.getElementById('register-error');

                if (password !== confirmPassword) {
                    errorDiv.textContent = 'Passwords do not match';
                    errorDiv.style.display = 'block';
                    return;
                }

                const result = await this.register(username, email, password, firstName, lastName);
                if (result.success) {
                    window.location.reload();
                } else {
                    errorDiv.textContent = result.error;
                    errorDiv.style.display = 'block';
                }
            });
        }
    }
}

/**
 * SessionMonitor
 *
 * Tracks user idle time and manages session lifecycle:
 *  - Active users (any interaction within the last 55 min): silently refresh
 *    the access token before it expires so the session extends indefinitely.
 *  - Idle users: warn at 55 min, force logout at 60 min.
 *  - On tab focus (visibilitychange): run an immediate check so returning to
 *    a backgrounded tab never silently leaves the user in a broken state.
 *
 * Activity is persisted in localStorage so multiple tabs share idle state.
 */
class SessionMonitor {
    constructor(authManager) {
        this.authManager = authManager;
        this.IDLE_WARN_MS  = 55 * 60 * 1000;  // warn after 55 min idle
        this.IDLE_LOGOUT_MS = 60 * 60 * 1000; // logout after 60 min idle
        this.REFRESH_AHEAD_MS = 5 * 60 * 1000; // refresh when <5 min left on token
        this.CHECK_INTERVAL_MS = 30 * 1000;    // check every 30 seconds
        this._interval = null;
        this._warnShown = false;
        this._activityThrottle = 0;            // prevents flooding localStorage
    }

    start() {
        this._recordActivity();

        // Track activity from any tab interaction
        ['click', 'keydown', 'touchstart'].forEach(evt =>
            document.addEventListener(evt, () => this._onActivity(), { passive: true })
        );

        // Scroll is high-frequency — throttle to once per 10 seconds
        document.addEventListener('scroll', () => {
            const now = Date.now();
            if (now - this._activityThrottle > 10_000) {
                this._activityThrottle = now;
                this._onActivity();
            }
        }, { passive: true });

        // Immediate check when tab comes back into focus
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') this._tick();
        });

        this._interval = setInterval(() => this._tick(), this.CHECK_INTERVAL_MS);
    }

    stop() {
        clearInterval(this._interval);
        this._removeWarningModal();
    }

    _onActivity() {
        this._recordActivity();
        // If the warning is showing and the user just interacted, dismiss it
        if (this._warnShown) {
            this._removeWarningModal();
            this._warnShown = false;
        }
    }

    _recordActivity() {
        localStorage.setItem('av_last_activity', Date.now().toString());
    }

    _idleMs() {
        const last = parseInt(localStorage.getItem('av_last_activity') || '0');
        return Date.now() - last;
    }

    async _tick() {
        if (!this.authManager.isLoggedIn()) { this.stop(); return; }

        const idle = this._idleMs();

        // Proactively refresh if token is close to expiry AND user is active
        if (idle < this.IDLE_WARN_MS) {
            const exp = this.authManager.getTokenExpiry();
            if (exp && (exp - Date.now()) < this.REFRESH_AHEAD_MS) {
                await this.authManager.refreshAccessToken();
            }
        }

        // Force logout at 60 min idle
        if (idle >= this.IDLE_LOGOUT_MS) {
            this._expireSession();
            return;
        }

        // Show warning at 55 min idle
        if (idle >= this.IDLE_WARN_MS && !this._warnShown) {
            const minsLeft = Math.ceil((this.IDLE_LOGOUT_MS - idle) / 60_000);
            this._showWarningModal(minsLeft);
            this._warnShown = true;
        }
    }

    _showWarningModal(minsLeft) {
        if (document.getElementById('session-warning-modal')) return;

        const modal = document.createElement('div');
        modal.id = 'session-warning-modal';
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            display: flex; align-items: center; justify-content: center;
            z-index: 9999; background: rgba(0,0,0,0.5);
        `;
        modal.innerHTML = `
            <div style="
                background: var(--surface, #1e1b4b);
                border: 1px solid var(--border, rgba(255,255,255,0.1));
                border-radius: 8px; padding: 28px 32px; max-width: 380px; width: 90%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.4); text-align: center;
            ">
                <div style="font-size: 2rem; margin-bottom: 12px;">⏱</div>
                <h3 style="margin: 0 0 8px; color: var(--text-primary, #fff); font-size: 1.1rem;">
                    Session Expiring Soon
                </h3>
                <p style="margin: 0 0 24px; color: var(--text-secondary, rgba(255,255,255,0.7)); font-size: 0.9rem;">
                    You'll be logged out in <strong id="session-countdown">${minsLeft} minute${minsLeft !== 1 ? 's' : ''}</strong>
                    due to inactivity.
                </p>
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button id="session-stay-btn" style="
                        padding: 9px 20px; border-radius: 6px; border: none; cursor: pointer;
                        background: var(--accent, #7c3aed); color: #fff; font-size: 0.9rem; font-weight: 500;
                    ">Stay Logged In</button>
                    <button id="session-logout-btn" style="
                        padding: 9px 20px; border-radius: 6px; cursor: pointer;
                        background: transparent; color: var(--text-secondary, rgba(255,255,255,0.6));
                        border: 1px solid var(--border, rgba(255,255,255,0.15)); font-size: 0.9rem;
                    ">Log Out Now</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        document.getElementById('session-stay-btn').addEventListener('click', async () => {
            const ok = await this.authManager.refreshAccessToken();
            if (ok) {
                this._recordActivity();
                this._removeWarningModal();
                this._warnShown = false;
            } else {
                this._expireSession();
            }
        });

        document.getElementById('session-logout-btn').addEventListener('click', () => {
            this.authManager.logout();
        });
    }

    _removeWarningModal() {
        const modal = document.getElementById('session-warning-modal');
        if (modal) modal.remove();
    }

    _expireSession() {
        this.stop();
        this.authManager.clearSession();
        localStorage.setItem('av_session_expired', '1');
        window.location.reload();
    }
}
