#!/bin/bash
set -e

# Staging Deployment Script
# Deploys the trading system to the staging environment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "${SCRIPT_DIR}")")"
DEPLOYMENT_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
GIT_COMMIT_SHORT=$(git rev-parse --short HEAD)
IMAGE_TAG="${IMAGE_TAG:-${GIT_COMMIT_SHORT}}"

# Staging environment configuration
ENVIRONMENT="staging"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-adaptive-trading-system}"
GKE_CLUSTER="${GKE_CLUSTER:-trading-staging}"
GKE_ZONE="${GKE_ZONE:-us-central1-a}"
NAMESPACE="staging"
DOMAIN="${STAGING_DOMAIN:-staging.trading-system.com}"
CONTAINER_REGISTRY="${CONTAINER_REGISTRY:-gcr.io}"

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

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check required tools
    local required_tools=("gcloud" "kubectl" "helm" "docker")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "${tool}" >/dev/null 2>&1; then
            missing_tools+=("${tool}")
        else
            print_status "${tool} is available"
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools:"
        for tool in "${missing_tools[@]}"; do
            echo "  - ${tool}"
        done
        exit 1
    fi
    
    # Check environment variables
    local required_vars=("GCP_PROJECT_ID")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("${var}")
        else
            print_status "${var} is set"
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - ${var}"
        done
        print_info "Please set these variables or use the CI/CD pipeline"
        exit 1
    fi
    
    # Check if we're authenticated with GCP
    if ! gcloud auth list --filter="status:ACTIVE" --format="value(account)" | grep -q .; then
        print_error "Not authenticated with Google Cloud"
        print_info "Run: gcloud auth login"
        exit 1
    fi
    
    print_status "Prerequisites check completed"
}

# Function to setup GKE cluster access
setup_cluster_access() {
    print_header "Setting up Cluster Access"
    
    print_info "Configuring kubectl for cluster: ${GKE_CLUSTER}"
    
    if gcloud container clusters get-credentials "${GKE_CLUSTER}" \
        --zone "${GKE_ZONE}" \
        --project "${GCP_PROJECT_ID}"; then
        print_status "Cluster credentials configured"
    else
        print_error "Failed to get cluster credentials"
        exit 1
    fi
    
    # Verify cluster access
    if kubectl cluster-info >/dev/null 2>&1; then
        print_status "Cluster access verified"
    else
        print_error "Cannot access Kubernetes cluster"
        exit 1
    fi
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "${NAMESPACE}" >/dev/null 2>&1; then
        print_info "Creating namespace: ${NAMESPACE}"
        kubectl create namespace "${NAMESPACE}"
        print_status "Namespace created"
    else
        print_status "Namespace ${NAMESPACE} exists"
    fi
}

# Function to setup Helm repositories
setup_helm() {
    print_header "Setting up Helm"
    
    print_info "Adding Helm repositories..."
    
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
    
    print_info "Updating Helm repositories..."
    helm repo update
    
    print_status "Helm repositories configured"
}

# Function to deploy infrastructure services
deploy_infrastructure() {
    print_header "Deploying Infrastructure Services"
    
    # Deploy PostgreSQL with TimescaleDB
    print_info "Deploying PostgreSQL with TimescaleDB..."
    helm upgrade --install postgresql bitnami/postgresql \
        --set auth.postgresPassword="${POSTGRES_PASSWORD:-staging_password_123}" \
        --set auth.database=trading_system \
        --set primary.persistence.size=20Gi \
        --set primary.resources.limits.cpu=1000m \
        --set primary.resources.limits.memory=2Gi \
        --set primary.resources.requests.cpu=500m \
        --set primary.resources.requests.memory=1Gi \
        --set metrics.enabled=true \
        --set metrics.serviceMonitor.enabled=true \
        --namespace "${NAMESPACE}" \
        --wait --timeout=10m
    
    print_status "PostgreSQL deployed"
    
    # Deploy Redis
    print_info "Deploying Redis..."
    helm upgrade --install redis bitnami/redis \
        --set auth.password="${REDIS_PASSWORD:-staging_redis_123}" \
        --set master.persistence.size=8Gi \
        --set master.resources.limits.cpu=500m \
        --set master.resources.limits.memory=1Gi \
        --set master.resources.requests.cpu=250m \
        --set master.resources.requests.memory=512Mi \
        --set metrics.enabled=true \
        --set metrics.serviceMonitor.enabled=true \
        --namespace "${NAMESPACE}" \
        --wait --timeout=5m
    
    print_status "Redis deployed"
    
    # Deploy Kafka
    print_info "Deploying Kafka..."
    helm upgrade --install kafka bitnami/kafka \
        --set persistence.size=10Gi \
        --set resources.limits.cpu=1000m \
        --set resources.limits.memory=2Gi \
        --set resources.requests.cpu=500m \
        --set resources.requests.memory=1Gi \
        --set metrics.jmx.enabled=true \
        --set metrics.kafka.enabled=true \
        --set metrics.serviceMonitor.enabled=true \
        --namespace "${NAMESPACE}" \
        --wait --timeout=10m
    
    print_status "Kafka deployed"
}

