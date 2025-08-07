#!/bin/bash
set -e

# Build All Services Script
# Builds Docker images for all services with proper tagging

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "${SCRIPT_DIR}")")"
BUILD_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
GIT_COMMIT_SHORT=$(git rev-parse --short HEAD)
IMAGE_TAG="${GIT_COMMIT_SHORT}"
REGISTRY="${CONTAINER_REGISTRY:-gcr.io}"
PROJECT_ID="${GCP_PROJECT_ID:-adaptive-trading-system}"

# Default to local build if not in CI
if [ -z "${CI}" ]; then
    REGISTRY="local"
    PROJECT_ID="trading"
fi

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

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_status "Docker is running"
}

# Function to check if required files exist
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    local missing_files=()
    
    # Check Dockerfiles
    if [ ! -f "${PROJECT_ROOT}/src/dashboard/Dockerfile" ] && [ ! -f "${PROJECT_ROOT}/src/dashboard/Dockerfile.dev" ]; then
        missing_files+=("src/dashboard/Dockerfile or src/dashboard/Dockerfile.dev")
    fi
    
    if [ ! -f "${PROJECT_ROOT}/src/execution-engine/Dockerfile" ]; then
        missing_files+=("src/execution-engine/Dockerfile")
    fi
    
    # Check if we're in a git repository
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        print_warning "Not in a git repository. Using timestamp for image tag."
        IMAGE_TAG="${BUILD_TIMESTAMP}"
    fi
    
    if [ ${#missing_files[@]} -ne 0 ]; then
        print_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            echo "  - ${file}"
        done
        exit 1
    fi
    
    print_status "Prerequisites check completed"
}

# Function to build a single service
build_service() {
    local service_name=$1
    local context_path=$2
    local dockerfile_path=$3
    
    print_header "Building ${service_name}"
    
    # Determine full image name
    local image_name
    if [ "${REGISTRY}" == "local" ]; then
        image_name="trading-${service_name}:${IMAGE_TAG}"
    else
        image_name="${REGISTRY}/${PROJECT_ID}/trading-${service_name}:${IMAGE_TAG}"
    fi
    
    print_info "Image: ${image_name}"
    print_info "Context: ${context_path}"
    print_info "Dockerfile: ${dockerfile_path}"
    
    # Build arguments
    local build_args=(
        "--tag" "${image_name}"
        "--file" "${dockerfile_path}"
        "--build-arg" "BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        "--build-arg" "VCS_REF=${GIT_COMMIT_SHORT}"
        "--build-arg" "VERSION=${IMAGE_TAG}"
    )
    
    # Add cache from previous builds in CI
    if [ -n "${CI}" ]; then
        build_args+=(
            "--cache-from" "${image_name}"
            "--cache-from" "${REGISTRY}/${PROJECT_ID}/trading-${service_name}:latest"
        )
    fi
    
    # Add progress output
    build_args+=("--progress" "plain")
    
    # Build the image
    if docker buildx build "${build_args[@]}" "${context_path}"; then
        print_status "${service_name} built successfully"
        
        # Tag as latest for local builds
        if [ "${REGISTRY}" == "local" ]; then
            docker tag "${image_name}" "trading-${service_name}:latest"
            print_status "Tagged as trading-${service_name}:latest"
        fi
        
        # Get image size
        local image_size=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | grep "${image_name}" | awk '{print $2}')
        print_info "Image size: ${image_size}"
        
        return 0
    else
        print_error "${service_name} build failed"
        return 1
    fi
}

# Function to run security scans on built images
security_scan() {
    if [ -z "${CI}" ]; then
        print_warning "Skipping security scans in local build"
        return 0
    fi
    
    print_header "Running Security Scans"
    
    local services=("dashboard" "execution-engine")
    
    for service in "${services[@]}"; do
        local image_name="${REGISTRY}/${PROJECT_ID}/trading-${service}:${IMAGE_TAG}"
        
        print_info "Scanning ${image_name}..."
        
        # Run Trivy scan
        if command -v trivy >/dev/null 2>&1; then
            trivy image --exit-code 1 --severity HIGH,CRITICAL "${image_name}" || {
                print_warning "Security vulnerabilities found in ${service}"
            }
        else
            print_warning "Trivy not installed, skipping vulnerability scan"
        fi
    done
}

