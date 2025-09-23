#!/bin/bash

# Trading System Docker Startup Script
echo "🚀 Starting TMT Trading System in Docker..."

# Check if .env.docker exists
if [ ! -f .env.docker ]; then
    echo "❌ .env.docker file not found!"
    echo "Please copy .env.docker.example to .env.docker and configure your OANDA API credentials"
    exit 1
fi

# Load environment variables
set -a
source .env.docker
set +a

echo "📋 Configuration:"
echo "  OANDA Environment: ${OANDA_ENVIRONMENT:-practice}"
echo "  Trading Enabled: ${ENABLE_TRADING:-true}"
echo "  Account IDs: ${OANDA_ACCOUNT_IDS:-101-001-21040028-001}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Build and start core services
echo "🏗️  Building and starting core services..."
docker-compose -f docker-compose.current.yml up --build -d \
    orchestrator \
    market-analysis \
    execution-engine \
    dashboard

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
services=("orchestrator:8089" "market-analysis:8001" "execution-engine:8082" "dashboard:3000")

for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)

    if curl -f http://localhost:$port/health >/dev/null 2>&1 || curl -f http://localhost:$port >/dev/null 2>&1; then
        echo "  ✅ $name (port $port) - healthy"
    else
        echo "  ❌ $name (port $port) - not responding"
    fi
done

echo ""
echo "🎯 Trading System is running!"
echo "📊 Dashboard: http://localhost:3000"
echo "🤖 Orchestrator: http://localhost:8089/health"
echo "📈 Market Analysis: http://localhost:8001/health"
echo "⚡ Execution Engine: http://localhost:8082/health"
echo ""
echo "To start all AI agents:"
echo "  docker-compose -f docker-compose.current.yml up -d"
echo ""
echo "To stop the system:"
echo "  docker-compose -f docker-compose.current.yml down"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.current.yml logs -f [service-name]"