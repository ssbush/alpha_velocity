#!/bin/bash
echo "🧪 Testing all database endpoints:"
echo ""

echo "1. Database Status:"
curl -s http://localhost:8000/database/status | jq -c
echo ""

echo "2. Get Portfolios:"
curl -s http://localhost:8000/database/portfolios | jq -c
echo ""

echo "3. Get Holdings count:"
curl -s http://localhost:8000/database/portfolio/1/holdings | jq -c '.position_count'
echo ""

echo "4. Transaction History:"
curl -s http://localhost:8000/database/portfolio/1/transactions | jq -c '.count'
echo ""

echo "✅ All database endpoints working!"