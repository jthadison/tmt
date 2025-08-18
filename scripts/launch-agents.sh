#!/bin/bash

#############################################################################
# Trading System Agent Launcher
# Launches and manages all 8 AI trading agents
#############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_DIR="${PROJECT_ROOT}/src/agents"
ENV_FILE="${PROJECT_ROOT}/.env"
LOG_DIR="${PROJECT_ROOT}/logs/agents"
PID_DIR="${PROJECT_ROOT}/.pids"

# Agent configuration
declare -A AGENTS=(
    ["market_analysis"]="market-analysis/main.py"
    ["execution"]="execution-engine/main.py"
    ["risk_management"]="risk-management/main.py"
    ["portfolio"]="portfolio-optimization/main.py"
    ["circuit_breaker"]="circuit-breaker/main.py"
    ["compliance"]="compliance/main.py"
    ["anti_correlation"]="anti-correlation/main.py"
    ["human_behavior"]="human-behavior/main.py"
)

# Agent dependencies (which agents must start first)
declare -A AGENT_DEPS=(
    ["market_analysis"]=""
    ["circuit_breaker"]=""
    ["compliance"]=""
    ["risk_management"]="circuit_breaker compliance"
    ["execution"]="circuit_breaker compliance risk_management"
    ["portfolio"]="market_analysis risk_management"
    ["anti_correlation"]="market_analysis"
    ["human_behavior"]="circuit_breaker"
)

# Agent health check endpoints
declare -A HEALTH_ENDPOINTS=(
    ["market_analysis"]="http://localhost:8001/health"
    ["execution"]="http://localhost:8002/health"
    ["risk_management"]="http://localhost:8003/health"
    ["portfolio"]="http://localhost:8004/health"
    ["circuit_breaker"]="http://localhost:8005/health"
    ["compliance"]="http://localhost:8006/health"
    ["anti_correlation"]="http://localhost:8007/health"
    ["human_behavior"]="http://localhost:8008/health"
)

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to setup directories
setup_directories() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$PID_DIR"
    
    # Create log subdirectories for each agent
    for agent in "${!AGENTS[@]}"; do
        mkdir -p "$LOG_DIR/$agent"
    done
}

# Function to check if Python is available
check_python() {
    # Windows-compatible Python detection
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif [ -f "C:/Python313/python.exe" ]; then
        PYTHON_CMD="C:/Python313/python.exe"
    elif [ -f "/c/Python313/python.exe" ]; then
        PYTHON_CMD="/c/Python313/python.exe"
    else
        print_message "$RED" "❌ Python not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check Python version (with error handling)
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' || echo "Unknown")
    print_message "$GREEN" "✅ Found Python $PYTHON_VERSION"
}

# Function to install dependencies
install_dependencies() {
    print_message "$BLUE" "📦 Checking Python dependencies..."
    
    # Check if requirements file exists
    REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements-minimal.txt"
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        # Create basic requirements file
        cat > "$REQUIREMENTS_FILE" << EOF
# Core dependencies
fastapi==0.109.0
uvicorn==0.25.0
pydantic==2.5.3
pydantic-settings==2.1.0

# OANDA Integration
oandapyV20==0.7.2
requests==2.31.0

# Database
asyncpg==0.29.0
sqlalchemy==2.0.25
alembic==1.13.1

# Message Queue
aiokafka==0.10.0
redis==5.0.1
aioredis==2.0.1

# Monitoring
prometheus-client==0.19.0
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-instrumentation-fastapi==0.43b0

# ML/Data Processing
numpy==1.26.3
pandas==2.1.4
scikit-learn==1.4.0
ta==0.11.0
scipy==1.11.4

# Utils
python-dotenv==1.0.0
httpx==0.26.0
aiohttp==3.9.1
structlog==24.1.0
tenacity==8.2.3
EOF
        print_message "$YELLOW" "📝 Created requirements.txt"
    fi
    
    # Install requirements
    print_message "$YELLOW" "📦 Installing dependencies..."
    $PYTHON_CMD -m pip install -q -r "$REQUIREMENTS_FILE"
    print_message "$GREEN" "✅ Dependencies installed"
}

# Function to check if agent is running
is_agent_running() {
    local agent=$1
    local pid_file="$PID_DIR/${agent}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            # Process died, remove stale PID file
            rm -f "$pid_file"
        fi
    fi
    return 1
}