# Function to deploy monitoring stack
deploy_monitoring() {
    print_header "Deploying Monitoring Stack"
    
    # Create monitoring namespace
    if ! kubectl get namespace monitoring >/dev/null 2>&1; then
        kubectl create namespace monitoring
    fi
    
    # Deploy Prometheus and Grafana
    print_info "Deploying Prometheus and Grafana..."
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --set grafana.adminPassword="${GRAFANA_PASSWORD:-staging_grafana_123}" \
        --set grafana.service.type=LoadBalancer \
        --set prometheus.prometheusSpec.retention=7d \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=20Gi \
        --set prometheus.prometheusSpec.resources.limits.cpu=1000m \
        --set prometheus.prometheusSpec.resources.limits.memory=2Gi \
        --set prometheus.prometheusSpec.resources.requests.cpu=500m \
        --set prometheus.prometheusSpec.resources.requests.memory=1Gi \
        --namespace monitoring \
        --wait --timeout=10m
    
    print_status "Monitoring stack deployed"
}

# Function to create application secrets
create_secrets() {
    print_header "Creating Application Secrets"
    
    # Delete existing secret if it exists
    kubectl delete secret app-secrets -n "${NAMESPACE}" 2>/dev/null || true
    
    # Create new secret
    kubectl create secret generic app-secrets \
        --from-literal=DATABASE_URL="postgresql://postgres:${POSTGRES_PASSWORD:-staging_password_123}@postgresql:5432/trading_system" \
        --from-literal=REDIS_URL="redis://:${REDIS_PASSWORD:-staging_redis_123}@redis-master:6379" \
        --from-literal=KAFKA_BROKERS="kafka:9092" \
        --from-literal=JWT_SECRET="${JWT_SECRET:-staging_jwt_secret_key_change_in_production}" \
        --from-literal=ENCRYPTION_KEY="${ENCRYPTION_KEY:-staging_encryption_key_32_chars}" \
        --from-literal=VAULT_TOKEN="${VAULT_TOKEN:-staging_vault_token}" \
        --from-literal=NEXTAUTH_SECRET="${NEXTAUTH_SECRET:-staging_nextauth_secret_32_chars_min}" \
        --namespace "${NAMESPACE}"
    
    print_status "Application secrets created"
}

# Function to deploy application services
deploy_application() {
    print_header "Deploying Application Services"
    
    # Check if Helm chart exists
    local helm_chart_path="${PROJECT_ROOT}/infrastructure/helm/trading-system"
    if [ ! -d "${helm_chart_path}" ]; then
        print_error "Helm chart not found at ${helm_chart_path}"
        print_info "Creating basic deployment manifests..."
        create_basic_manifests
        return 0
    fi
    
    # Update values file with current configuration
    local values_file="${helm_chart_path}/values-${ENVIRONMENT}.yaml"
    if [ ! -f "${values_file}" ]; then
        print_warning "Values file not found: ${values_file}"
        print_info "Creating default values file..."
        create_staging_values_file "${values_file}"
    fi
    
    # Deploy application using Helm
    print_info "Deploying trading system application..."
    helm upgrade --install trading-system "${helm_chart_path}" \
        --values "${values_file}" \
        --set image.tag="${IMAGE_TAG}" \
        --set global.containerRegistry="${CONTAINER_REGISTRY}/${GCP_PROJECT_ID}" \
        --set global.environment="${ENVIRONMENT}" \
        --set ingress.hosts[0].host="${DOMAIN}" \
        --namespace "${NAMESPACE}" \
        --wait --timeout=10m
    
    print_status "Application deployed with Helm"
}

