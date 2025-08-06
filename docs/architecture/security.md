# Security

## Input Validation

- **Validation Library:** Python: pydantic 2.5.0, TypeScript: zod 3.22.0, Rust: validator crate
- **Validation Location:** At API boundaries before any processing, never trust client input
- **Required Rules:**
  - All external inputs MUST be validated
  - Validation at API boundary before processing
  - Whitelist approach preferred over blacklist

## Authentication & Authorization

- **Auth Method:** JWT with RS256 signing, 2FA using TOTP (RFC 6238)
- **Session Management:** Stateless JWT with 15-minute access tokens, 7-day refresh tokens stored in HttpOnly cookies
- **Required Patterns:**
  - All endpoints except /auth/login require valid JWT
  - Role-based access control (RBAC) with trader, admin, read-only roles
  - Account-level authorization checks for all trading operations

## Secrets Management

- **Development:** `.env` files with git-crypt encryption, never commit unencrypted
- **Production:** HashiCorp Vault with Kubernetes auth, automatic rotation every 90 days
- **Code Requirements:**
  - NEVER hardcode secrets
  - Access via configuration service only
  - No secrets in logs or error messages

## API Security

- **Rate Limiting:** 100 requests/minute per IP, 1000 requests/minute per authenticated user
- **CORS Policy:** Whitelist specific origins only, no wildcard in production
- **Security Headers:** X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Strict-Transport-Security
- **HTTPS Enforcement:** TLS 1.3 minimum, HSTS with 1-year max-age

## Data Protection

- **Encryption at Rest:** AES-256-GCM for database encryption, Google Cloud KMS for key management
- **Encryption in Transit:** TLS 1.3 for all connections, mTLS between internal services
- **PII Handling:** No PII in logs, pseudonymization for analytics, right to deletion support
- **Logging Restrictions:** Never log: passwords, API keys, JWT tokens, account credentials, full credit cards

## Dependency Security

- **Scanning Tool:** Snyk for vulnerability scanning, integrated in CI/CD
- **Update Policy:** Security patches within 24 hours, minor updates weekly, major updates monthly with testing
- **Approval Process:** All new dependencies require security review, no packages with known critical vulnerabilities

## Security Testing

- **SAST Tool:** Semgrep with custom rules for financial code patterns
- **DAST Tool:** OWASP ZAP for API security testing, run before each production deploy
- **Penetration Testing:** Quarterly third-party penetration tests, annual red team exercises
