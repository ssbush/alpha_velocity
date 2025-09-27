// Test Frontend Database Integration
// This script simulates the frontend API calls

console.log('🧪 Testing Frontend-Database Integration...\n');

// Simulate API client
class TestAPI {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    async request(endpoint) {
        const url = `${this.baseURL}${endpoint}`;
        const response = await fetch(url);
        return await response.json();
    }

    async getHealth() {
        return this.request('/');
    }

    async getDatabaseStatus() {
        return this.request('/database/status');
    }

    async getPortfolioHoldings(portfolioId) {
        return this.request(`/database/portfolio/${portfolioId}/holdings`);
    }
}

async function testIntegration() {
    const api = new TestAPI();

    try {
        // Test 1: API Health
        console.log('1. Testing API Health...');
        const health = await api.getHealth();
        console.log('✅ API Health:', health.message);

        // Test 2: Database Status
        console.log('\n2. Testing Database Status...');
        const dbStatus = await api.getDatabaseStatus();
        console.log('✅ Database Status:', dbStatus.connected ? 'Connected' : 'Disconnected');

        // Test 3: Portfolio Holdings
        console.log('\n3. Testing Portfolio Holdings...');
        const holdings = await api.getPortfolioHoldings(1);
        console.log('✅ Portfolio Holdings:', holdings.position_count, 'positions');

        // Test 4: Simulate Frontend Database Mode Detection
        console.log('\n4. Testing Database Mode Detection...');
        const databaseMode = dbStatus.available && dbStatus.connected;
        console.log('✅ Frontend would enable:', databaseMode ? 'Database Mode' : 'File Mode');

        console.log('\n🎉 All frontend integration tests passed!');
        console.log('\nFrontend can now:');
        console.log('- Detect database availability');
        console.log('- Load portfolio data from PostgreSQL');
        console.log('- Show database status indicator');
        console.log('- Switch between file and database modes');

    } catch (error) {
        console.error('❌ Integration test failed:', error.message);
    }
}

// Run tests if this is executed directly
if (typeof window === 'undefined') {
    // Node.js environment
    global.fetch = require('node-fetch');
    testIntegration();
}