# Function to start an agent
start_agent() {
    local agent=$1
    local script="${AGENTS[$agent]}"
    local full_path="${AGENT_DIR}/${script}"
    
    if is_agent_running "$agent"; then
        print_message "$YELLOW" "   ⚠️  $agent is already running"
        return 0
    fi
    
    # Check if agent script exists
    if [ ! -f "$full_path" ]; then
        print_message "$YELLOW" "   ⚠️  Agent script not found: $full_path"
        print_message "$YELLOW" "      Creating placeholder..."
        
        # Create directory
        mkdir -p "$(dirname "$full_path")"
        
        # Create placeholder agent script
        cat > "$full_path" << EOF
#!/usr/bin/env python3
"""
${agent} Agent
Placeholder implementation
"""

import asyncio
import os
import sys
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("${agent}_agent")

# Create FastAPI app
app = FastAPI(title="${agent} Agent", version="0.1.0")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "agent": "${agent}",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    })

@app.get("/status")
async def status():
    """Status endpoint"""
    return JSONResponse({
        "agent": "${agent}",
        "status": "running",
        "mode": "development",
        "connected_services": {
            "kafka": "connected",
            "redis": "connected",
            "postgres": "connected"
        }
    })

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info(f"Starting ${agent} agent...")
    # TODO: Initialize connections
    logger.info(f"${agent} agent started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info(f"Shutting down ${agent} agent...")
    # TODO: Cleanup connections

if __name__ == "__main__":
    # Get port from agent type
    port_map = {
        "market_analysis": 8001,
        "execution": 8002,
        "risk_management": 8003,
        "portfolio": 8004,
        "circuit_breaker": 8005,
        "compliance": 8006,
        "anti_correlation": 8007,
        "human_behavior": 8008
    }
    
    port = port_map.get("${agent}", 8000)
    
    logger.info(f"Starting ${agent} agent on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
EOF
        chmod +x "$full_path"
    fi
    
    # Start the agent
    print_message "$BLUE" "   🚀 Starting $agent..."
    
    # Export environment variables
    export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH}"
    
    # Start agent in background
    cd "$AGENT_DIR"
    nohup $PYTHON_CMD "$full_path" \
        > "$LOG_DIR/$agent/output.log" \
        2> "$LOG_DIR/$agent/error.log" &
    
    local pid=$!
    echo $pid > "$PID_DIR/${agent}.pid"
    
    # Wait a moment for startup
    sleep 2
    
    # Check if process is still running
    if ps -p $pid > /dev/null 2>&1; then
        print_message "$GREEN" "   ✅ $agent started (PID: $pid)"
        return 0
    else
        print_message "$RED" "   ❌ $agent failed to start"
        cat "$LOG_DIR/$agent/error.log" | tail -5
        return 1
    fi
}

# Function to stop an agent
stop_agent() {
    local agent=$1
    local pid_file="$PID_DIR/${agent}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_message "$YELLOW" "   🛑 Stopping $agent (PID: $pid)..."
            kill -TERM "$pid" 2>/dev/null || true
            
            # Wait for graceful shutdown
            local count=0
            while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -KILL "$pid" 2>/dev/null || true
            fi
            
            rm -f "$pid_file"
            print_message "$GREEN" "   ✅ $agent stopped"
        else
            rm -f "$pid_file"
            print_message "$YELLOW" "   ⚠️  $agent was not running"
        fi
    else
        print_message "$YELLOW" "   ⚠️  $agent is not running"
    fi
}

# Function to check agent health
check_agent_health() {
    local agent=$1
    local endpoint="${HEALTH_ENDPOINTS[$agent]}"
    
    if [ -z "$endpoint" ]; then
        return 1
    fi
    
    # Use curl or wget to check health
    if command -v curl &> /dev/null; then
        curl -s -f "$endpoint" > /dev/null 2>&1
        return $?
    elif command -v wget &> /dev/null; then
        wget -q -O - "$endpoint" > /dev/null 2>&1
        return $?
    else
        # Can't check, assume healthy if process is running
        is_agent_running "$agent"
        return $?
    fi
}

