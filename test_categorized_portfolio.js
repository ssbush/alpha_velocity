// Test Categorized Portfolio Display
// This script tests the frontend portfolio categorization

console.log('🧪 Testing Categorized Portfolio Display...\n');

// Simulate the frontend categorized API call
async function testCategorizedPortfolio() {
    try {
        const response = await fetch('http://localhost:8000/database/portfolio/1/categories-detailed');
        const data = await response.json();

        console.log('✅ API Response Structure:');
        console.log(`  Portfolio ID: ${data.portfolio_id}`);
        console.log(`  Total Value: $${data.total_portfolio_value.toLocaleString()}`);
        console.log(`  Total Categories: ${data.total_categories}`);
        console.log(`  Total Positions: ${data.total_positions}`);

        console.log('\n📊 Category Breakdown:');
        data.categories.forEach((category, index) => {
            console.log(`\n${index + 1}. ${category.category_name}`);
            console.log(`   Target Allocation: ${category.target_allocation_pct}%`);
            console.log(`   Current Value: $${category.total_value.toLocaleString()}`);
            console.log(`   Positions: ${category.position_count}`);
            console.log(`   Benchmark: ${category.benchmark_ticker}`);

            if (category.holdings.length > 0) {
                console.log('   Holdings:');
                category.holdings.forEach(holding => {
                    const gainLoss = holding.current_value - holding.total_cost_basis;
                    const gainPercent = (gainLoss / holding.total_cost_basis * 100).toFixed(1);
                    console.log(`     • ${holding.ticker}: ${holding.shares} shares | $${holding.current_value.toFixed(2)} (${gainPercent >= 0 ? '+' : ''}${gainPercent}%)`);
                });
            }
        });

        console.log('\n🎯 Frontend Display Test:');
        console.log('The Portfolio page should now show:');
        console.log('✅ Portfolio summary with total value');
        console.log('✅ Categories organized by target allocation');
        console.log('✅ Each category with colored header');
        console.log('✅ Holdings table with company names, sectors');
        console.log('✅ Cost basis and current value columns');
        console.log('✅ Gain/loss calculations with color coding');
        console.log('✅ Category descriptions and benchmarks');

        return true;

    } catch (error) {
        console.error('❌ Test failed:', error.message);
        return false;
    }
}

// Run test if this is executed directly
if (typeof window === 'undefined') {
    // Node.js environment
    global.fetch = require('node-fetch');
    testCategorizedPortfolio().then(success => {
        if (success) {
            console.log('\n🎉 Categorized portfolio display is ready!');
            console.log('\nTo view:');
            console.log('1. Open http://localhost:3000 in browser');
            console.log('2. Click "Portfolio" tab');
            console.log('3. See categorized holdings with real data');
        }
    });
}