# Function to create basic Kubernetes manifests (fallback)
create_basic_manifests() {
    print_info "Creating basic Kubernetes manifests..."
    
    # Dashboard deployment
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-dashboard
  namespace: ${NAMESPACE}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: trading-dashboard
  template:
    metadata:
      labels:
        app: trading-dashboard
    spec:
      containers:
      - name: dashboard
        image: ${CONTAINER_REGISTRY}/${GCP_PROJECT_ID}/trading-dashboard:${IMAGE_TAG}
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: NEXT_PUBLIC_API_URL
          value: "https://${DOMAIN}/api"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: DATABASE_URL
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: trading-dashboard
  namespace: ${NAMESPACE}
spec:
  selector:
    app: trading-dashboard
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
EOF
    
    print_status "Basic manifests created"
}

# Function to create staging values file
create_staging_values_file() {
    local values_file=$1
    
    mkdir -p "$(dirname "${values_file}")"
    
    cat > "${values_file}" << EOF
# Staging environment values for Adaptive Trading System

global:
  environment: staging
  containerRegistry: ${CONTAINER_REGISTRY}/${GCP_PROJECT_ID}
  domain: ${DOMAIN}

image:
  tag: ${IMAGE_TAG}
  pullPolicy: Always

dashboard:
  replicaCount: 2
  image:
    repository: trading-dashboard
  service:
    type: LoadBalancer
    port: 80
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 500m
      memory: 1Gi

agents:
  replicaCount: 1
  image:
    repository: trading-agents
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 1000m
      memory: 2Gi

executionEngine:
  replicaCount: 2
  image:
    repository: execution-engine
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 500m
      memory: 1Gi

ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: ${DOMAIN}
      paths:
        - path: /
          pathType: Prefix
          service: trading-dashboard
        - path: /api
          pathType: Prefix
          service: trading-agents
  tls:
    - secretName: trading-system-tls
      hosts:
        - ${DOMAIN}

secrets:
  name: app-secrets

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
EOF
    
    print_info "Created staging values file: ${values_file}"
}

# Function to wait for deployment rollout
wait_for_rollout() {
    print_header "Waiting for Deployment Rollout"
    
    local deployments=("trading-dashboard")
    
    for deployment in "${deployments[@]}"; do
        print_info "Waiting for ${deployment} rollout..."
        
        if kubectl rollout status deployment/"${deployment}" -n "${NAMESPACE}" --timeout=600s; then
            print_status "${deployment} rolled out successfully"
        else
            print_error "${deployment} rollout failed"
            kubectl describe deployment/"${deployment}" -n "${NAMESPACE}"
            return 1
        fi
    done
}

