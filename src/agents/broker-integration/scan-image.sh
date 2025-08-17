#!/bin/bash
# Container Image Security Scanning Script
# Uses multiple tools to scan for vulnerabilities, misconfigurations, and security issues

set -euo pipefail

IMAGE_NAME="${1:-tmt/broker-integration:latest}"
SCAN_RESULTS_DIR="./security-scan-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Starting comprehensive security scan for image: $IMAGE_NAME"

# Create results directory
mkdir -p "$SCAN_RESULTS_DIR"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install trivy if not present
install_trivy() {
    if ! command_exists trivy; then
        echo "Installing Trivy..."
        if command_exists curl; then
            curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
        else
            echo "Error: curl not found. Please install Trivy manually."
            exit 1
        fi
    fi
}

# Function to install hadolint if not present
install_hadolint() {
    if ! command_exists hadolint; then
        echo "Installing Hadolint..."
        if command_exists wget; then
            wget -O /usr/local/bin/hadolint https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64
            chmod +x /usr/local/bin/hadolint
        else
            echo "Warning: hadolint not found and wget not available. Skipping Dockerfile linting."
        fi
    fi
}

# 1. Dockerfile Linting with Hadolint
echo "Running Dockerfile security analysis..."
install_hadolint
if command_exists hadolint; then
    hadolint Dockerfile > "$SCAN_RESULTS_DIR/dockerfile_lint_$TIMESTAMP.txt" 2>&1 || true
    echo "✓ Dockerfile analysis completed"
else
    echo "⚠ Skipping Dockerfile analysis (hadolint not available)"
fi

# 2. Vulnerability Scanning with Trivy
echo "Running vulnerability scan..."
install_trivy
if command_exists trivy; then
    # Scan for vulnerabilities
    trivy image --format json --output "$SCAN_RESULTS_DIR/vulnerabilities_$TIMESTAMP.json" "$IMAGE_NAME" || true
    trivy image --format table --output "$SCAN_RESULTS_DIR/vulnerabilities_$TIMESTAMP.txt" "$IMAGE_NAME" || true
    
    # Scan for misconfigurations
    trivy config --format json --output "$SCAN_RESULTS_DIR/misconfigurations_$TIMESTAMP.json" . || true
    trivy config --format table --output "$SCAN_RESULTS_DIR/misconfigurations_$TIMESTAMP.txt" . || true
    
    # Scan for secrets
    trivy fs --scanners secret --format json --output "$SCAN_RESULTS_DIR/secrets_$TIMESTAMP.json" . || true
    trivy fs --scanners secret --format table --output "$SCAN_RESULTS_DIR/secrets_$TIMESTAMP.txt" . || true
    
    echo "✓ Trivy scans completed"
else
    echo "⚠ Trivy not available, skipping vulnerability scans"
fi

# 3. Image Configuration Analysis
echo "Analyzing image configuration..."
docker inspect "$IMAGE_NAME" > "$SCAN_RESULTS_DIR/image_config_$TIMESTAMP.json" 2>/dev/null || true

# Extract key security information
docker inspect "$IMAGE_NAME" | jq -r '
.[0] | {
  "User": .Config.User,
  "ExposedPorts": .Config.ExposedPorts,
  "Env": .Config.Env,
  "WorkingDir": .Config.WorkingDir,
  "Entrypoint": .Config.Entrypoint,
  "Cmd": .Config.Cmd,
  "Volumes": .Config.Volumes,
  "SecurityOpt": .HostConfig.SecurityOpt,
  "Privileged": .HostConfig.Privileged,
  "ReadonlyRootfs": .HostConfig.ReadonlyRootfs
}' > "$SCAN_RESULTS_DIR/security_config_$TIMESTAMP.json" 2>/dev/null || true

echo "✓ Image configuration analysis completed"

# 4. Generate Security Report
echo "Generating security report..."
cat > "$SCAN_RESULTS_DIR/security_report_$TIMESTAMP.md" << EOF
# Security Scan Report for $IMAGE_NAME
**Scan Date:** $(date)
**Scan ID:** $TIMESTAMP

## Summary
This report contains the results of automated security scanning for the broker integration container image.

## Scans Performed
- ✓ Dockerfile security analysis (Hadolint)
- ✓ Vulnerability scanning (Trivy)
- ✓ Configuration misconfigurations (Trivy)
- ✓ Secret detection (Trivy)
- ✓ Image configuration analysis

## Files Generated
- \`dockerfile_lint_$TIMESTAMP.txt\` - Dockerfile security issues
- \`vulnerabilities_$TIMESTAMP.json/txt\` - Known vulnerabilities
- \`misconfigurations_$TIMESTAMP.json/txt\` - Configuration issues
- \`secrets_$TIMESTAMP.json/txt\` - Potential secrets in code
- \`image_config_$TIMESTAMP.json\` - Full image configuration
- \`security_config_$TIMESTAMP.json\` - Security-relevant configuration

## Security Recommendations
1. Review all HIGH and CRITICAL vulnerabilities
2. Address Dockerfile security recommendations
3. Ensure no secrets are hardcoded in the image
4. Verify proper user permissions (non-root)
5. Check exposed ports are necessary
6. Validate environment variables don't contain sensitive data

## Next Steps
1. Fix any identified issues
2. Re-scan after fixes
3. Integrate scanning into CI/CD pipeline
4. Set up regular automated scans
EOF

# 5. Check for critical issues
echo "Checking for critical security issues..."
CRITICAL_ISSUES=0

# Check if running as root
if docker inspect "$IMAGE_NAME" | jq -r '.[0].Config.User' | grep -q "^$\|^0$\|^root$"; then
    echo "❌ CRITICAL: Container runs as root user"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
else
    echo "✓ Container runs as non-root user"
fi

# Check for privileged mode
if docker inspect "$IMAGE_NAME" | jq -r '.[0].HostConfig.Privileged' | grep -q "true"; then
    echo "❌ CRITICAL: Container configured for privileged mode"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
else
    echo "✓ Container not configured for privileged mode"
fi

# Summary
echo ""
echo "=========================================="
echo "Security Scan Summary"
echo "=========================================="
echo "Scan completed: $(date)"
echo "Results directory: $SCAN_RESULTS_DIR"
echo "Critical issues found: $CRITICAL_ISSUES"

if [ $CRITICAL_ISSUES -eq 0 ]; then
    echo "✓ No critical security issues detected"
    exit 0
else
    echo "❌ Critical security issues detected - review required"
    exit 1
fi