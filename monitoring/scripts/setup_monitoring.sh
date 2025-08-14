#!/bin/bash

# TMT Trading System Monitoring Setup Script
# Deploys and configures production monitoring stack

set -euo pipefail

# Configuration
MONITORING_DIR="/opt/tmt/monitoring"
BACKUP_DIR="/opt/tmt/backups/monitoring"
LOG_FILE="/var/log/tmt-monitoring-setup.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    log "ERROR: $1"
    exit 1
}

# Success logging
success() {
    echo -e "${GREEN}✓ $1${NC}"
    log "SUCCESS: $1"
}

# Warning logging
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    log "WARNING: $1"
}

# Info logging
info() {
    echo -e "${BLUE}ℹ $1${NC}"
    log "INFO: $1"
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -ne 0 ]]; then
        error_exit "This script must be run as root or with sudo"
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed. Please install Docker first."
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error_exit "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Check available disk space (minimum 10GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 10485760 ]]; then  # 10GB in KB
        error_exit "Insufficient disk space. Minimum 10GB required."
    fi
    
    success "Prerequisites check passed"
}

# Create directory structure
create_directories() {
    info "Creating directory structure..."
    
    mkdir -p "$MONITORING_DIR"/{prometheus,grafana,alertmanager,loki,promtail,blackbox}
    mkdir -p "$BACKUP_DIR"
    mkdir -p /var/lib/tmt/{prometheus,grafana,alertmanager,loki}
    
    # Set proper permissions
    chown -R 472:472 /var/lib/tmt/grafana  # Grafana user
    chown -R 65534:65534 /var/lib/tmt/prometheus  # Nobody user
    chown -R 65534:65534 /var/lib/tmt/alertmanager  # Nobody user
    chown -R 10001:10001 /var/lib/tmt/loki  # Loki user
    
    success "Directory structure created"
}

# Setup SSL certificates
setup_ssl() {
    info "Setting up SSL certificates..."
    
    SSL_DIR="$MONITORING_DIR/ssl"
    mkdir -p "$SSL_DIR"
    
    # Generate self-signed certificates for development
    # In production, replace with proper certificates
    if [[ ! -f "$SSL_DIR/tmt-monitoring.crt" ]]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$SSL_DIR/tmt-monitoring.key" \
            -out "$SSL_DIR/tmt-monitoring.crt" \
            -subj "/C=US/ST=State/L=City/O=TMT/CN=tmt-monitoring.local"
        
        success "SSL certificates generated"
    else
        info "SSL certificates already exist"
    fi
}

# Configure Prometheus
configure_prometheus() {
    info "Configuring Prometheus..."
    
    # Copy configuration files
    cp prometheus/trading_metrics.yml "$MONITORING_DIR/prometheus/prometheus.yml"
    cp prometheus/alert_rules.yml "$MONITORING_DIR/prometheus/"
    
    # Validate configuration
    docker run --rm -v "$MONITORING_DIR/prometheus:/etc/prometheus" \
        prom/prometheus:v2.45.0 \
        promtool check config /etc/prometheus/prometheus.yml
    
    success "Prometheus configuration validated"
}

# Configure Grafana
configure_grafana() {
    info "Configuring Grafana..."
    
    # Create provisioning directories
    mkdir -p "$MONITORING_DIR/grafana/provisioning"/{dashboards,datasources,notifiers}
    
    # Copy dashboard
    cp grafana/trading_dashboard.json "$MONITORING_DIR/grafana/dashboards/"
    
    # Create datasource configuration
    cat > "$MONITORING_DIR/grafana/provisioning/datasources/prometheus.yml" << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true
EOF

    # Create dashboard provisioning
    cat > "$MONITORING_DIR/grafana/provisioning/dashboards/trading.yml" << EOF
apiVersion: 1

providers:
  - name: 'TMT Trading Dashboards'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

    success "Grafana configuration complete"
}

# Configure AlertManager
configure_alertmanager() {
    info "Configuring AlertManager..."
    
    cp alertmanager/config.yml "$MONITORING_DIR/alertmanager/"
    
    # Validate configuration
    docker run --rm -v "$MONITORING_DIR/alertmanager:/etc/alertmanager" \
        prom/alertmanager:v0.26.0 \
        amtool check-config /etc/alertmanager/config.yml
    
    success "AlertManager configuration validated"
}

# Setup log rotation
setup_log_rotation() {
    info "Setting up log rotation..."
    
    cat > /etc/logrotate.d/tmt-monitoring << EOF
/var/log/tmt-monitoring*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        docker kill -s HUP tmt-prometheus tmt-grafana tmt-alertmanager 2>/dev/null || true
    endscript
}
EOF

    success "Log rotation configured"
}

# Create systemd service
create_systemd_service() {
    info "Creating systemd service..."
    
    cat > /etc/systemd/system/tmt-monitoring.service << EOF
[Unit]
Description=TMT Trading System Monitoring Stack
Requires=docker.service
After=docker.service
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$MONITORING_DIR
ExecStart=/usr/bin/docker-compose -f docker-compose.monitoring.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.monitoring.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable tmt-monitoring.service
    
    success "Systemd service created and enabled"
}

