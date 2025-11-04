/**
 * Authentication Manager
 * Handles user login, registration, and session management
 */

class AuthManager {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.currentUser = null;
        this.token = null;
        this.loadSession();
    }

    /**
     * Load session from localStorage
     */
    loadSession() {
        const token = localStorage.getItem('auth_token');
        const userStr = localStorage.getItem('current_user');

        if (token && userStr) {
            this.token = token;
            this.currentUser = JSON.parse(userStr);
        }
    }

    /**
     * Save session to localStorage
     */
    saveSession(token, user) {
        this.token = token;
        this.currentUser = user;
        localStorage.setItem('auth_token', token);
        localStorage.setItem('current_user', JSON.stringify(user));
    }

    /**
     * Clear session
     */
    clearSession() {
        this.token = null;
        this.currentUser = null;
        localStorage.removeItem('auth_token');
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
            this.saveSession(data.token.access_token, data.user);
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
            this.saveSession(data.token.access_token, data.user);
            return { success: true, user: data.user };
        } catch (error) {
            return { success: false, error: error.message };
        }
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
                    this.hideModal();
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
                    this.hideModal();
                    window.location.reload();
                } else {
                    errorDiv.textContent = result.error;
                    errorDiv.style.display = 'block';
                }
            });
        }
    }
}