# Function to run smoke tests
run_smoke_tests() {
    print_header "Running Smoke Tests"
    
    print_info "Getting service endpoints..."
    
    # Wait for load balancer to get external IP
    local max_attempts=30
    local attempt=1
    local dashboard_ip=""
    
    while [ ${attempt} -le ${max_attempts} ]; do
        dashboard_ip=$(kubectl get service trading-dashboard -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
        
        if [ -n "${dashboard_ip}" ] && [ "${dashboard_ip}" != "null" ]; then
            break
        fi
        
        print_info "Waiting for load balancer IP... (${attempt}/${max_attempts})"
        sleep 30
        ((attempt++))
    done
    
    if [ -z "${dashboard_ip}" ] || [ "${dashboard_ip}" == "null" ]; then
        print_warning "Load balancer IP not available, trying service port-forward..."
        kubectl port-forward service/trading-dashboard 8080:80 -n "${NAMESPACE}" &
        local port_forward_pid=$!
        sleep 10
        dashboard_url="http://localhost:8080"
    else
        dashboard_url="http://${dashboard_ip}"
        print_status "Dashboard URL: ${dashboard_url}"
    fi
    
    # Test health endpoints
    print_info "Testing health endpoints..."
    
    local max_health_attempts=10
    local health_attempt=1
    
    while [ ${health_attempt} -le ${max_health_attempts} ]; do
        if curl -f --max-time 10 "${dashboard_url}/api/health" >/dev/null 2>&1; then
            print_status "Dashboard health check passed"
            break
        fi
        
        if [ ${health_attempt} -eq ${max_health_attempts} ]; then
            print_error "Dashboard health check failed after ${max_health_attempts} attempts"
            
            # Debug information
            print_info "Debug information:"
            kubectl get pods -n "${NAMESPACE}"
            kubectl describe service trading-dashboard -n "${NAMESPACE}"
            
            return 1
        fi
        
        print_info "Health check attempt ${health_attempt}/${max_health_attempts}..."
        sleep 30
        ((health_attempt++))
    done
    
    # Cleanup port-forward if used
    if [ -n "${port_forward_pid}" ]; then
        kill ${port_forward_pid} 2>/dev/null || true
    fi
    
    print_status "Smoke tests completed successfully"
}

# Function to update deployment status
update_deployment_status() {
    print_header "Updating Deployment Status"
    
    local status_file="${PROJECT_ROOT}/deployment-status-${ENVIRONMENT}.json"
    
    cat > "${status_file}" << EOF
{
  "environment": "${ENVIRONMENT}",
  "deployment_timestamp": "${DEPLOYMENT_TIMESTAMP}",
  "git_commit": "${GIT_COMMIT_SHORT}",
  "image_tag": "${IMAGE_TAG}",
  "cluster": "${GKE_CLUSTER}",
  "namespace": "${NAMESPACE}",
  "domain": "${DOMAIN}",
  "status": "deployed",
  "services": {
    "dashboard": "${CONTAINER_REGISTRY}/${GCP_PROJECT_ID}/trading-dashboard:${IMAGE_TAG}",
    "execution-engine": "${CONTAINER_REGISTRY}/${GCP_PROJECT_ID}/trading-execution-engine:${IMAGE_TAG}"
  }
}
EOF
    
    print_status "Deployment status updated: ${status_file}"
}

# Function to display deployment summary
display_summary() {
    print_header "Deployment Summary"
    
    print_status "Deployment completed successfully!"
    echo
    print_info "Environment Details:"
    print_info "  Environment: ${ENVIRONMENT}"
    print_info "  Cluster: ${GKE_CLUSTER}"
    print_info "  Namespace: ${NAMESPACE}"
    print_info "  Image Tag: ${IMAGE_TAG}"
    print_info "  Domain: ${DOMAIN}"
    echo
    print_info "Access URLs:"
    local dashboard_ip=$(kubectl get service trading-dashboard -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    print_info "  Dashboard: http://${dashboard_ip} (or https://${DOMAIN})"
    print_info "  Grafana: Check monitoring namespace for access"
    echo
    print_info "Useful Commands:"
    print_info "  Watch pods: kubectl get pods -n ${NAMESPACE} -w"
    print_info "  View logs: kubectl logs -f deployment/trading-dashboard -n ${NAMESPACE}"
    print_info "  Port forward: kubectl port-forward service/trading-dashboard 8080:80 -n ${NAMESPACE}"
}

# Main execution function
main() {
    print_header "Staging Deployment - Adaptive Trading System"
    
    print_info "Deployment configuration:"
    print_info "  Environment: ${ENVIRONMENT}"
    print_info "  GCP Project: ${GCP_PROJECT_ID}"
    print_info "  Cluster: ${GKE_CLUSTER}"
    print_info "  Zone: ${GKE_ZONE}"
    print_info "  Namespace: ${NAMESPACE}"
    print_info "  Image Tag: ${IMAGE_TAG}"
    print_info "  Domain: ${DOMAIN}"
    print_info "  Registry: ${CONTAINER_REGISTRY}"
    
    # Change to project root
    cd "${PROJECT_ROOT}"
    
    # Execute deployment steps
    check_prerequisites
    setup_cluster_access
    setup_helm
    deploy_infrastructure
    deploy_monitoring
    create_secrets
    deploy_application
    wait_for_rollout
    run_smoke_tests
    update_deployment_status
    display_summary
    
    print_header "Staging Deployment Completed Successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --image-tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --project-id)
            GCP_PROJECT_ID="$2"
            shift 2
            ;;
        --cluster)
            GKE_CLUSTER="$2"
            shift 2
            ;;
        --zone)
            GKE_ZONE="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --skip-infrastructure)
            SKIP_INFRASTRUCTURE=true
            shift
            ;;
        --skip-monitoring)
            SKIP_MONITORING=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --image-tag TAG        Docker image tag to deploy"
            echo "  --project-id ID        GCP project ID"
            echo "  --cluster CLUSTER      GKE cluster name"
            echo "  --zone ZONE           GCP zone"
            echo "  --domain DOMAIN       Application domain"
            echo "  --skip-infrastructure  Skip infrastructure deployment"
            echo "  --skip-monitoring     Skip monitoring stack deployment"
            echo "  --help                Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"