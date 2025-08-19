#!/bin/bash

#############################################################################
# Trading System Launch Script
# Full system startup with health checks and OANDA integration
#############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
ENV_FILE="${PROJECT_ROOT}/.env"
LOG_DIR="${PROJECT_ROOT}/logs"
HEALTHCHECK_TIMEOUT=300  # 5 minutes
AGENT_DIR="${PROJECT_ROOT}/src/agents"

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if docker is running
check_docker() {
    print_message "$BLUE" "🔍 Checking Docker status..."
    if ! docker info > /dev/null 2>&1; then
        print_message "$RED" "❌ Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    print_message "$GREEN" "✅ Docker is running"
}

# Function to check for port conflicts
check_port_conflicts() {
    print_message "$BLUE" "🔍 Checking for port conflicts..."
    
    local ports=(5432 6379 9092 8200 3000 3001 16686 9090 9094)
    local conflicts=()
    
    for port in "${ports[@]}"; do
        # Check if port is in use (cross-platform)
        if command -v netstat > /dev/null 2>&1; then
            # Windows/Linux with netstat
            if netstat -an 2>/dev/null | grep -q ":$port.*LISTEN"; then
                # Check if it's one of our containers
                if ! docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -q "trading-.*$port"; then
                    conflicts+=($port)
                fi
            fi
        elif command -v lsof > /dev/null 2>&1; then
            # macOS/Linux with lsof
            if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                if ! docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -q "trading-.*$port"; then
                    conflicts+=($port)
                fi
            fi
        fi
    done
    
    if [ ${#conflicts[@]} -gt 0 ]; then
        print_message "$YELLOW" "⚠️  Port conflicts detected on: ${conflicts[*]}"
        print_message "$YELLOW" "   You can:"
        print_message "$YELLOW" "   1. Stop conflicting services"
        print_message "$YELLOW" "   2. Run: docker ps -a to check for old containers"
        print_message "$YELLOW" "   3. Run: docker-compose down to clean up"
        
        # Show what's using the ports
        for port in "${conflicts[@]}"; do
            print_message "$YELLOW" "   Port $port is in use by:"
            if command -v netstat > /dev/null 2>&1; then
                netstat -ano | grep ":$port.*LISTEN" | head -1 || true
            fi
        done
        
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_message "$GREEN" "✅ No port conflicts detected"
    fi
}

# Function to check environment variables
check_environment() {
    print_message "$BLUE" "🔍 Checking environment configuration..."
    
    local missing_vars=()
    
    # Check for .env file
    if [ ! -f "$ENV_FILE" ]; then
        print_message "$YELLOW" "⚠️  .env file not found. Creating from template..."
        if [ -f "${ENV_FILE}.example" ]; then
            cp "${ENV_FILE}.example" "$ENV_FILE"
            print_message "$YELLOW" "📝 Please edit .env file with your credentials"
        else
            print_message "$YELLOW" "📝 Creating basic .env file..."
            cat > "$ENV_FILE" << EOF
# OANDA Configuration
OANDA_API_KEY=your_api_key_here
OANDA_ACCOUNT_ID=your_account_id_here
OANDA_ENVIRONMENT=practice
OANDA_BASE_URL=https://api-fxpractice.oanda.com

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_system
REDIS_URL=redis://localhost:6379

# Kafka Configuration
KAFKA_BROKERS=localhost:9092

# Vault Configuration
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=dev-token-trading-system

# Monitoring
JAEGER_ENDPOINT=http://localhost:14268/api/traces
PROMETHEUS_PUSHGATEWAY=http://localhost:9091

# Trading Configuration
MAX_CONCURRENT_TRADES=3
RISK_PER_TRADE=0.02
MAX_DAILY_LOSS=0.06
CIRCUIT_BREAKER_THRESHOLD=0.10

# Agent Configuration
AGENT_LOG_LEVEL=INFO
AGENT_HEALTH_CHECK_INTERVAL=30
EOF
            print_message "$YELLOW" "⚠️  Please update .env file with your OANDA credentials"
            return 1
        fi
    fi
    
    # Source the env file
    source "$ENV_FILE"
    
    # Check required variables
    if [ -z "$OANDA_API_KEY" ] || [ "$OANDA_API_KEY" == "your_api_key_here" ]; then
        missing_vars+=("OANDA_API_KEY")
    fi
    
    if [ -z "$OANDA_ACCOUNT_ID" ] || [ "$OANDA_ACCOUNT_ID" == "your_account_id_here" ]; then
        missing_vars+=("OANDA_ACCOUNT_ID")
    fi
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_message "$RED" "❌ Missing or unconfigured environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "   - $var"
        done
        print_message "$YELLOW" "Please update your .env file"
        return 1
    fi
    
    print_message "$GREEN" "✅ Environment configured"
    return 0
}

# Function to create necessary directories
setup_directories() {
    print_message "$BLUE" "📁 Setting up directories..."
    
    mkdir -p "$LOG_DIR"
    mkdir -p "${PROJECT_ROOT}/data/postgres"
    mkdir -p "${PROJECT_ROOT}/data/redis"
    mkdir -p "${PROJECT_ROOT}/data/kafka"
    mkdir -p "${PROJECT_ROOT}/data/prometheus"
    mkdir -p "${PROJECT_ROOT}/data/grafana"
    
    print_message "$GREEN" "✅ Directories ready"
}

# Function to clean up old containers and volumes
cleanup_old_containers() {
    print_message "$BLUE" "🧹 Cleaning up old containers..."
    
    docker-compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
    
    # Optional: Clean up dangling images
    docker image prune -f > /dev/null 2>&1 || true
    
    print_message "$GREEN" "✅ Cleanup complete"
}

# Function to launch infrastructure services
launch_infrastructure() {
    print_message "$BLUE" "🚀 Launching infrastructure services..."
    
    # Start core services first
    docker-compose -f "$COMPOSE_FILE" up -d \
        postgres \
        redis \
        kafka \
        zookeeper \
        vault
    
    print_message "$YELLOW" "⏳ Waiting for core services to be healthy..."
    
    # Wait for PostgreSQL
    local postgres_ready=false
    for i in {1..60}; do
        if docker exec trading-postgres pg_isready -U postgres -d trading_system >/dev/null 2>&1; then
            postgres_ready=true
            break
        fi
        sleep 2
    done
    
    if [ "$postgres_ready" = false ]; then
        print_message "$RED" "❌ PostgreSQL failed to start"
        return 1
    fi
    print_message "$GREEN" "✅ PostgreSQL ready"
    
    # Wait for Redis
    local redis_ready=false
    for i in {1..30}; do
        if docker exec trading-redis redis-cli ping >/dev/null 2>&1; then
            redis_ready=true
            break
        fi
        sleep 2
    done
    
    if [ "$redis_ready" = false ]; then
        print_message "$RED" "❌ Redis failed to start"
        return 1
    fi
    print_message "$GREEN" "✅ Redis ready"
    
    # Wait for Kafka
    local kafka_ready=false
    for i in {1..60}; do
        if docker exec trading-kafka kafka-broker-api-versions --bootstrap-server localhost:9092 >/dev/null 2>&1; then
            kafka_ready=true
            break
        fi
        sleep 2
    done
    
    if [ "$kafka_ready" = false ]; then
        print_message "$RED" "❌ Kafka failed to start"
        return 1
    fi
    print_message "$GREEN" "✅ Kafka ready"
    
    print_message "$GREEN" "✅ Core infrastructure running"
}

# Function to launch monitoring stack
launch_monitoring() {
    print_message "$BLUE" "📊 Launching monitoring services..."
    
    docker-compose -f "$COMPOSE_FILE" up -d \
        prometheus \
        grafana \
        jaeger \
        alertmanager
    
    print_message "$GREEN" "✅ Monitoring stack launched"
}

# Function to launch dashboard
launch_dashboard() {
    print_message "$BLUE" "🖥️  Launching dashboard..."
    
    docker-compose -f "$COMPOSE_FILE" up -d dashboard
    
    print_message "$GREEN" "✅ Dashboard launched at http://localhost:3000"
}

# Function to run database migrations
run_migrations() {
    print_message "$BLUE" "🗄️  Running database migrations..."
    
    # Check if migration files exist
    if [ -d "${PROJECT_ROOT}/src/shared/schemas/migrations" ]; then
        # Migrations are auto-run via docker-entrypoint-initdb.d volume mount
        print_message "$GREEN" "✅ Migrations configured (auto-run on container start)"
    else
        print_message "$YELLOW" "⚠️  No migration files found"
    fi
}

# Function to initialize Kafka topics
setup_kafka_topics() {
    print_message "$BLUE" "📬 Setting up Kafka topics..."
    
    # Create required topics
    docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 \
        --create --if-not-exists --topic market-data \
        --partitions 3 --replication-factor 1 2>/dev/null || true
    
    docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 \
        --create --if-not-exists --topic trading-signals \
        --partitions 3 --replication-factor 1 2>/dev/null || true
    
    docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 \
        --create --if-not-exists --topic trade-executions \
        --partitions 3 --replication-factor 1 2>/dev/null || true
    
    docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 \
        --create --if-not-exists --topic risk-events \
        --partitions 1 --replication-factor 1 2>/dev/null || true
    
    docker exec trading-kafka kafka-topics --bootstrap-server localhost:9092 \
        --create --if-not-exists --topic audit-logs \
        --partitions 1 --replication-factor 1 2>/dev/null || true
    
    print_message "$GREEN" "✅ Kafka topics ready"
}

# Function to check OANDA connectivity
check_oanda_connection() {
    print_message "$BLUE" "🔌 Testing OANDA connectivity..."
    
    # Find Python executable
    local PYTHON_CMD=""
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    elif [ -f "C:/Python313/python.exe" ]; then
        PYTHON_CMD="C:/Python313/python.exe"
    elif [ -f "/c/Python313/python.exe" ]; then
        PYTHON_CMD="/c/Python313/python.exe"
    else
        print_message "$YELLOW" "⚠️  Python not found. Skipping OANDA connectivity test."
        print_message "$YELLOW" "   To enable OANDA testing, install Python or update PATH"
        return
    fi
    
    # Run the OANDA validation script
    if [ -f "${PROJECT_ROOT}/scripts/validate-oanda-connection.py" ]; then
        $PYTHON_CMD "${PROJECT_ROOT}/scripts/validate-oanda-connection.py"
    else
        print_message "$YELLOW" "⚠️  OANDA validation script not found. Skipping connectivity test."
    fi
}

# Function to launch Python agents
launch_agents() {
    print_message "$BLUE" "🤖 Launching trading agents..."
    
    # Check if agent launcher exists
    if [ -f "${PROJECT_ROOT}/scripts/launch-agents.sh" ]; then
        bash "${PROJECT_ROOT}/scripts/launch-agents.sh"
    else
        print_message "$YELLOW" "⚠️  Agent launcher not found. Please start agents manually."
        print_message "$YELLOW" "   Example: cd ${AGENT_DIR} && python -m <agent_name>"
    fi
}

# Function to display system status
display_status() {
    print_message "$BLUE" "\n📋 System Status:"
    echo "=================================="
    
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    print_message "$GREEN" "🎉 Trading System Successfully Launched!"
    echo ""
    print_message "$BLUE" "📌 Service URLs:"
    echo "   Dashboard:     http://localhost:3000"
    echo "   Grafana:       http://localhost:3001 (admin/admin)"
    echo "   Jaeger UI:     http://localhost:16686"
    echo "   Prometheus:    http://localhost:9090"
    echo "   Alertmanager:  http://localhost:9094"
    echo ""
    print_message "$BLUE" "📝 Logs:"
    echo "   View logs:     docker-compose logs -f [service-name]"
    echo "   All logs:      docker-compose logs -f"
    echo ""
    print_message "$BLUE" "🛑 To stop:"
    echo "   docker-compose down"
    echo ""
}

# Function to handle graceful shutdown
shutdown() {
    print_message "$YELLOW" "\n⚠️  Shutting down trading system..."
    docker-compose -f "$COMPOSE_FILE" down
    print_message "$GREEN" "✅ System stopped"
    exit 0
}

# Trap CTRL+C
trap shutdown SIGINT

# Main execution
main() {
    print_message "$BLUE" "🚀 Trading System Launcher v1.0"
    echo "=================================="
    
    # Parse command line arguments
    case "${1:-}" in
        --core)
            # Launch only core services
            check_docker
            check_port_conflicts
            check_environment || exit 1
            setup_directories
            cleanup_old_containers
            launch_infrastructure
            run_migrations
            setup_kafka_topics
            ;;
        --monitoring)
            # Launch with monitoring
            check_docker
            check_port_conflicts
            check_environment || exit 1
            setup_directories
            cleanup_old_containers
            launch_infrastructure
            launch_monitoring
            run_migrations
            setup_kafka_topics
            ;;
        --full)
            # Launch everything
            check_docker
            check_port_conflicts
            check_environment || exit 1
            setup_directories
            cleanup_old_containers
            launch_infrastructure
            launch_monitoring
            launch_dashboard
            run_migrations
            setup_kafka_topics
            check_oanda_connection
            launch_agents
            ;;
        --agents-only)
            # Launch only agents (assumes infrastructure is running)
            check_environment || exit 1
            check_oanda_connection
            launch_agents
            ;;
        --stop)
            # Stop everything
            shutdown
            ;;
        --status)
            # Show status only
            display_status
            exit 0
            ;;
        *)
            # Default: launch core + monitoring + dashboard
            check_docker
            check_port_conflicts
            check_environment || exit 1
            setup_directories
            cleanup_old_containers
            launch_infrastructure
            launch_monitoring
            launch_dashboard
            run_migrations
            setup_kafka_topics
            check_oanda_connection
            ;;
    esac
    
    # Display final status
    display_status
    
    print_message "$YELLOW" "⏳ System is running. Press CTRL+C to stop."
    
    # Keep script running
    while true; do
        sleep 1
    done
}

# Run main function
main "$@"