#!/bin/bash

# TMT Trading System - Postman Setup Validation Script
# Verifies all services are running before using Postman collections

echo "🔍 TMT Trading System - Service Validation"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service configuration
SERVICES=(
    "Orchestrator:8089:/health"
    "Execution Engine:8082:/health"
    "Circuit Breaker:8084:/health"
    "Dashboard:3003:/"
    "Market Analysis:8001:/health"
    "Strategy Analysis:8002:/health" 
    "Parameter Optimization:8003:/health"
    "Learning Safety:8004:/health"
    "Disagreement Engine:8005:/health"
    "Data Collection:8006:/health"
    "Continuous Improvement:8007:/health"
    "Pattern Detection:8008:/health"
)

BASE_URL="http://localhost"
TIMEOUT=5

# Function to check service health
check_service() {
    local service_name=$1
    local port=$2
    local endpoint=$3
    local url="${BASE_URL}:${port}${endpoint}"
    
    echo -n "📊 Checking ${service_name} (${port})... "
    
    if curl -s --max-time $TIMEOUT "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ONLINE${NC}"
        return 0
    else
        echo -e "${RED}❌ OFFLINE${NC}"
        return 1
    fi
}

# Function to check port availability
check_port() {
    local port=$1
    if netstat -an 2>/dev/null | grep ":$port " > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Main validation
echo -e "\n${BLUE}🏗️ Core Infrastructure${NC}"
echo "========================"

core_services=("Orchestrator:8089:/health" "Execution Engine:8082:/health" "Circuit Breaker:8084:/health" "Dashboard:3003:/")
core_online=0

for service in "${core_services[@]}"; do
    IFS=':' read -r name port endpoint <<< "$service"
    if check_service "$name" "$port" "$endpoint"; then
        ((core_online++))
    fi
done

echo -e "\n${BLUE}🤖 8-Agent AI Ecosystem${NC}"
echo "========================="

agent_services=("Market Analysis:8001:/health" "Strategy Analysis:8002:/health" "Parameter Optimization:8003:/health" "Learning Safety:8004:/health" "Disagreement Engine:8005:/health" "Data Collection:8006:/health" "Continuous Improvement:8007:/health" "Pattern Detection:8008:/health")
agents_online=0

for service in "${agent_services[@]}"; do
    IFS=':' read -r name port endpoint <<< "$service"
    if check_service "$name" "$port" "$endpoint"; then
        ((agents_online++))
    fi
done

# Summary
echo -e "\n${BLUE}📊 System Status Summary${NC}"
echo "=========================="
echo -e "Core Infrastructure: ${core_online}/4 services online"
echo -e "AI Agent Ecosystem:  ${agents_online}/8 agents online"
echo -e "Total System:        $((core_online + agents_online))/12 services online"

# Recommendations
echo -e "\n${YELLOW}💡 Recommendations${NC}"
echo "=================="

if [ $((core_online + agents_online)) -eq 12 ]; then
    echo -e "${GREEN}✅ All services online! Ready for Postman testing.${NC}"
    echo ""
    echo "🚀 Next Steps:"
    echo "1. Import TMT_Trading_System_Complete.postman_collection.json"
    echo "2. Import TMT_Local_Development.postman_environment.json" 
    echo "3. Set your OANDA API key in environment variables"
    echo "4. Start testing with health check endpoints"
elif [ $core_online -eq 4 ]; then
    echo -e "${YELLOW}⚠️ Core infrastructure ready, but some agents offline.${NC}"
    echo "   You can test basic orchestrator and execution functions."
    echo "   Start missing agents for full functionality."
elif [ $core_online -gt 0 ]; then
    echo -e "${YELLOW}⚠️ Partial system availability.${NC}"
    echo "   Some core services are missing. Check service startup."
else
    echo -e "${RED}❌ No services detected.${NC}"
    echo "   Please start the TMT trading system services."
fi

# Service startup commands
if [ $((core_online + agents_online)) -lt 12 ]; then
    echo ""
    echo -e "${BLUE}🔧 Service Startup Commands${NC}"
    echo "============================"
    echo ""
    echo "# Core Infrastructure:"
    echo "cd orchestrator && OANDA_API_KEY=your_key OANDA_ACCOUNT_IDS=your_account ENABLE_TRADING=true PORT=8089 python -m app.main &"
    echo "cd execution-engine && PORT=8082 python simple_main.py &"
    echo "cd agents/circuit-breaker && PORT=8084 python main.py &"  
    echo "cd dashboard && npm run dev &"
    echo ""
    echo "# AI Agent Ecosystem:"
    echo "cd agents/market-analysis && PORT=8001 python simple_main.py &"
    echo "cd agents/strategy-analysis && PORT=8002 python start_agent_simple.py &"
    echo "cd agents/parameter-optimization && PORT=8003 python start_agent.py &"
    echo "cd agents/learning-safety && PORT=8004 python start_agent.py &"
    echo "cd agents/disagreement-engine && PORT=8005 python start_agent.py &"
    echo "cd agents/data-collection && PORT=8006 python start_agent.py &"
    echo "cd agents/continuous-improvement && PORT=8007 python start_agent.py &"
    echo "cd agents/pattern-detection && PORT=8008 python start_agent_simple.py &"
fi

# Environment check
echo ""
echo -e "${BLUE}🌍 Environment Check${NC}"
echo "==================="

if [ -n "$OANDA_API_KEY" ]; then
    echo -e "OANDA_API_KEY: ${GREEN}✅ Set${NC}"
else
    echo -e "OANDA_API_KEY: ${YELLOW}⚠️ Not set (required for live testing)${NC}"
fi

if [ -n "$OANDA_ACCOUNT_ID" ]; then
    echo -e "OANDA_ACCOUNT_ID: ${GREEN}✅ Set${NC}"
else
    echo -e "OANDA_ACCOUNT_ID: ${YELLOW}⚠️ Not set (using default: 101-001-21040028-001)${NC}"
fi

echo ""
echo -e "${BLUE}📱 Access Points${NC}"
echo "==============="
echo "Dashboard:    http://localhost:3003"
echo "Orchestrator: http://localhost:8089/health"
echo "Exec Engine:  http://localhost:8082/health"
echo ""
echo -e "${GREEN}🎯 Ready to test with Postman!${NC}"

# Exit with appropriate code
if [ $core_online -eq 4 ]; then
    exit 0
else
    exit 1
fi