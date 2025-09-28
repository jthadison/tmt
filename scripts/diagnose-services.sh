#!/bin/bash
# TMT Trading System - Service Diagnosis Script

set -e

echo "🔍 Diagnosing TMT Trading System Services"
echo "========================================"

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

# Function to check service logs
check_service_logs() {
    local service=$1
    local lines=${2:-20}

    print_status "Checking logs for $service (last $lines lines):"
    echo "----------------------------------------"
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail="$lines" "$service" || {
        print_error "Failed to get logs for $service"
        return 1
    }
    echo ""
}

# Function to test service health manually
test_service_health() {
    local service=$1
    local port=$2
    local path=${3:-"/health"}

    print_status "Testing $service health endpoint manually..."

    # Test from inside container
    docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec "$service" python -c "
import urllib.request
import urllib.error
try:
    response = urllib.request.urlopen('http://localhost:$port$path')
    print('Health check successful:', response.read().decode())
except urllib.error.URLError as e:
    print('Health check failed:', str(e))
except Exception as e:
    print('Error:', str(e))
" 2>/dev/null || print_error "Could not test $service health endpoint"
    echo ""
}

# Check overall container status
print_status "Current container status:"
docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
echo ""

# Check failing services
print_status "Checking services that are restarting or unhealthy..."

# List of services to check
declare -a services=("orchestrator" "execution-engine" "circuit-breaker" "market-analysis")
declare -a ports=("8089" "8082" "8084" "8001")

for i in "${!services[@]}"; do
    service="${services[$i]}"
    port="${ports[$i]}"

    # Check if service is running
    if docker-compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
        print_success "$service is running"
        test_service_health "$service" "$port"
    else
        print_error "$service is not running properly"
        check_service_logs "$service" 30
    fi
done

# Check environment variables
print_status "Checking critical environment variables..."
if [ -f "$ENV_FILE" ]; then
    print_status "Environment file exists: $ENV_FILE"
    if grep -q "OANDA_API_KEY" "$ENV_FILE"; then
        print_success "OANDA_API_KEY is set"
    else
        print_error "OANDA_API_KEY is missing from $ENV_FILE"
    fi

    if grep -q "OANDA_ACCOUNT_ID" "$ENV_FILE"; then
        print_success "OANDA_ACCOUNT_ID is set"
    else
        print_error "OANDA_ACCOUNT_ID is missing from $ENV_FILE"
    fi
else
    print_error "Environment file not found: $ENV_FILE"
fi

echo ""
print_status "Resource usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

echo ""
print_status "Troubleshooting suggestions:"
echo "• Check logs for specific error messages"
echo "• Ensure all required environment variables are set"
echo "• Verify services are binding to 0.0.0.0:PORT"
echo "• Check if services are waiting for dependencies"
echo "• Consider restarting services: docker-compose restart [service]"