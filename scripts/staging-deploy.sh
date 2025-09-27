#!/bin/bash
# TMT Trading System - Staging Deployment Script

set -e

echo "🚀 Starting TMT Trading System Staging Deployment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.staging.yml"
ENV_FILE=".env.staging"

# Function to print colored output
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

# Pre-deployment checks
print_status "Running pre-deployment checks..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose >/dev/null 2>&1; then
    print_error "Docker Compose is not installed."
    exit 1
fi

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    print_error "Environment file $ENV_FILE not found."
    echo "Please copy .env.staging.template to .env.staging and configure it."
    exit 1
fi

# Check for required environment variables without sourcing
# Just verify they exist in the file
if ! grep -q "^OANDA_API_KEY=" "$ENV_FILE"; then
    print_error "OANDA_API_KEY not found in $ENV_FILE"
    print_error "Please set OANDA_API_KEY in your .env.staging file"
    exit 1
fi

if ! grep -q "^OANDA_ACCOUNT_ID=" "$ENV_FILE"; then
    print_error "OANDA_ACCOUNT_ID not found in $ENV_FILE"
    print_error "Please set OANDA_ACCOUNT_ID in your .env.staging file"
    exit 1
fi

print_success "Pre-deployment checks passed"

# Build and start services
print_status "Building Docker images..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build

print_status "Starting core infrastructure (Redis)..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d redis

# Wait for Redis to be ready
print_status "Waiting for Redis to be ready..."
timeout 30 bash -c 'until docker-compose --env-file .env.staging -f docker-compose.staging.yml exec redis redis-cli ping; do sleep 1; done'

print_status "Starting core services..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d orchestrator execution-engine circuit-breaker

# Wait for core services to be healthy
print_status "Waiting for core services to be healthy..."
sleep 30

# Check health of core services
print_status "Checking health of core services..."
for service in orchestrator execution-engine circuit-breaker; do
    if docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps "$service" | grep -q "healthy"; then
        print_success "$service is healthy"
    else
        print_warning "$service may not be fully ready yet"
    fi
done

print_status "Starting AI agents..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d \
    market-analysis \
    strategy-analysis \
    parameter-optimization \
    learning-safety \
    disagreement-engine \
    data-collection \
    continuous-improvement \
    pattern-detection

print_status "Starting dashboard and monitoring..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d dashboard prometheus grafana

# Final health check
print_status "Performing final health checks..."
sleep 30

# Display service status
print_status "Service Status:"
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

# Display important URLs
echo
print_success "🎉 Staging deployment completed!"
echo
echo "📊 Service URLs:"
echo "  • Dashboard:     http://localhost:3003"
echo "  • Orchestrator:  http://localhost:8089"
echo "  • Execution:     http://localhost:8082"
echo "  • Prometheus:    http://localhost:9090"
echo "  • Grafana:       http://localhost:3000 (admin/admin)"
echo
echo "🔧 Management Commands:"
echo "  • View logs:     docker-compose -f $COMPOSE_FILE logs -f [service]"
echo "  • Stop all:      docker-compose -f $COMPOSE_FILE down"
echo "  • Restart:       docker-compose -f $COMPOSE_FILE restart [service]"
echo
echo "⚠️  Important Notes:"
echo "  • Trading is disabled by default (ENABLE_TRADING=false)"
echo "  • Using practice account (OANDA_ENVIRONMENT=practice)"
echo "  • Conservative risk settings are applied"
echo "  • Monitor logs before enabling trading"
echo
print_warning "To enable trading, set ENABLE_TRADING=true in $ENV_FILE and restart orchestrator"
echo

# Show next steps
echo "🚀 Next Steps:"
echo "1. Monitor logs: docker-compose -f $COMPOSE_FILE logs -f"
echo "2. Check dashboard: http://localhost:3003"
echo "3. Verify all services are healthy"
echo "4. Test with small positions before enabling full trading"
echo "5. Monitor Slack notifications in your staging channel"