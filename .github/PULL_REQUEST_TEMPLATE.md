# Pull Request

## 📋 Description

<!-- Provide a brief description of the changes in this PR -->

### Story Reference
- **Story**: #[story-number] - [story-title]
- **Epic**: [epic-name]

### Change Type
- [ ] 🚀 New feature
- [ ] 🐛 Bug fix
- [ ] 📚 Documentation
- [ ] 🔧 Refactoring
- [ ] 🏗️ Infrastructure
- [ ] 🧪 Tests
- [ ] ⚡ Performance improvement
- [ ] 🔒 Security fix

## 🧪 Testing Checklist

### Unit Tests
- [ ] All new/modified code has unit tests
- [ ] All unit tests pass (`npm test`, `cargo test`, `pytest`)
- [ ] Code coverage meets 80% minimum requirement
- [ ] Tests cover edge cases and error scenarios

### Integration Tests
- [ ] Integration tests added for new features
- [ ] All integration tests pass
- [ ] Database migrations tested (if applicable)
- [ ] API contract tests updated (if applicable)

### Manual Testing
- [ ] Functionality manually tested locally
- [ ] Health endpoints respond correctly
- [ ] Error handling validated
- [ ] Performance impact assessed

## 🔒 Security Checklist

- [ ] No secrets or sensitive data in code
- [ ] Security scanning passes (Semgrep, Trivy)
- [ ] Input validation implemented where needed
- [ ] Authentication/authorization properly implemented
- [ ] Dependencies scanned for vulnerabilities

## 📊 Performance & Monitoring

- [ ] Performance impact assessed and acceptable
- [ ] Monitoring/logging added for new features
- [ ] Metrics collection implemented where appropriate
- [ ] Circuit breakers implemented for external calls
- [ ] Correlation IDs included in logs

## 🏗️ Infrastructure & Deployment

### Database Changes
- [ ] Database migrations are backwards compatible
- [ ] Migration rollback plan documented
- [ ] Database changes tested in staging
- [ ] Performance impact of schema changes assessed

### Configuration Changes
- [ ] New environment variables documented in .env.example
- [ ] Configuration changes don't break existing deployments
- [ ] Secrets properly configured in deployment pipelines
- [ ] Feature flags used for risky changes

### Docker & Kubernetes
- [ ] Docker images build successfully
- [ ] Kubernetes manifests updated (if applicable)
- [ ] Resource limits and requests specified
- [ ] Health check endpoints functional

## 📚 Documentation

- [ ] README updated with new requirements/setup steps
- [ ] API documentation updated (if applicable)
- [ ] Architecture decisions documented (if applicable)
- [ ] Troubleshooting guide updated (if needed)
- [ ] Story file updated with implementation notes

## 🚀 Deployment Readiness

### Pre-Deployment
- [ ] Feature flags configured (if applicable)
- [ ] Rollback plan documented
- [ ] Database backup verified (for schema changes)
- [ ] Monitoring alerts configured
- [ ] Stakeholders notified of deployment

### Staging Deployment
- [ ] Changes tested in staging environment
- [ ] End-to-end tests pass in staging
- [ ] Performance tests acceptable
- [ ] Integration with external services validated

### Production Readiness
- [ ] Canary deployment plan ready (for high-risk changes)
- [ ] Production secrets configured
- [ ] Monitoring dashboards updated
- [ ] Runbook updated with new operational procedures

## 🔄 Rollback Plan

**Rollback Strategy**: [Describe how to rollback these changes]

- [ ] Rollback steps documented
- [ ] Rollback tested in staging
- [ ] Data migration rollback plan (if applicable)
- [ ] Feature flag rollback option available

## 📝 Review Instructions

### For Reviewers
Please ensure:
1. **Code Quality**: Follow coding standards and best practices
2. **Security**: Check for potential security vulnerabilities
3. **Performance**: Assess impact on system performance
4. **Testing**: Verify adequate test coverage
5. **Documentation**: Ensure changes are properly documented

### Areas of Focus
<!-- Highlight specific areas where you'd like focused review -->

## 🔗 Related Links

- **Story**: [Link to story file]
- **Architecture Decision**: [Link to ADR if applicable]
- **Design Document**: [Link to design doc if applicable]
- **Monitoring Dashboard**: [Link to relevant Grafana dashboard]

## 📸 Screenshots/Evidence

<!-- Include screenshots, logs, or other evidence of testing -->

---

## ✅ Pre-Merge Checklist

**Before merging, confirm:**
- [ ] All CI checks pass (build, test, lint, security)
- [ ] Code review approved by at least one senior developer
- [ ] Story acceptance criteria met
- [ ] Breaking changes communicated to team
- [ ] Production deployment plan confirmed

**For DevOps/Infrastructure changes:**
- [ ] Changes reviewed by DevOps team
- [ ] Infrastructure changes tested in staging
- [ ] Monitoring and alerting verified
- [ ] Runbook updated

---

**Merge Strategy**: 
- [ ] Squash and merge (default for feature branches)
- [ ] Merge commit (for release branches)
- [ ] Rebase and merge (for simple changes)

**Post-Merge Actions**:
- [ ] Monitor deployment in staging
- [ ] Update project board/story status
- [ ] Notify stakeholders if needed