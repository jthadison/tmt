# Epic 2: Emergency Controls - Service Reference Card

**Quick Reference for Epic 2 E2E Testing**
**Last Updated**: 2025-10-01

---

## 🚀 Quick Start

### Windows (Recommended):
```bash
cd e:\projects\claude_code\prop-ai\tmt
start-trading.bat
```

### Cross-Platform:
```bash
# Terminal 1: Backend services
python start-complete-trading-system.py

# Terminal 2: Dashboard
cd dashboard
npm run dev
```

---

## 📊 Core Infrastructure (Required for Epic 2)

| Service | Port | Health URL | Status | Required For |
|---------|------|------------|--------|--------------|
| **Execution Engine** | 8082 | http://localhost:8082/health | 🟢 | Stories 2.1, 2.2 |
| **Circuit Breaker** | 8084 | http://localhost:8084/health | 🔴 | Story 2.2 (**Blocker 2**) |
| **Orchestrator** | 8089 | http://localhost:8089/health | 🔴 | Stories 2.1, 2.3 (**Blocker 3**) |
| **Dashboard** | 8090 | http://localhost:8090 | 🟢 | All E2E Tests |

### Critical Service Details

#### Execution Engine (Port 8082)
**Purpose**: Trade execution and position management
**Endpoints Used**:
- `GET /positions` - Get open positions (Story 2.2)
- `POST /api/positions/close-all` - Close all positions (Story 2.2)
- `GET /health` - Health check

**Startup**:
```bash
cd execution-engine
python simple_main.py
```

---

#### Circuit Breaker Agent (Port 8084) 🚨 **BLOCKER 2**
**Purpose**: Real-time risk monitoring and circuit breaker management
**Endpoints Used**:
- `GET /api/circuit-breakers/status` - Get threshold status (Story 2.2)
- `POST /api/circuit-breakers/reset` - Reset breakers (Story 2.2)
- `GET /health` - Health check

**Startup**:
```bash
cd agents/circuit-breaker
PORT=8084 OANDA_API_KEY=<key> OANDA_ACCOUNT_ID=<id> python main.py
```

**Why Required**: Story 2.2 Circuit Breaker Widget cannot function without this service

---

#### Orchestrator (Port 8089) 🚨 **BLOCKER 3**
**Purpose**: Central trading orchestration and emergency system coordination
**Endpoints Used**:

**Story 2.1**:
- `POST /api/trading/disable` - Emergency stop trading
- `POST /api/trading/enable` - Resume trading
- `GET /api/system/status` - Get system status

**Story 2.3 (NEW - Need Restart)**:
- `POST /api/rollback/execute` - Execute emergency rollback
- `GET /api/rollback/history` - Get rollback history
- `GET /api/rollback/conditions` - Get automated trigger conditions
- `PATCH /api/rollback/conditions/{type}` - Update condition
- `GET /api/audit/logs` - Query audit trail

**Startup**:
```bash
cd orchestrator
PORT=8089 OANDA_API_KEY=<key> OANDA_ACCOUNT_IDS=<ids> ENABLE_TRADING=true python -m uvicorn app.main:app --host 0.0.0.0 --port 8089
```

**Why Required**: New Story 2.3 endpoints must be loaded (requires restart if running)

---

#### Dashboard (Port 8090 or 3003)
**Purpose**: Frontend UI for all Epic 2 features
**Pages**:
- `/` - Home page with Emergency Stop button
- `/system-control` - Emergency Rollback Control (Story 2.3)
- `/audit-trail` - Audit Trail page (Story 2.3)

**Startup**:
```bash
cd dashboard
npm run dev
```

**Note**: Port configured in `playwright.config.ts` as 8090, but may run on 3003 depending on Next.js config

---

## 🤖 AI Agent Ecosystem (Supporting Services)

| Agent | Port | Health URL | Required | Notes |
|-------|------|------------|----------|-------|
| Market Analysis | 8001 | http://localhost:8001/health | ⚠️ Optional | Signal generation |
| Strategy Analysis | 8002 | http://localhost:8002/health | ⚠️ Optional | Performance tracking |
| Parameter Optimization | 8003 | http://localhost:8003/health | ⚠️ Optional | Risk tuning |
| Learning Safety | 8004 | http://localhost:8004/health | ⚠️ Optional | Safety systems |
| Disagreement Engine | 8005 | http://localhost:8005/health | ⚠️ Optional | Decision protocols |
| Data Collection | 8006 | http://localhost:8006/health | ⚠️ Optional | Metrics tracking |
| Continuous Improvement | 8007 | http://localhost:8007/health | ⚠️ Optional | Performance analysis |
| Pattern Detection | 8008 | http://localhost:8008/health | ⚠️ Optional | Wyckoff patterns |

