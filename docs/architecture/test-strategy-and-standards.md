# Test Strategy and Standards

## Testing Philosophy

- **Approach:** Test-Driven Development (TDD) for critical paths, test-after for exploratory features
- **Coverage Goals:** 80% unit test coverage, 100% coverage for financial calculations and risk management
- **Test Pyramid:** 70% unit tests, 20% integration tests, 10% end-to-end tests

## Test Types and Organization

### Unit Tests

- **Framework:** Python: pytest 8.0.1, TypeScript: Jest 29.7.0, Rust: built-in test framework
- **File Convention:** Python: `test_*.py` in tests/ directory, TypeScript: `*.test.ts` alongside source, Rust: `#[cfg(test)]` modules
- **Location:** Python: `/agents/*/tests/`, TypeScript: `/dashboard/src/**/*.test.ts`, Rust: inline or `/tests/unit/`
- **Mocking Library:** Python: pytest-mock, TypeScript: Jest built-in mocks, Rust: mockall
- **Coverage Requirement:** 80% minimum, 100% for financial calculations

### Integration Tests

- **Scope:** Agent-to-agent communication, database operations, external API interactions
- **Location:** `/tests/integration/` at repository root
- **Test Infrastructure:**
  - **Database:** PostgreSQL Testcontainers for real database testing
  - **Message Queue:** Embedded Kafka (Redpanda) for event testing
  - **External APIs:** WireMock for HTTP stubbing, recorded responses for replay

### End-to-End Tests

- **Framework:** Playwright 1.41.0 for UI testing, pytest for API workflows
- **Scope:** Complete user journeys from login through trade execution
- **Environment:** Dedicated staging environment with test accounts
- **Test Data:** Synthetic prop firm accounts with mock funds

## Test Data Management

- **Strategy:** Factory pattern for test data generation with faker library
- **Fixtures:** `/shared/tests/fixtures/` for shared test data
- **Factories:** Python: factory_boy, TypeScript: fishery
- **Cleanup:** Automatic transaction rollback after each test, truncate tables in integration tests

## Continuous Testing

- **CI Integration:** All tests run on PR, integration tests on merge to main, E2E tests before production deploy
- **Performance Tests:** k6 for load testing, target 1000 concurrent users, <100ms p95 latency
- **Security Tests:** Semgrep for SAST, OWASP ZAP for DAST, dependency scanning with Snyk
