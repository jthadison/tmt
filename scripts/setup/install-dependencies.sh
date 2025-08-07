#!/bin/bash
set -e

echo "🚀 Setting up Adaptive Trading System development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check for required tools
echo "📋 Checking system requirements..."

# Check Python 3.11.8
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    if [[ "$PYTHON_VERSION" == "3.11."* ]]; then
        print_status "Python $PYTHON_VERSION found"
    else
        print_warning "Python 3.11.x recommended, found $PYTHON_VERSION"
    fi
else
    print_error "Python 3.11.8+ required. Please install from https://python.org"
    exit 1
fi

# Check Node.js 20.11.0
if command_exists node; then
    NODE_VERSION=$(node --version | sed 's/v//')
    if [[ "$NODE_VERSION" == "20."* ]]; then
        print_status "Node.js $NODE_VERSION found"
    else
        print_warning "Node.js 20.x LTS recommended, found $NODE_VERSION"
    fi
else
    print_error "Node.js 20.11.0+ required. Please install from https://nodejs.org"
    exit 1
fi

# Check Rust 1.75.0
if command_exists rustc; then
    RUST_VERSION=$(rustc --version | cut -d' ' -f2)
    print_status "Rust $RUST_VERSION found"
else
    print_error "Rust 1.75.0+ required. Install from https://rustup.rs/"
    exit 1
fi

# Check Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | sed 's/,//')
    print_status "Docker $DOCKER_VERSION found"
else
    print_error "Docker 25.0.3+ required. Install from https://docker.com"
    exit 1
fi

# Check Docker Compose
if command_exists docker-compose; then
    print_status "Docker Compose found"
elif docker compose version >/dev/null 2>&1; then
    print_status "Docker Compose (plugin) found"
else
    print_error "Docker Compose required"
    exit 1
fi

echo ""
echo "📦 Installing dependencies..."

# Install Python dependencies
echo "Installing Python dependencies..."
if [ -f "pyproject.toml" ]; then
    pip3 install -e .
    print_status "Python dependencies installed"
fi

# Install Node.js dependencies for dashboard
echo "Installing Node.js dependencies..."
cd dashboard
if [ -f "package.json" ]; then
    npm ci
    print_status "Dashboard dependencies installed"
fi
cd ..

# Install Rust dependencies for execution engine
echo "Installing Rust dependencies..."
cd execution-engine
cargo build
print_status "Execution engine dependencies installed"
cd ..

# Install pre-commit hooks if available
if [ -f ".pre-commit-config.yaml" ]; then
    echo "Setting up pre-commit hooks..."
    if command_exists pre-commit; then
        pre-commit install
        print_status "Pre-commit hooks installed"
    else
        print_warning "pre-commit not found. Install with: pip install pre-commit"
    fi
fi

echo ""
echo "🔧 Setting up environment files..."

# Create .env.example if it doesn't exist
if [ ! -f ".env.example" ]; then
    cat > .env.example << EOF
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/trading_system
REDIS_URL=redis://localhost:6379

# Kafka Configuration
KAFKA_BROKERS=localhost:9092

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0

# Security
SECRET_KEY=your-secret-key-here
VAULT_URL=http://localhost:8200
VAULT_TOKEN=your-vault-token

# Monitoring
PROMETHEUS_URL=http://localhost:9090
GRAFANA_URL=http://localhost:3001

# Development
DEBUG=true
LOG_LEVEL=INFO
EOF
    print_status "Environment template created (.env.example)"
fi

echo ""
echo "🏥 Health checks..."

# Verify installations
python3 -c "import sys; print(f'Python {sys.version}')" 2>/dev/null && print_status "Python working" || print_error "Python issue"
node -e "console.log(\`Node.js \${process.version}\`)" 2>/dev/null && print_status "Node.js working" || print_error "Node.js issue"
rustc --version >/dev/null 2>&1 && print_status "Rust working" || print_error "Rust issue"
docker --version >/dev/null 2>&1 && print_status "Docker working" || print_error "Docker issue"

echo ""
echo "✨ Setup complete! Next steps:"
echo "1. Copy .env.example to .env and configure your settings"
echo "2. Start the development environment: docker-compose up -d"
echo "3. Run health checks: ./scripts/setup/system-health-check.sh"
echo "4. Access the dashboard at http://localhost:3000"
echo ""
echo "For more information, see README.md"