**Note**: AI agents enhance functionality but are not strictly required for Epic 2 E2E testing

---

## 🧪 Epic 2 E2E Test Suites

### Test Files
| Test Suite | File | Stories Covered | Status |
|------------|------|-----------------|--------|
| Emergency Stop | `emergency-stop.spec.ts` | Story 2.1 | ✅ Passing (~85%) |
| Emergency Actions Panel | `emergency-actions-panel.spec.ts` | Story 2.2 | ⚠️ Passing (needs CB agent) |
| Emergency Rollback | `emergency-rollback.spec.ts` | Story 2.3 | 🚨 Blocked (import fixed) |

### Run All Epic 2 Tests
```bash
cd dashboard
npx playwright test emergency-stop.spec.ts emergency-actions-panel.spec.ts emergency-rollback.spec.ts --reporter=html
npx playwright show-report
```

### Run Individual Test Suites
```bash
# Story 2.1 only
npx playwright test emergency-stop.spec.ts

# Story 2.2 only
npx playwright test emergency-actions-panel.spec.ts

# Story 2.3 only
npx playwright test emergency-rollback.spec.ts
```

---

## 🔍 Service Health Check

### Quick Health Check
Run the automated health check script:
```bash
python scripts/health-check-epic2.py
```

This will:
- ✅ Check all 12 services (4 core + 8 AI agents)
- ✅ Show response times
- ✅ Identify blockers
- ✅ Provide story-specific readiness status
- ✅ Suggest next steps

### Manual Health Checks
```bash
# Core services
curl http://localhost:8082/health  # Execution Engine
curl http://localhost:8084/health  # Circuit Breaker
curl http://localhost:8089/health  # Orchestrator
curl http://localhost:8090         # Dashboard

# Test specific endpoints
curl http://localhost:8089/api/system/status              # Story 2.1
curl http://localhost:8084/api/circuit-breakers/status    # Story 2.2
curl http://localhost:8089/api/rollback/history?limit=5   # Story 2.3
curl http://localhost:8089/api/audit/logs?limit=5         # Story 2.3
```

---

## 🚨 Known Blockers & Fixes

### ✅ Blocker 1: Import Error (FIXED)
**Status**: ✅ **RESOLVED**
**File**: `dashboard/components/emergency/EmergencyRollbackControl.tsx`
**Fix Applied**: Changed to named import `import { useKeyboardShortcut }`

### ⚠️ Blocker 2: Circuit Breaker Agent Not Running
**Status**: 🔴 **ACTIVE BLOCKER**
**Impact**: Story 2.2 Circuit Breaker Widget non-functional
**Fix**:
```bash
cd agents/circuit-breaker
PORT=8084 OANDA_API_KEY=your_key OANDA_ACCOUNT_ID=your_account python main.py
```
**Or use**: `start-trading.bat` (starts all services)

### ⚠️ Blocker 3: Orchestrator Needs Restart
**Status**: 🔴 **ACTIVE BLOCKER**
**Impact**: Story 2.3 new API endpoints return 404
**Fix**:
```bash
# Stop current orchestrator, then restart
cd orchestrator
PORT=8089 OANDA_API_KEY=your_key OANDA_ACCOUNT_IDS=your_accounts ENABLE_TRADING=true python -m uvicorn app.main:app --host 0.0.0.0 --port 8089
```
**Or use**: `start-trading.bat` (restarts all services)

---

## 📝 Story-Specific Service Requirements

### Story 2.1: Emergency Stop Button
**Required Services**:
- ✅ Orchestrator (8089) - `/api/trading/disable`, `/api/trading/enable`
- ✅ Execution Engine (8082) - Position data
- ✅ Dashboard (8090) - UI

**Test Readiness**: ✅ **READY** (if services running)

---

### Story 2.2: Emergency Actions Panel & Circuit Breaker
**Required Services**:
- ✅ Orchestrator (8089) - Trading control
- ✅ Execution Engine (8082) - `/api/positions/close-all`
- 🔴 Circuit Breaker (8084) - **BLOCKER** - `/api/circuit-breakers/*`
- ✅ Dashboard (8090) - UI

**Test Readiness**: ⚠️ **PARTIAL** (needs Circuit Breaker agent)

---