# Setup monitoring health checks
setup_health_checks() {
    info "Setting up health checks..."
    
    # Create health check script
    cat > "$MONITORING_DIR/scripts/health_check.sh" << 'EOF'
#!/bin/bash

# TMT Monitoring Health Check Script

SERVICES=("prometheus" "grafana" "alertmanager" "loki")
FAILED_SERVICES=()

for service in "${SERVICES[@]}"; do
    if ! docker ps | grep -q "tmt-$service"; then
        FAILED_SERVICES+=("$service")
    fi
done

if [[ ${#FAILED_SERVICES[@]} -eq 0 ]]; then
    echo "All monitoring services are running"
    exit 0
else
    echo "Failed services: ${FAILED_SERVICES[*]}"
    exit 1
fi
EOF

    chmod +x "$MONITORING_DIR/scripts/health_check.sh"
    
    # Add to crontab for automated checks
    (crontab -l 2>/dev/null; echo "*/5 * * * * $MONITORING_DIR/scripts/health_check.sh >> /var/log/tmt-monitoring-health.log 2>&1") | crontab -
    
    success "Health checks configured"
}

# Setup backup automation
setup_backup() {
    info "Setting up backup automation..."
    
    # Create backup script
    cat > "$MONITORING_DIR/scripts/backup.sh" << EOF
#!/bin/bash

# TMT Monitoring Backup Script

BACKUP_DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup_\$BACKUP_DATE"

mkdir -p "\$BACKUP_PATH"

# Backup Grafana data
docker exec tmt-grafana grafana-cli admin export-dashboard > "\$BACKUP_PATH/grafana_dashboards.json"

# Backup Prometheus data
docker exec tmt-prometheus tar czf - /prometheus | cat > "\$BACKUP_PATH/prometheus_data.tar.gz"

# Backup configurations
cp -r "$MONITORING_DIR"/{prometheus,grafana,alertmanager} "\$BACKUP_PATH/"

# Clean up old backups (keep last 7 days)
find "$BACKUP_DIR" -name "backup_*" -type d -mtime +7 -exec rm -rf {} +

echo "Backup completed: \$BACKUP_PATH"
EOF

    chmod +x "$MONITORING_DIR/scripts/backup.sh"
    
    # Schedule daily backups
    (crontab -l 2>/dev/null; echo "0 2 * * * $MONITORING_DIR/scripts/backup.sh >> /var/log/tmt-monitoring-backup.log 2>&1") | crontab -
    
    success "Backup automation configured"
}

# Deploy monitoring stack
deploy_stack() {
    info "Deploying monitoring stack..."
    
    cd "$MONITORING_DIR"
    
    # Copy docker-compose file
    cp "$(dirname "$0")/docker-compose.monitoring.yml" .
    
    # Start services
    docker-compose -f docker-compose.monitoring.yml up -d
    
    # Wait for services to be ready
    sleep 30
    
    # Verify services are running
    if docker-compose -f docker-compose.monitoring.yml ps | grep -q "Up"; then
        success "Monitoring stack deployed successfully"
    else
        error_exit "Failed to deploy monitoring stack"
    fi
}

# Test monitoring setup
test_monitoring() {
    info "Testing monitoring setup..."
    
    # Test Prometheus
    if curl -s "http://localhost:9090/-/healthy" | grep -q "Prometheus is Healthy"; then
        success "Prometheus is healthy"
    else
        warning "Prometheus health check failed"
    fi
    
    # Test Grafana
    if curl -s "http://localhost:3000/api/health" | grep -q "ok"; then
        success "Grafana is healthy"
    else
        warning "Grafana health check failed"
    fi
    
    # Test AlertManager
    if curl -s "http://localhost:9093/-/healthy" | grep -q "OK"; then
        success "AlertManager is healthy"
    else
        warning "AlertManager health check failed"
    fi
    
    success "Monitoring setup testing complete"
}

# Generate summary report
generate_summary() {
    info "Generating deployment summary..."
    
    cat << EOF

========================================
TMT Monitoring Stack Deployment Summary
========================================

✓ Monitoring Services:
  - Prometheus: http://localhost:9090
  - Grafana: http://localhost:3000 (admin/secure_admin_password)
  - AlertManager: http://localhost:9093
  - Loki: http://localhost:3100

✓ Configuration Files:
  - Prometheus: $MONITORING_DIR/prometheus/
  - Grafana: $MONITORING_DIR/grafana/
  - AlertManager: $MONITORING_DIR/alertmanager/

✓ Automated Tasks:
  - Health checks: Every 5 minutes
  - Backups: Daily at 2:00 AM
  - Log rotation: Daily

✓ Key Features:
  - <100ms latency monitoring
  - 99.5% uptime SLA tracking
  - Circuit breaker monitoring
  - Business metrics dashboard
  - Multi-channel alerting

📋 Next Steps:
  1. Configure SMTP credentials in AlertManager
  2. Set up Slack/PagerDuty integrations
  3. Customize alert thresholds
  4. Add SSL certificates for production
  5. Configure backup retention policy

📖 Documentation: $MONITORING_DIR/README.md

========================================
EOF

    success "Deployment completed successfully!"
}

# Main execution
main() {
    log "Starting TMT monitoring setup..."
    
    check_prerequisites
    create_directories
    setup_ssl
    configure_prometheus
    configure_grafana
    configure_alertmanager
    setup_log_rotation
    create_systemd_service
    setup_health_checks
    setup_backup
    deploy_stack
    test_monitoring
    generate_summary
    
    log "TMT monitoring setup completed"
}

# Execute main function
main "$@"