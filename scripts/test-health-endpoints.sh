#!/bin/bash
# TMT Trading System - Health Check Test Script

set -e

echo "🏥 Testing TMT Trading System Health Endpoints"
echo "=============================================="

# Configuration
COMPOSE_FILE="docker-compose.staging.yml"
ENV_FILE=".env.staging"
SERVER_IP="192.168.50.137"

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

# Function to test URL
test_url() {
    local url=$1
    local service_name=$2

    print_status "Testing $service_name: $url"

    if curl -f -s -m 5 "$url" > /dev/null 2>&1; then
        print_success "$service_name health check passed"
        return 0
    else
        print_error "$service_name health check failed"
        return 1
    fi
}

# Test internal container health
print_status "Checking Docker container health status..."
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

echo ""
print_status "Testing external health endpoints..."

# Test all service health endpoints
declare -a services=(
    "dashboard:http://$SERVER_IP:3003/api/health"
    "orchestrator:http://$SERVER_IP:8089/health"
    "execution-engine:http://$SERVER_IP:8082/health"
    "circuit-breaker:http://$SERVER_IP:8084/health"
    "market-analysis:http://$SERVER_IP:8001/health"
)

failed_count=0
total_count=${#services[@]}

for service_info in "${services[@]}"; do
    IFS=':' read -r service_name url <<< "$service_info"
    if ! test_url "$url" "$service_name"; then
        ((failed_count++))
    fi
    echo ""
done

# Summary
echo "=============================================="
if [ $failed_count -eq 0 ]; then
    print_success "🎉 All $total_count health checks passed!"
else
    print_warning "⚠️  $failed_count out of $total_count health checks failed"
fi

echo ""
print_status "Debugging information:"
echo "• Check container logs: docker-compose -f $COMPOSE_FILE logs [service]"
echo "• Check service status: docker-compose -f $COMPOSE_FILE ps"
echo "• Restart services: docker-compose -f $COMPOSE_FILE restart [service]"
echo ""

if [ $failed_count -gt 0 ]; then
    print_status "Common issues:"
    echo "• Service may still be starting up (wait 30-60 seconds)"
    echo "• Health endpoint may not be implemented"
    echo "• Service may be binding to 127.0.0.1 instead of 0.0.0.0"
    echo "• Python urllib or Node.js HTTP modules missing in container"
fi

exit $failed_count