#!/bin/bash
set -e

echo "🏥 Adaptive Trading System Health Check"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_healthy() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to check HTTP endpoint
check_endpoint() {
    local url=$1
    local name=$2
    local timeout=${3:-5}
    
    if curl -s --max-time "$timeout" "$url" >/dev/null 2>&1; then
        print_healthy "$name is responding"
        return 0
    else
        print_error "$name is not responding at $url"
        return 1
    fi
}

# Function to check docker service
check_docker_service() {
    local service=$1
    if docker-compose ps -q "$service" >/dev/null 2>&1; then
        local status=$(docker-compose ps "$service" | grep "$service" | awk '{print $4}')
        if [[ "$status" == *"Up"* ]]; then
            print_healthy "Docker service $service is running"
            return 0
        else
            print_error "Docker service $service status: $status"
            return 1
        fi
    else
        print_error "Docker service $service not found"
        return 1
    fi
}

echo "🐳 Docker Services"
echo "---------------"
if command -v docker-compose >/dev/null 2>&1; then
    if [ -f "docker-compose.yml" ]; then
        # Check if any services are running
        if docker-compose ps -q | wc -l | grep -q "0"; then
            print_warning "No Docker services running. Start with: docker-compose up -d"
        else
            # List running services
            echo "Running services:"
            docker-compose ps --format "table {{.Name}}\t{{.State}}\t{{.Ports}}"
        fi
    else
        print_warning "docker-compose.yml not found"
    fi
else
    print_error "docker-compose not found"
fi

echo ""
echo "🌐 Service Health Checks"
echo "----------------------"

# Check database (if running)
if check_docker_service "postgres" 2>/dev/null; then
    if command -v psql >/dev/null 2>&1; then
        if psql "postgresql://postgres:password@localhost:5432/postgres" -c "SELECT 1;" >/dev/null 2>&1; then
            print_healthy "PostgreSQL connection successful"
        else
            print_error "PostgreSQL connection failed"
        fi
    else
        print_warning "psql not installed, skipping database connection test"
    fi
fi

# Check Redis (if running)
if check_docker_service "redis" 2>/dev/null; then
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -p 6379 ping >/dev/null 2>&1; then
            print_healthy "Redis connection successful"
        else
            print_error "Redis connection failed"
        fi
    else
        print_warning "redis-cli not installed, skipping Redis connection test"
    fi
fi

# Check web services
echo ""
echo "🔗 Endpoint Health Checks"
echo "------------------------"

# Dashboard
if check_endpoint "http://localhost:3000" "Dashboard" 10; then
    :
fi

# API Gateway (when implemented)
if check_endpoint "http://localhost:8000/health" "API Gateway" 5; then
    :
fi

# Execution Engine (when implemented)  
if check_endpoint "http://localhost:8080/health" "Execution Engine" 5; then
    :
fi

# Grafana (if running)
if check_endpoint "http://localhost:3001" "Grafana" 5; then
    :
fi

# Prometheus (if running)
if check_endpoint "http://localhost:9090" "Prometheus" 5; then
    :
fi

echo ""
echo "💾 System Resources"
echo "---------------"

# Check disk space
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    print_healthy "Disk usage: ${DISK_USAGE}%"
elif [ "$DISK_USAGE" -lt 90 ]; then
    print_warning "Disk usage: ${DISK_USAGE}% (getting high)"
else
    print_error "Disk usage: ${DISK_USAGE}% (critically high)"
fi

# Check memory usage
if command -v free >/dev/null 2>&1; then
    MEM_USAGE=$(free | awk 'NR==2{printf "%.1f", $3*100/$2 }')
    if (( $(echo "$MEM_USAGE < 80" | bc -l) )); then
        print_healthy "Memory usage: ${MEM_USAGE}%"
    elif (( $(echo "$MEM_USAGE < 90" | bc -l) )); then
        print_warning "Memory usage: ${MEM_USAGE}% (getting high)"
    else
        print_error "Memory usage: ${MEM_USAGE}% (critically high)"
    fi
fi

# Check Docker status
if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        print_healthy "Docker daemon is running"
    else
        print_error "Docker daemon is not accessible"
    fi
fi

echo ""
echo "📊 Summary"
echo "--------"
echo "Health check completed at $(date)"

# Return exit code based on critical failures
# For now, we'll always return 0 since this is informational
exit 0