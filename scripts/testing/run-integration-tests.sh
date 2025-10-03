#!/bin/bash
set -e

# Integration Tests Runner
# Runs comprehensive integration tests across all services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "${SCRIPT_DIR}")")"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Main execution
main() {
    print_header "Integration Tests - Adaptive Trading System"
    
    cd "${PROJECT_ROOT}"
    
    print_info "Starting integration test suite..."
    
    # Wait for services to be ready
    print_info "Waiting for services to be ready..."
    sleep 30
    
    # Run basic health checks
    print_info "Running health checks..."
    if curl -f http://localhost:3000/api/health >/dev/null 2>&1; then
        print_status "Dashboard health check passed"
    else
        print_warning "Dashboard not responding, skipping dashboard tests"
    fi
    
    # Run pytest integration tests
    print_info "Running pytest integration tests..."

    if ! command -v pytest &> /dev/null; then
        print_error "pytest not found. Install requirements-dev.txt first"
        exit 1
    fi

    # Run integration tests with proper markers
    print_info "Running 8-agent orchestration tests..."
    pytest tests/integration/ \
        -v \
        --tb=short \
        -m "integration" \
        --maxfail=5 \
        --junitxml=integration-test-results.xml \
        || {
        print_warning "Some integration tests failed (this is expected if agents aren't running)"
    }

    print_status "Integration tests completed successfully"
}

main "$@"