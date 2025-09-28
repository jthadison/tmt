#!/bin/bash
# TMT Trading System - Minimal Staging Test Script
# Start only essential services to isolate issues

set -e

echo "🔬 TMT Trading System - Minimal Service Test"
echo "============================================"

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

# Create minimal environment if missing
if [ ! -f "$ENV_FILE" ]; then
    print_status "Creating minimal .env.staging..."
    cat > "$ENV_FILE" <<EOF
# Minimal staging configuration for testing
OANDA_API_KEY=demo_key_for_testing
OANDA_ACCOUNT_IDS=demo_account_for_testing
OANDA_ENVIRONMENT=practice
ENABLE_TRADING=false
ENVIRONMENT=staging
LOG_LEVEL=DEBUG
REDIS_URL=redis://redis:6379
HOST=0.0.0.0
EOF
    print_success "Created minimal .env.staging"
fi

print_status "Stopping all services..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down

print_status "Starting Redis only..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d redis

print_status "Waiting for Redis (10 seconds)..."
sleep 10

print_status "Testing Redis..."
if docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec redis redis-cli ping | grep -q PONG; then
    print_success "Redis is working"
else
    print_error "Redis failed"
    exit 1
fi

print_status "Starting Dashboard only (to test Next.js)..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d dashboard

print_status "Waiting for Dashboard (30 seconds)..."
sleep 30

print_status "Testing Dashboard..."
if curl -f -s http://192.168.50.137:3003/api/health > /dev/null; then
    print_success "Dashboard is working"
else
    print_warning "Dashboard health check failed, checking logs..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail=20 dashboard
fi

print_status "Starting Orchestrator only..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d orchestrator

print_status "Waiting for Orchestrator (45 seconds)..."
sleep 45

print_status "Testing Orchestrator..."
if curl -f -s http://192.168.50.137:8089/health > /dev/null; then
    print_success "Orchestrator is working"
else
    print_error "Orchestrator health check failed"
    print_status "Orchestrator logs (last 30 lines):"
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail=30 orchestrator

    print_status "Checking if orchestrator container is running:"
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps orchestrator

    print_status "Testing orchestrator from inside container:"
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec orchestrator python -c "
import urllib.request
try:
    response = urllib.request.urlopen('http://localhost:8089/health', timeout=5)
    print('Internal health check successful:', response.read().decode())
except Exception as e:
    print('Internal health check failed:', str(e))
" 2>/dev/null || print_error "Could not test orchestrator internally"
fi

print_status "Current service status:"
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo ""
print_status "Minimal test completed. Check results above."
echo ""
print_status "If Orchestrator failed:"
echo "• Check environment variables in .env.staging"
echo "• Verify OANDA credentials (even demo ones need proper format)"
echo "• Check for Python import errors in logs"
echo "• Ensure all required dependencies are installed"