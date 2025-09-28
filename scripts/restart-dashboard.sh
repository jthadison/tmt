#!/bin/bash
# TMT Trading System - Restart Dashboard Script

set -e

echo "🔄 Restarting TMT Dashboard Service"
echo "=================================="

# Configuration
COMPOSE_FILE="docker-compose.staging.yml"
ENV_FILE=".env.staging"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Stop dashboard
print_status "Stopping dashboard service..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" stop dashboard

# Rebuild dashboard image
print_status "Rebuilding dashboard image..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build dashboard

# Start dashboard
print_status "Starting dashboard service..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d dashboard

# Wait and check health
print_status "Waiting for dashboard to be ready..."
sleep 15

# Test health endpoint
print_status "Testing health endpoint..."
if docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec dashboard curl -f http://localhost:3003/api/health; then
    print_success "Dashboard health check passed"
else
    echo "Health check failed, checking logs..."
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail=20 dashboard
fi

# Show status
print_status "Dashboard Status:"
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps dashboard

echo
print_success "🎉 Dashboard restart completed!"
echo
echo "📊 Access URLs:"
echo "  • Local:     http://localhost:3003"
echo "  • Network:   http://192.168.50.137:3003"
echo "  • Health:    http://192.168.50.137:3003/api/health"
echo
echo "🔑 Demo Login Credentials:"
echo "  • Email:     demo@trading.com"
echo "  • Password:  demo123"
echo "  • Note:      Mock authentication is enabled for staging"
echo
echo "🔧 Troubleshooting:"
echo "  • View logs: docker-compose -f $COMPOSE_FILE logs -f dashboard"
echo "  • Check status: docker-compose -f $COMPOSE_FILE ps dashboard"