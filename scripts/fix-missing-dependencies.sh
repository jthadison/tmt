#!/bin/bash
# TMT Trading System - Fix Missing Dependencies Script

set -e

echo "🔧 Fixing Missing Dependencies in TMT Services"
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

print_status "Stopping affected services..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" stop orchestrator circuit-breaker

print_status "Removing old containers..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" rm -f orchestrator circuit-breaker

print_status "Rebuilding orchestrator with aiohttp dependency..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build --no-cache orchestrator

print_status "Rebuilding circuit-breaker with aiohttp dependency..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build --no-cache circuit-breaker

print_status "Starting Redis (dependency)..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d redis

print_status "Waiting for Redis..."
sleep 10

print_status "Starting orchestrator..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d orchestrator

print_status "Waiting for orchestrator to start (45 seconds)..."
sleep 45

print_status "Testing orchestrator health..."
if curl -f -s http://192.168.50.137:8089/health > /dev/null; then
    print_success "✅ Orchestrator is now working!"
else
    print_error "❌ Orchestrator still failing, checking logs..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail=20 orchestrator
fi

print_status "Starting circuit-breaker..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d circuit-breaker

print_status "Waiting for circuit-breaker (30 seconds)..."
sleep 30

print_status "Testing circuit-breaker health..."
if curl -f -s http://192.168.50.137:8084/health > /dev/null; then
    print_success "✅ Circuit-breaker is now working!"
else
    print_warning "⚠️  Circuit-breaker may still be starting..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail=10 circuit-breaker
fi

print_status "Current service status:"
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo ""
print_success "🎉 Dependency fix completed!"
echo ""
echo "📊 Test health endpoints:"
echo "  • Orchestrator: http://192.168.50.137:8089/health"
echo "  • Circuit-breaker: http://192.168.50.137:8084/health"
echo ""
echo "🚀 Run full test suite:"
echo "  ./scripts/test-health-endpoints.sh"