#!/bin/bash
# TMT Trading System - Quick Staging Fix Script

set -e

echo "🚀 Quick Fix for TMT Trading System Staging Issues"
echo "================================================="

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

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    print_error "Environment file $ENV_FILE not found!"
    print_status "Creating minimal staging environment file..."

    cat > "$ENV_FILE" <<EOF
# TMT Trading System - Staging Environment (Auto-generated)
OANDA_API_KEY=demo_key_staging
OANDA_ACCOUNT_IDS=demo_account_staging
OANDA_ENVIRONMENT=practice
ENABLE_TRADING=false
TRADING_MODE=paper
ENVIRONMENT=staging
LOG_LEVEL=INFO
REDIS_URL=redis://redis:6379
JWT_SECRET_KEY=staging_jwt_secret_key
SESSION_SECRET=staging_session_secret
DEBUG=false
MAX_WORKERS=4
HEALTH_CHECK_INTERVAL=30
EOF

    print_warning "Created basic .env.staging file with demo values"
    print_warning "Update OANDA_API_KEY and OANDA_ACCOUNT_IDS with real values if needed"
fi

print_status "Stopping all services..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down

print_status "Removing any problematic containers..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" rm -f

print_status "Pulling latest images..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull --ignore-pull-failures

print_status "Starting Redis first..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d redis

print_status "Waiting for Redis..."
sleep 10

print_status "Starting core services..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d orchestrator execution-engine circuit-breaker

print_status "Waiting for core services..."
sleep 30

print_status "Starting remaining services..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

print_status "Waiting for all services to start..."
sleep 30

print_status "Final service status:"
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo ""
print_success "🎉 Quick fix completed!"
echo ""
echo "📊 Service URLs:"
echo "  • Dashboard:     http://192.168.50.137:3003 (demo@trading.com / demo123)"
echo "  • Orchestrator:  http://192.168.50.137:8089/health"
echo "  • Execution:     http://192.168.50.137:8082/health"
echo "  • Circuit Breaker: http://192.168.50.137:8084/health"
echo ""
echo "🔧 Test health endpoints:"
echo "  ./scripts/test-health-endpoints.sh"
echo ""
echo "🔍 If issues persist:"
echo "  ./scripts/diagnose-services.sh"