# Function to push images (CI only)
push_images() {
    if [ -z "${CI}" ]; then
        print_info "Local build - skipping image push"
        return 0
    fi
    
    if [ "${REGISTRY}" == "local" ]; then
        print_info "Local registry - skipping image push"
        return 0
    fi
    
    print_header "Pushing Images"
    
    local services=("dashboard" "execution-engine")
    
    for service in "${services[@]}"; do
        local image_name="${REGISTRY}/${PROJECT_ID}/trading-${service}:${IMAGE_TAG}"
        local latest_name="${REGISTRY}/${PROJECT_ID}/trading-${service}:latest"
        
        print_info "Pushing ${image_name}..."
        
        if docker push "${image_name}"; then
            print_status "${service} pushed successfully"
            
            # Push latest tag for main branch
            if [ "${GITHUB_REF}" == "refs/heads/main" ] || [ "${BRANCH}" == "main" ]; then
                docker tag "${image_name}" "${latest_name}"
                docker push "${latest_name}"
                print_status "${service}:latest pushed"
            fi
        else
            print_error "Failed to push ${service}"
            return 1
        fi
    done
}

# Function to generate build manifest
generate_manifest() {
    print_header "Generating Build Manifest"
    
    local manifest_file="${PROJECT_ROOT}/build-manifest.json"
    
    cat > "${manifest_file}" << EOF
{
  "build_timestamp": "${BUILD_TIMESTAMP}",
  "git_commit": "${GIT_COMMIT_SHORT}",
  "image_tag": "${IMAGE_TAG}",
  "registry": "${REGISTRY}",
  "project_id": "${PROJECT_ID}",
  "images": {
    "dashboard": "${REGISTRY}/${PROJECT_ID}/trading-dashboard:${IMAGE_TAG}",
    "execution-engine": "${REGISTRY}/${PROJECT_ID}/trading-execution-engine:${IMAGE_TAG}"
  },
  "build_environment": {
    "ci": "${CI:-false}",
    "runner": "${RUNNER_OS:-local}",
    "node_version": "$(node --version 2>/dev/null || echo 'not_available')",
    "docker_version": "$(docker --version | cut -d' ' -f3 | cut -d',' -f1)"
  }
}
EOF
    
    print_status "Build manifest generated: ${manifest_file}"
}

# Function to cleanup old images (local builds only)
cleanup_old_images() {
    if [ -n "${CI}" ]; then
        return 0
    fi
    
    print_header "Cleaning Up Old Images"
    
    # Remove dangling images
    local dangling_images=$(docker images -f "dangling=true" -q)
    if [ -n "${dangling_images}" ]; then
        docker rmi ${dangling_images} 2>/dev/null || true
        print_status "Removed dangling images"
    fi
    
    # Remove old tagged images (keep last 5)
    local old_images=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | grep "trading-" | tail -n +6 | awk '{print $1}')
    if [ -n "${old_images}" ]; then
        echo "${old_images}" | xargs docker rmi 2>/dev/null || true
        print_status "Removed old images"
    fi
}

# Main execution
main() {
    print_header "Adaptive Trading System - Build All Services"
    
    print_info "Build configuration:"
    print_info "  Registry: ${REGISTRY}"
    print_info "  Project ID: ${PROJECT_ID}"
    print_info "  Image Tag: ${IMAGE_TAG}"
    print_info "  Build Timestamp: ${BUILD_TIMESTAMP}"
    print_info "  CI Mode: ${CI:-false}"
    
    # Change to project root
    cd "${PROJECT_ROOT}"
    
    # Run checks
    check_docker
    check_prerequisites
    
    # Build services
    local build_failed=false
    
    # Build Dashboard
    if [ -f "src/dashboard/Dockerfile" ]; then
        build_service "dashboard" "./dashboard" "./src/dashboard/Dockerfile" || build_failed=true
    elif [ -f "src/dashboard/Dockerfile.dev" ]; then
        build_service "dashboard" "./dashboard" "./src/dashboard/Dockerfile.dev" || build_failed=true
    fi
    
    # Build Execution Engine
    build_service "execution-engine" "./execution-engine" "./src/execution-engine/Dockerfile" || build_failed=true
    
    # Check if any builds failed
    if [ "${build_failed}" = true ]; then
        print_error "One or more builds failed"
        exit 1
    fi
    
    # Run additional steps
    security_scan
    push_images
    generate_manifest
    cleanup_old_images
    
    print_header "Build Completed Successfully"
    print_status "All services built successfully with tag: ${IMAGE_TAG}"
    
    if [ "${REGISTRY}" == "local" ]; then
        print_info "To run locally: docker-compose up -d"
        print_info "To test health: ./scripts/maintenance/system-health-check.sh"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        --no-push)
            NO_PUSH=true
            shift
            ;;
        --no-cleanup)
            NO_CLEANUP=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --tag TAG              Custom image tag (default: git commit short)"
            echo "  --registry REGISTRY    Container registry (default: gcr.io)"
            echo "  --project-id ID        GCP project ID"
            echo "  --no-push              Skip pushing images"
            echo "  --no-cleanup           Skip cleanup of old images"
            echo "  --help                 Show this help message"
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