# CI/CD Pipeline Troubleshooting Guide

This guide helps developers and DevOps engineers troubleshoot common issues in the Adaptive Trading System CI/CD pipeline.

## 🔍 Quick Diagnostics

### Pipeline Status Check
```bash
# Check workflow status
gh workflow list

# View recent runs
gh run list --workflow=ci.yml --limit=10

# Get detailed run information
gh run view <run-id>
```

### Build Health Dashboard
- **GitHub Actions**: [Repository Actions](https://github.com/jthadison/tmt/actions)
- **Code Coverage**: [Codecov Dashboard](https://codecov.io/gh/jthadison/tmt)
- **Security Scans**: [Security Tab](https://github.com/jthadison/tmt/security)

---

## 🐛 Common Issues & Solutions

### Build Failures

#### **1. Python Test Failures**

**Symptoms:**
- `pytest` commands fail
- Import errors in Python modules
- Type checking errors with `mypy`

**Diagnostics:**
```bash
# Check Python environment
python --version
pip list

# Run tests locally
pytest agents/ --verbose
mypy agents/ --show-error-codes
```

**Common Solutions:**
```bash
# Update dependencies
pip install -e .[dev,test]

# Fix import paths
# Ensure __init__.py files exist in all package directories

# Resolve type errors
# Add proper type annotations
# Update mypy configuration in pyproject.toml
```

**Environment Issues:**
- Verify Python version is 3.11.8
- Check if all required environment variables are set
- Ensure database services are running for integration tests

#### **2. TypeScript Build Failures**

**Symptoms:**
- `npm run build` fails
- ESLint errors
- Type checking errors

**Diagnostics:**
```bash
# Check Node.js environment
node --version
npm --version

# Run build locally
cd dashboard
npm ci
npm run lint
npm run type-check
npm run build
```

**Common Solutions:**
```bash
# Fix dependencies
npm ci
npm audit fix

# Resolve linting errors
npm run lint -- --fix

# Fix TypeScript errors
# Update type definitions
# Fix strict mode violations
```

#### **3. Rust Compilation Failures**

**Symptoms:**
- `cargo build` fails
- Clippy warnings treated as errors
- Test compilation failures

**Diagnostics:**
```bash
# Check Rust environment
rustc --version
cargo --version

# Build locally
cd execution-engine
cargo check
cargo clippy
cargo test
```

**Common Solutions:**
```bash
# Fix compilation errors
cargo check --verbose

# Address clippy warnings
cargo clippy --fix

# Update dependencies
cargo update
```

### Security Scan Failures

#### **1. Semgrep SAST Issues**

**Symptoms:**
- Security vulnerabilities detected
- False positive security issues
- Configuration errors

**Solutions:**
```bash
# Run Semgrep locally
semgrep --config=auto .

# Exclude false positives
# Add to .semgrepignore file
# Use inline comments: # nosemgrep

# Fix genuine security issues
# Update vulnerable code patterns
# Add input validation
# Fix authentication/authorization issues
```

#### **2. Trivy Vulnerability Scanning**

**Symptoms:**
- Container image vulnerabilities
- Dependency vulnerabilities
- Base image security issues

**Solutions:**
```bash
# Scan locally
trivy image trading-dashboard:latest

# Fix vulnerabilities
# Update base images
# Update dependencies to patched versions
# Use multi-stage builds to reduce attack surface
```

### Docker Build Issues

#### **1. Build Context Problems**

**Symptoms:**
- Files not found during build
- Permission denied errors
- Build context too large

**Solutions:**
```bash
# Check .dockerignore
# Add unnecessary files to .dockerignore
# Verify COPY paths in Dockerfile

# Fix permissions
chmod +x scripts/*.sh

# Optimize build context
# Use multi-stage builds
# Copy only necessary files
```

#### **2. Dependency Installation Failures**

**Symptoms:**
- npm install fails
- pip install fails
- cargo build fails in container

**Solutions:**
```bash
# Use proper package managers
# Pin dependency versions
# Use proper base images
# Configure proxy settings if needed

# Example Dockerfile fixes
FROM node:20.11.0-alpine AS base
COPY package*.json ./
RUN npm ci --production
```

### Deployment Issues

#### **1. Staging Deployment Failures**

**Symptoms:**
- Helm deployment fails
- Kubernetes pods not starting
- Health checks failing

**Diagnostics:**
```bash
# Check cluster access
kubectl cluster-info
kubectl get nodes

# Check deployments
kubectl get deployments -n staging
kubectl describe deployment trading-dashboard -n staging

# Check pods
kubectl get pods -n staging
kubectl logs -f deployment/trading-dashboard -n staging
```

**Solutions:**
```bash
# Fix resource issues
# Increase memory/CPU limits
# Check resource quotas

# Fix configuration
# Verify secrets are created
# Check environment variables
# Validate ConfigMaps

# Fix health checks
# Ensure /health endpoints work
# Adjust health check timeouts
# Fix readiness probe configurations
```

#### **2. Service Communication Issues**

**Symptoms:**
- Services can't connect to database
- Inter-service communication failures
- Load balancer not accessible

**Solutions:**
```bash
# Check service discovery
kubectl get services -n staging
kubectl describe service trading-dashboard -n staging

# Test connectivity
kubectl exec -it deployment/trading-dashboard -n staging -- curl http://postgresql:5432

# Fix networking
# Check service selectors
# Verify port configurations
# Check network policies
```

### Performance Issues

#### **1. Slow Build Times**

**Symptoms:**
- CI pipeline takes too long
- Docker builds are slow
- Test execution is slow

**Solutions:**
```bash
# Optimize Docker builds
# Use build cache
# Optimize layer order
# Use multi-stage builds

# Optimize tests
# Run tests in parallel
# Use test databases
# Mock external services

# Use GitHub Actions cache
uses: actions/cache@v4
with:
  path: ~/.cargo/registry
  key: ${{ runner.os }}-cargo-${{ hashFiles('Cargo.lock') }}
```

#### **2. Test Timeout Issues**

**Symptoms:**
- Tests timeout in CI
- Integration tests fail due to timing
- Health checks timeout

**Solutions:**
```bash
# Increase timeouts
# Optimize test setup/teardown
# Use proper wait conditions
# Mock slow external services

# Example timeout fixes
pytest --timeout=300 tests/
jest --testTimeout=30000
```

---

## 🔧 Environment-Specific Issues

### Local Development

**Docker Compose Issues:**
```bash
# Reset Docker Compose
docker-compose down -v
docker-compose up -d

# Check service logs
docker-compose logs -f

# Rebuild images
docker-compose build --no-cache
```

**Pre-commit Hook Issues:**
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Run manually
pre-commit run --all-files

# Skip hooks temporarily (not recommended)
git commit --no-verify -m "message"
```

### Staging Environment

**GKE Access Issues:**
```bash
# Refresh cluster credentials
gcloud container clusters get-credentials trading-staging \
  --zone us-central1-a \
  --project ${GCP_PROJECT_ID}

# Check permissions
gcloud auth list
kubectl auth can-i create deployments --namespace=staging
```

**Resource Constraints:**
```bash
# Check cluster resources
kubectl top nodes
kubectl top pods -n staging

# Scale resources
kubectl scale deployment trading-dashboard --replicas=3 -n staging
```

### Production Environment

**Rollback Issues:**
```bash
# Check rollback status
kubectl rollout status deployment/trading-dashboard -n production
kubectl rollout history deployment/trading-dashboard -n production

# Manual rollback
kubectl rollout undo deployment/trading-dashboard -n production

# Verify rollback
kubectl get pods -n production -l app=trading-dashboard
```

---

## 📊 Monitoring & Alerting

### Pipeline Metrics

**Key Metrics to Monitor:**
- Build success rate (target: >95%)
- Build duration (target: <15 minutes)
- Test coverage (target: >80%)
- Security vulnerabilities (target: 0 critical)
- Deployment frequency (target: daily)
- Lead time (target: <4 hours)

**Grafana Dashboards:**
- CI/CD Pipeline Performance
- Build Quality Metrics
- Deployment Success Rate
- Security Scan Trends

### Alert Configurations

**Critical Alerts:**
- Build failure rate >10%
- Security scan failures
- Deployment failures
- Rollback executions

**Warning Alerts:**
- Build time >20 minutes
- Test coverage <75%
- Flaky test detection
- Resource utilization >80%

---

## 🆘 Emergency Procedures

### Critical Build Failure

1. **Immediate Actions:**
   ```bash
   # Check if main branch is broken
   git checkout main
   git pull origin main
   
   # Run local build
   ./scripts/deployment/build-all.sh
   
   # If build fails, revert last commit
   git revert HEAD --no-edit
   git push origin main
   ```

2. **Investigation:**
   - Check GitHub Actions logs
   - Review recent commits
   - Verify dependency changes
   - Check external service availability

3. **Communication:**
   - Notify team in #trading-system-alerts
   - Update incident status
   - Document root cause

### Production Deployment Failure

1. **Immediate Rollback:**
   ```bash
   # Trigger emergency rollback
   gh workflow run rollback.yml \
     -f environment=production \
     -f rollback_to=last-known-good \
     -f reason="Production deployment failure" \
     -f force_rollback=true
   ```

2. **Damage Assessment:**
   - Check system health
   - Verify trading operations
   - Review error logs
   - Assess data integrity

3. **Post-Incident:**
   - Conduct post-mortem
   - Update procedures
   - Improve monitoring
   - Document lessons learned

---

## 📞 Support Contacts

### Escalation Path

1. **Level 1:** Development Team
   - Slack: #trading-system-dev
   - Check: Build logs, test failures, code issues

2. **Level 2:** DevOps Team
   - Slack: #trading-system-devops
   - Check: Infrastructure, deployments, monitoring

3. **Level 3:** SRE/Platform Team
   - Slack: #platform-emergency
   - Check: Critical system failures, security incidents

### On-Call Contacts

- **Weekdays (9-5):** Development team rotation
- **After Hours:** SRE on-call engineer
- **Weekends:** Critical issues only

---

## 📚 Additional Resources

### Documentation Links
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Kubernetes Troubleshooting](https://kubernetes.io/docs/tasks/debug-application-cluster/)
- [Helm Troubleshooting](https://helm.sh/docs/faq/)

### Internal Documentation
- [Architecture Documentation](../docs/architecture/)
- [Deployment Runbooks](../docs/runbooks/)
- [Security Guidelines](../docs/security/)
- [Monitoring Setup](../docs/monitoring/)

### Tools & Utilities
- [GitHub CLI](https://cli.github.com/)
- [kubectl cheat sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Docker debugging commands](https://docs.docker.com/engine/reference/commandline/logs/)
- [Helm debugging](https://helm.sh/docs/chart_template_guide/debugging/)

---

**Last Updated:** 2025-08-07  
**Version:** 1.0  
**Maintainer:** DevOps Team