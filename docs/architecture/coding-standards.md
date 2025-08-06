# Coding Standards

## Core Standards

- **Languages & Runtimes:** Python 3.11.8 (agents), Rust 1.75.0 (execution), TypeScript 5.3.3 (dashboard), Node.js 20.11.0 (dashboard backend)
- **Style & Linting:** Python: Black 24.2.0 (no config needed), Rust: rustfmt default, TypeScript: ESLint with Prettier
- **Test Organization:** Tests mirror source structure, `test_` prefix for Python, `.test.ts` suffix for TypeScript, `#[test]` attribute for Rust

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Python Classes | PascalCase | `MarketAnalysisAgent` |
| Python Functions | snake_case | `calculate_position_size` |
| TypeScript Components | PascalCase | `AccountGrid` |
| TypeScript Functions | camelCase | `fetchAccountData` |
| Database Tables | snake_case plural | `trading_accounts` |
| Kafka Topics | dot.notation | `trading.signals.generated` |
| Environment Variables | UPPER_SNAKE_CASE | `DATABASE_URL` |
| API Endpoints | kebab-case | `/api/v1/calculate-position-size` |

## Critical Rules

- **Use dependency injection for all external services:** Never instantiate clients directly, inject them
- **All monetary values must use Decimal type:** Never use float for money (Python: Decimal, Rust: rust_decimal, TypeScript: decimal.js)
- **Every Kafka message must include correlation_id:** Required for distributed tracing
- **All database queries must use repositories:** Never write raw SQL in business logic, use repository pattern
- **All API responses must use standardized wrapper:** `{"data": {...}, "error": null, "correlation_id": "..."}`
- **Never log sensitive data:** No passwords, API keys, or personal information in logs
- **All async operations must have timeouts:** Default 5s for HTTP, 30s for database operations
- **Use structured logging with correlation IDs:** Every log must include correlation_id and service context
- **Circuit breakers required for all external calls:** Trip after 5 failures, reset after 30s
- **All trades must be idempotent:** Use UUID idempotency keys with 24-hour retention
- **All public functions must have JSDoc comments:** TypeScript/JavaScript functions, classes, and interfaces require complete JSDoc documentation with @param, @returns, and @throws tags
