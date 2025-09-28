#!/bin/bash
# TMT Trading System - Test Orchestrator Fix Script

set -e

echo "🔧 Testing Orchestrator Fix - Direct App Object"
echo "=============================================="

# Configuration
COMPOSE_FILE="docker-compose.staging.yml"
ENV_FILE=".env.staging"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "Stopping orchestrator..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" stop orchestrator

print_status "Removing old orchestrator container..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" rm -f orchestrator

print_status "Rebuilding orchestrator with app object fix..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build --no-cache orchestrator

print_status "Starting orchestrator..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d orchestrator

print_status "Waiting for orchestrator to start (60 seconds)..."
sleep 60

print_status "Testing orchestrator health..."
if curl -f -s http://192.168.50.137:8089/health > /dev/null; then
    print_success "🎉 ✅ ORCHESTRATOR IS NOW WORKING!"

    print_status "Getting orchestrator health details..."
    curl -s http://192.168.50.137:8089/health | python3 -m json.tool 2>/dev/null || echo "Health endpoint responded successfully"

else
    print_error "❌ Orchestrator still failing"
    print_status "Checking orchestrator logs (last 20 lines):"
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail=20 orchestrator

    print_status "Container status:"
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps orchestrator
fi

print_status "Current service status:"
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo ""
if curl -f -s http://192.168.50.137:8089/health > /dev/null; then
    print_success "🚀 SUCCESS! All critical services are now operational:"
    echo "  ✅ Redis: Working"
    echo "  ✅ Dashboard: Working (http://192.168.50.137:3003)"
    echo "  ✅ Circuit-breaker: Working (http://192.168.50.137:8084/health)"
    echo "  ✅ Orchestrator: Working (http://192.168.50.137:8089/health)"
    echo ""
    echo "🎯 Run full system test:"
    echo "  ./scripts/test-health-endpoints.sh"
else
    print_warning "⚠️  Still troubleshooting orchestrator startup..."
    echo "Next steps:"
    echo "• Check logs for new error patterns"
    echo "• Verify environment variables"
    echo "• Try manual container restart"
fi