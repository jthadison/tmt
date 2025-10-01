# E2E Tests for TMT Dashboard

This directory contains End-to-End (E2E) tests for the TMT Trading Dashboard using Playwright.

## Prerequisites

### Backend Services Required

**IMPORTANT**: E2E tests require the following backend services to be running:

#### Core Services (Required for all tests)
- **Orchestrator** - `http://localhost:8089` - Provides `/health/detailed` endpoint
- **Dashboard** - `http://localhost:8090` - Next.js application

#### AI Agent Services (Required for Story 1.3 tests)
All 8 AI agents must be running for complete health data:
- Market Analysis - `http://localhost:8001`
- Strategy Analysis - `http://localhost:8002`
- Parameter Optimization - `http://localhost:8003`
- Learning Safety - `http://localhost:8004`
- Disagreement Engine - `http://localhost:8005`
- Data Collection - `http://localhost:8006`
- Continuous Improvement - `http://localhost:8007`
- Pattern Detection - `http://localhost:8008`

#### Additional Services (Optional but recommended)
- Execution Engine - `http://localhost:8082`
- Circuit Breaker - `http://localhost:8084`

## Starting Services

### Quick Start (All Services)

From the project root:

```bash
# Start Orchestrator
cd orchestrator && OANDA_API_KEY=your_key OANDA_ACCOUNT_IDS=your_account ENABLE_TRADING=true PORT=8089 python -m app.main &

# Start all 8 AI agents
cd agents/market-analysis && PORT=8001 python simple_main.py &
cd agents/strategy-analysis && PORT=8002 python start_agent_simple.py &
cd agents/parameter-optimization && PORT=8003 python start_agent.py &
cd agents/learning-safety && PORT=8004 python start_agent.py &
cd agents/disagreement-engine && PORT=8005 python start_agent.py &
cd agents/data-collection && PORT=8006 python start_agent.py &
cd agents/continuous-improvement && PORT=8007 python start_agent.py &
cd agents/pattern-detection && PORT=8008 python start_agent_simple.py &

# Start Dashboard (test runner will start this automatically)
# cd dashboard && npm run dev
```

### Health Check

Verify services are running:

```bash
# Check orchestrator
curl http://localhost:8089/health

# Check orchestrator detailed health endpoint
curl http://localhost:8089/health/detailed

# Check individual agents
curl http://localhost:8001/health
curl http://localhost:8002/health
# ... etc
```

## Running Tests

### Run All E2E Tests

```bash
cd dashboard
npx playwright test
```

### Run Specific Test File

```bash
npx playwright test e2e/story-1.3-connection-quality.spec.ts
```

### Run Tests in UI Mode (Recommended for Development)

```bash
npx playwright test --ui
```

### Run Tests in Specific Browser

```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

### Debug Tests

```bash
npx playwright test --debug
```

## Test Behavior Without Backend Services

### Expected Behavior

When backend services are **not running**, tests will:

1. **Connection Quality Tests**:
   - ✅ Indicator will still render (shows "disconnected" or "poor" quality)
   - ✅ Tests for indicator presence will pass
   - ⚠️ Quality might show "poor" or "disconnected" instead of "excellent"

2. **Mini Agent Health Cards Tests**:
   - ✅ Cards container will render with empty state message
   - ✅ Will show "No agent data available" or "Loading agents..."
   - ❌ Tests expecting 8 agent cards will fail (0 cards found)
   - ❌ Tests for card interactions will fail (no cards to click)

3. **Footer Layout Tests**:
   - ✅ Most layout tests will pass
   - ✅ Footer positioning and styling tests will pass

### Test Failures Without Services

The following test suites will fail without backend services:

- `Mini Agent Health Cards › should display all 8 agent cards`
- `Mini Agent Health Cards › should show agent name on each card`
- `Mini Agent Health Cards › should show status dot on each card`
- `Mini Agent Health Cards › should show latency value on each card`
- `Mini Agent Health Cards › should open detailed health panel when card is clicked`
- `Mini Agent Health Cards › should be keyboard navigable`
- `Integration with Detailed Panel › should scroll to clicked agent`

## Test Configuration

### Playwright Configuration

Configuration is in `dashboard/playwright.config.ts`:

- **Base URL**: `http://localhost:8090`
- **Web Server**: Automatically starts `npm run dev` before tests
- **Timeout**: 30 seconds per test (configurable)
- **Browsers**: Chromium, Firefox, WebKit, Mobile Chrome, Mobile Safari

### Test Retries

- **CI Environment**: 2 retries on failure
- **Local Development**: 0 retries (fail immediately)

## Troubleshooting

### "Error: page.goto: net::ERR_CONNECTION_REFUSED"

**Cause**: Dashboard is not running on port 8090

**Solution**:
```bash
cd dashboard && npm run dev
```

### "Test timeout of 30000ms exceeded"

**Cause**: Backend service not responding or very slow

**Solution**:
1. Check if orchestrator is running: `curl http://localhost:8089/health`
2. Check orchestrator logs for errors
3. Increase timeout in test if service is intentionally slow

### "expect(miniCards).toBeVisible() - Received: element not found"

**Cause**: No health data available (agents not running)

**Solution**:
1. Start all 8 AI agent services (see "Starting Services" above)
2. Verify agents are healthy: `curl http://localhost:8089/health/detailed`
3. Or run only tests that don't require agents

### "strict mode violation: locator resolved to N elements"

**Cause**: Selector is too broad and matches multiple elements

**Solution**: Tests have been updated to use specific `data-testid` attributes. Update to latest version.

## Test Reports

### HTML Report

After test run, view detailed HTML report:

```bash
npx playwright show-report
```

### Video Recordings

Videos are recorded for failed tests and available in:
```
dashboard/test-results/[test-name]/video.webm
```

### Screenshots

Screenshots on failure are saved in:
```
dashboard/test-results/[test-name]/test-failed-1.png
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Start Backend Services
  run: |
    # Start orchestrator and agents
    # (see "Starting Services" above)

- name: Run E2E Tests
  run: |
    cd dashboard
    npx playwright test
  env:
    CI: true

- name: Upload Test Results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: dashboard/playwright-report/
```

## Future Improvements

### Planned Enhancements

1. **Mock Data Provider**: Add ability to run E2E tests with mocked health data
2. **Service Health Checks**: Add pre-flight checks before test execution
3. **Parallel Service Startup**: Script to start all services in parallel
4. **Docker Compose**: Containerized test environment with all services
5. **Test Data Fixtures**: Predefined health states for consistent testing

### Mock Data Implementation (Future)

```typescript
// Future implementation idea
import { test, expect } from '@playwright/test'

test.use({
  mockHealthData: {
    agents: [
      { name: 'Market Analysis', status: 'healthy', port: 8001, latency_ms: 45 },
      // ... 7 more agents
    ]
  }
})
```

## Contributing

When adding new E2E tests:

1. Document any new service dependencies
2. Use specific selectors (prefer `data-testid` over class selectors)
3. Add tests to appropriate test suite
4. Include empty state and loading state tests
5. Test responsive behavior at multiple viewport sizes
6. Ensure WCAG accessibility compliance

## Contact

For questions or issues with E2E tests:
- Check test results in `playwright-report/`
- Review service logs in respective service directories
- See Story documentation in `docs/stories/dashboard-enhancements/`