### Story 2.3: Emergency Rollback Control & Audit Trail
**Required Services**:
- 🔴 Orchestrator (8089) - **BLOCKER** - New endpoints must be loaded
  - `/api/rollback/execute`
  - `/api/rollback/history`
  - `/api/rollback/conditions`
  - `/api/audit/logs`
- ✅ Dashboard (8090) - UI (import fixed)

**Test Readiness**: 🔴 **BLOCKED** (needs Orchestrator restart)

---

## 🎯 Complete System Startup Checklist

### Pre-Flight Checklist
- [ ] Environment variables set (OANDA_API_KEY, OANDA_ACCOUNT_IDS)
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`, `npm install`)

### Startup Sequence (Windows)
```bash
# Option A: All-in-one (Recommended)
start-trading.bat

# Option B: Step-by-step
# 1. Core infrastructure
cd execution-engine && python simple_main.py
cd agents/circuit-breaker && PORT=8084 python main.py
cd orchestrator && PORT=8089 python -m uvicorn app.main:app --host 0.0.0.0 --port 8089

# 2. Dashboard
cd dashboard && npm run dev

# 3. (Optional) AI agents
python start-complete-trading-system.py
```

### Verification
```bash
# Run health check
python scripts/health-check-epic2.py

# Expected output:
# ✅ Execution Engine (8082)
# ✅ Circuit Breaker (8084)
# ✅ Orchestrator (8089)
# ✅ Dashboard (8090)
# ✅ All critical services ready!
```

---

## 🔧 Troubleshooting

### Service Won't Start
**Issue**: `Port already in use`
**Fix**:
```bash
# Windows
netstat -ano | findstr ":8089"
taskkill /PID <pid> /F

# Linux/Mac
lsof -ti:8089 | xargs kill -9
```

### 404 on New Endpoints
**Issue**: Story 2.3 endpoints return 404
**Cause**: Orchestrator started before code was added
**Fix**: Restart orchestrator service

### Circuit Breaker Widget Shows Error
**Issue**: "Connection refused" on port 8084
**Cause**: Circuit Breaker agent not started
**Fix**: Start agent with `PORT=8084 python main.py` in `agents/circuit-breaker/`

### Dashboard Won't Load
**Issue**: "Module not found" or build errors
**Fix**:
```bash
cd dashboard
rm -rf node_modules .next
npm install
npm run dev
```

---

## 📚 Additional Resources

### Documentation
- **Epic 2 Overview**: `docs/epics/epic-2-emergency-controls.md`
- **Story 2.1**: `docs/stories/dashboard-enhancements/epic-2-emergency-controls/2.1.emergency-stop-button.md`
- **Story 2.2**: `docs/stories/dashboard-enhancements/epic-2-emergency-controls/2.2.emergency-actions-panel-circuit-breaker.md`
- **Story 2.3**: `docs/stories/dashboard-enhancements/epic-2-emergency-controls/2.3.emergency-rollback-audit-trail.md`
- **E2E Test Report**: `docs/qa/epic-2-e2e-test-report.md`

### Test Files
- **Emergency Stop Tests**: `dashboard/e2e/emergency-stop.spec.ts`
- **Emergency Actions Panel Tests**: `dashboard/e2e/emergency-actions-panel.spec.ts`
- **Emergency Rollback Tests**: `dashboard/e2e/emergency-rollback.spec.ts` (NEW)

### Scripts
- **Health Check**: `scripts/health-check-epic2.py`
- **Complete Startup**: `start-complete-trading-system.py`
- **Windows Startup**: `start-trading.bat`

---

## 🎉 Success Criteria

Epic 2 is ready for testing when:

- ✅ All 4 core services healthy (8082, 8084, 8089, 8090)
- ✅ Health check script shows 0 blockers
- ✅ Story 2.1 tests passing (~85%)
- ✅ Story 2.2 tests passing (~80%)
- ✅ Story 2.3 tests passing (~75%)
- ✅ All acceptance criteria met (41/45 ACs)

**Expected Test Results**: 100+ test scenarios, ~80% pass rate after fixing blockers

---

**Quick Command Summary**:
```bash
# Start everything
start-trading.bat

# Check health
python scripts/health-check-epic2.py

# Run tests
cd dashboard && npx playwright test emergency-*.spec.ts --reporter=html

# View results
npx playwright show-report
```

---

**QA Contact**: Quinn (Senior Developer & QA Architect)
**Last Health Check**: 2025-10-01
**Next Review**: After blocker fixes (ETA: ~15 minutes)
