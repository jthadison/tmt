# Infrastructure and Deployment

## Infrastructure as Code

- **Tool:** Terraform 1.7.0
- **Location:** `infrastructure/terraform/`
- **Approach:** Environment-based modules with shared global resources

## Deployment Strategy

- **Strategy:** Blue-Green deployment with canary releases for critical services
- **CI/CD Platform:** GitHub Actions with environment-specific workflows
- **Pipeline Configuration:** `.github/workflows/` with staging and production pipelines

## Environments

- **Development:** Local Docker Compose with mock external services - Single developer setup with hot reloading
- **Staging:** GKE cluster with production-like data but scaled down - Full integration testing environment
- **Production:** Multi-region GKE with HA PostgreSQL and Kafka - 99.5% uptime target with auto-scaling

## Environment Promotion Flow

```text
Development (Local)
    ↓ [PR Merge]
Staging (GKE us-central1-a)
    ↓ [Manual Approval + Integration Tests Pass]
Production Canary (5% traffic)
    ↓ [Automated Health Checks + 15min soak time]
Production Blue-Green Swap (100% traffic)
```

## Rollback Strategy

- **Primary Method:** Blue-Green instant rollback via load balancer traffic switching
- **Trigger Conditions:** Error rate >1%, latency >500ms, circuit breaker activations, failed health checks
- **Recovery Time Objective:** <60 seconds for application rollback, <5 minutes for database rollback