# Function to start agents with dependencies
start_agents_ordered() {
    print_message "$BLUE" "🤖 Starting agents in dependency order..."
    
    local started=()
    local to_start=(${!AGENTS[@]})
    local max_iterations=10
    local iteration=0
    
    while [ ${#to_start[@]} -gt 0 ] && [ $iteration -lt $max_iterations ]; do
        local new_to_start=()
        
        for agent in "${to_start[@]}"; do
            local deps="${AGENT_DEPS[$agent]}"
            local can_start=true
            
            # Check if all dependencies are started
            if [ -n "$deps" ]; then
                for dep in $deps; do
                    if [[ ! " ${started[@]} " =~ " ${dep} " ]]; then
                        can_start=false
                        break
                    fi
                done
            fi
            
            if [ "$can_start" = true ]; then
                if start_agent "$agent"; then
                    started+=("$agent")
                else
                    print_message "$RED" "   ❌ Failed to start $agent"
                fi
            else
                new_to_start+=("$agent")
            fi
        done
        
        to_start=("${new_to_start[@]}")
        iteration=$((iteration + 1))
    done
    
    if [ ${#to_start[@]} -gt 0 ]; then
        print_message "$RED" "❌ Could not start agents due to dependency issues:"
        for agent in "${to_start[@]}"; do
            echo "   - $agent"
        done
        return 1
    fi
    
    print_message "$GREEN" "✅ All agents started successfully"
    return 0
}

# Function to stop all agents
stop_all_agents() {
    print_message "$BLUE" "🛑 Stopping all agents..."
    
    for agent in "${!AGENTS[@]}"; do
        stop_agent "$agent"
    done
    
    print_message "$GREEN" "✅ All agents stopped"
}

# Function to show agent status
show_status() {
    print_message "$BLUE" "📊 Agent Status:"
    echo "=================================="
    
    for agent in "${!AGENTS[@]}"; do
        if is_agent_running "$agent"; then
            local pid=$(cat "$PID_DIR/${agent}.pid")
            local health_status="❓ Unknown"
            
            if check_agent_health "$agent"; then
                health_status="✅ Healthy"
            else
                health_status="⚠️  Unhealthy"
            fi
            
            print_message "$GREEN" "   $agent: Running (PID: $pid) - $health_status"
        else
            print_message "$RED" "   $agent: Stopped"
        fi
    done
    
    echo ""
    print_message "$BLUE" "📝 Log files:"
    echo "   $LOG_DIR/<agent>/output.log"
    echo "   $LOG_DIR/<agent>/error.log"
}

# Function to tail logs
tail_logs() {
    local agent=$1
    
    if [ -z "$agent" ]; then
        # Tail all agent logs
        print_message "$BLUE" "📜 Tailing all agent logs..."
        tail -f "$LOG_DIR"/*/output.log "$LOG_DIR"/*/error.log
    else
        # Tail specific agent logs
        if [ -d "$LOG_DIR/$agent" ]; then
            print_message "$BLUE" "📜 Tailing $agent logs..."
            tail -f "$LOG_DIR/$agent/output.log" "$LOG_DIR/$agent/error.log"
        else
            print_message "$RED" "❌ Agent '$agent' not found"
        fi
    fi
}

# Main execution
main() {
    print_message "$BLUE" "🤖 Trading Agent Launcher v1.0"
    echo "=================================="
    
    # Setup
    setup_directories
    check_python
    
    # Source environment variables
    if [ -f "$ENV_FILE" ]; then
        source "$ENV_FILE"
    fi
    
    # Parse command
    case "${1:-}" in
        start)
            install_dependencies
            start_agents_ordered
            show_status
            ;;
        stop)
            stop_all_agents
            ;;
        restart)
            stop_all_agents
            sleep 2
            install_dependencies
            start_agents_ordered
            show_status
            ;;
        status)
            show_status
            ;;
        logs)
            tail_logs "${2:-}"
            ;;
        install)
            install_dependencies
            ;;
        *)
            print_message "$YELLOW" "Usage: $0 {start|stop|restart|status|logs [agent]|install}"
            echo ""
            echo "Commands:"
            echo "   start    - Start all agents"
            echo "   stop     - Stop all agents"
            echo "   restart  - Restart all agents"
            echo "   status   - Show agent status"
            echo "   logs     - Tail agent logs (optionally specify agent)"
            echo "   install  - Install Python dependencies"
            echo ""
            echo "Available agents:"
            for agent in "${!AGENTS[@]}"; do
                echo "   - $agent"
            done
            exit 1
            ;;
    esac
}

# Run main function
main "$@"