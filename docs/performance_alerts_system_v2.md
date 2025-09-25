# Enhanced Performance Alerts System v2.0

**Implementation Status**: ✅ **COMPLETED WITH ENHANCEMENTS**
**Action Items**: Addressed all merge requirements
**Updated**: September 24, 2025

---

## 🚀 **Enhanced Features**

This version addresses all action items for merge:

1. ✅ **Configurable Schedule Times** - Environment variable configuration
2. ✅ **Proper Async Context Management** - Full async/await implementation
3. ✅ **API Authentication/Authorization** - Role-based access control
4. ✅ **Retry Logic** - Exponential backoff for failed executions

---

## 🔧 **Configuration System**

### Environment Variables for Schedule Times

```bash
# Alert schedule configuration
ALERT_DAILY_PNL_TIME="17:00"              # Daily P&L check time (UTC)
ALERT_WEEKLY_STABILITY_TIME="08:00"       # Weekly stability check time (UTC)
ALERT_WEEKLY_STABILITY_DAY="monday"       # Day of week for stability check
ALERT_MONTHLY_FORWARD_TIME="09:00"        # Monthly forward test time (UTC)
ALERT_MONTHLY_FORWARD_DAY="1"             # Day of month for forward test
ALERT_THRESHOLD_TIME_1="12:00"            # First threshold check time (UTC)
ALERT_THRESHOLD_TIME_2="22:00"            # Second threshold check time (UTC)

# Retry configuration
ALERT_MAX_RETRY_ATTEMPTS="3"              # Maximum retry attempts
ALERT_RETRY_DELAY_SECONDS="60"            # Initial retry delay
ALERT_RETRY_BACKOFF_MULTIPLIER="2.0"      # Exponential backoff multiplier

# Alert suppression
ALERT_SUPPRESS_SIMILAR_MINUTES="60"       # Suppress similar alerts duration
ALERT_ESCALATION_DELAY_MINUTES="15"       # Escalation delay
```

### Example Configuration

```bash
# Production configuration
export ALERT_DAILY_PNL_TIME="21:00"                    # 9 PM UTC (5 PM EST)
export ALERT_WEEKLY_STABILITY_TIME="09:00"
export ALERT_WEEKLY_STABILITY_DAY="monday"
export ALERT_MONTHLY_FORWARD_TIME="10:00"
export ALERT_MAX_RETRY_ATTEMPTS="5"
export ALERT_RETRY_DELAY_SECONDS="30"
```

---

## 🔒 **Authentication & Authorization**

### Role-Based Access Control

| Role | Permissions | Description |
|------|-------------|-------------|
| **Viewer** | `alert:view_status`, `alert:view_history` | Read-only access to alerts and status |
| **Operator** | Viewer + `alert:trigger_manual`, `alert:enable_disable` | Can trigger and manage alerts |
| **Admin** | Operator + `alert:configure`, `alert:admin` | Full configuration and admin access |

### Authentication Methods

#### 1. API Key Authentication

```bash
# Set up API keys for different roles
export ALERT_ADMIN_API_KEY="admin-key-12345"
export ALERT_OPERATOR_API_KEY="operator-key-67890"
export ALERT_VIEWER_API_KEY="viewer-key-abcdef"

# Or use master key for all permissions
export ALERT_MASTER_API_KEY="master-key-xyz789"
```

#### 2. JWT Token Authentication

```bash
# Login with API key to get JWT token
curl -X POST http://localhost:8089/api/performance-alerts/auth/login \
  -H "Content-Type: application/json" \
  -d '{"api_key": "admin-key-12345"}'

# Response:
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
#   "token_type": "bearer",
#   "expires_in": 86400,
#   "user": {
#     "user_id": "admin",
#     "username": "admin",
#     "roles": ["admin"],
#     "permissions": ["alert:view_status", "alert:view_history", ...]
#   }
# }
```

### API Usage with Authentication

```bash
# Using API key header
curl -H "X-Alert-API-Key: admin-key-12345" \
  http://localhost:8089/api/performance-alerts/schedule/status

# Using JWT Bearer token
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  http://localhost:8089/api/performance-alerts/schedule/status

# Get current user info
curl -H "X-Alert-API-Key: admin-key-12345" \
  http://localhost:8089/api/performance-alerts/auth/me
```

### Authentication Environment Variables

```bash
# Authentication configuration
ALERT_AUTH_ENABLED="true"                   # Enable/disable authentication
ALERT_JWT_SECRET="your-secret-key"          # JWT signing secret
ALERT_JWT_ALGORITHM="HS256"                 # JWT algorithm
ALERT_JWT_EXPIRE_HOURS="24"                 # Token expiration hours
ALERT_API_KEY_HEADER="X-Alert-API-Key"      # API key header name

# User API keys
ALERT_ADMIN_API_KEY="secure-admin-key"
ALERT_OPERATOR_API_KEY="secure-operator-key"
ALERT_VIEWER_API_KEY="secure-viewer-key"
ALERT_MASTER_API_KEY="secure-master-key"     # Master key (all permissions)
```

---

## ⚡ **Async Context Management**

### Proper Async Implementation

The enhanced scheduler uses proper async/await throughout:

```python
class AsyncPerformanceAlertScheduler:
    @asynccontextmanager
    async def _scheduler_context(self):
        """Proper async context management"""
        try:
            # Initialize resources
            self.performance_tracker = get_performance_tracker()
            self._running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())

            yield self

        finally:
            await self._shutdown()

    async def start(self):
        """Start with context management"""
        async with self._scheduler_context():
            await self._shutdown_event.wait()

    async def _shutdown(self):
        """Graceful async shutdown"""
        self._running = False

        # Cancel scheduler task
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()

        # Cancel all alert tasks
        for task in self._alert_tasks.values():
            if not task.done():
                task.cancel()

        # Wait for cleanup
        if self._alert_tasks:
            await asyncio.gather(*self._alert_tasks.values(), return_exceptions=True)
```

### Integration with Orchestrator

```python
# Orchestrator starts scheduler as background task
async def start(self):
    self.background_tasks.append(
        asyncio.create_task(self.alert_scheduler.start())
    )
```

---

## 🔄 **Retry Logic with Exponential Backoff**

### Retry Configuration

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: float = 60.0      # seconds
    backoff_multiplier: float = 2.0
    max_delay: float = 300.0         # 5 minutes max
```

### Retry Logic Implementation

```python
async def _execute_alert_with_retry(self, alert_config, execution_id):
    """Execute alert with exponential backoff retry"""
    for attempt in range(1, alert_config.retry_config.max_attempts + 1):
        try:
            await self._execute_alert_function(alert_config)
            # Success - no retry needed
            return

        except Exception as e:
            if attempt < alert_config.retry_config.max_attempts:
                # Calculate exponential backoff delay
                delay = self._calculate_retry_delay(retry_config, attempt)
                logger.info(f"Retrying {alert_config.name} in {delay} seconds")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Alert {alert_config.name} failed after {attempt} attempts")

def _calculate_retry_delay(self, retry_config, attempt):
    """Exponential backoff: delay = initial * (multiplier ^ (attempt - 1))"""
    delay = retry_config.initial_delay * (retry_config.backoff_multiplier ** (attempt - 1))
    return min(delay, retry_config.max_delay)
```

### Retry Examples

```python
# Default retry behavior:
# Attempt 1: Immediate
# Attempt 2: 60 seconds delay
# Attempt 3: 120 seconds delay (60 * 2^1)
# Attempt 4: 240 seconds delay (60 * 2^2)
# Max delay capped at 300 seconds

# Custom retry for critical alerts:
critical_retry = RetryConfig(
    max_attempts=5,
    initial_delay=30.0,      # Start with 30 seconds
    backoff_multiplier=1.5,  # Gentler backoff
    max_delay=180.0          # Max 3 minutes
)
```

---

## 📊 **Enhanced API Endpoints**

### Authentication Endpoints

```bash
# Login and get JWT token
POST /api/performance-alerts/auth/login
Content-Type: application/json
Body: {"api_key": "your-api-key"}

# Get current user info
GET /api/performance-alerts/auth/me
Headers: X-Alert-API-Key: your-api-key OR Authorization: Bearer jwt-token
```

### Protected Alert Endpoints

All alert endpoints now require appropriate permissions:

```bash
# View status (requires: alert:view_status)
GET /api/performance-alerts/schedule/status

# View history (requires: alert:view_history)
GET /api/performance-alerts/schedule/summary/24

# Trigger manually (requires: alert:trigger_manual)
POST /api/performance-alerts/schedule/trigger/daily_pnl_check

# Enable/disable alerts (requires: alert:enable_disable)
POST /api/performance-alerts/schedule/enable/daily_pnl_check
POST /api/performance-alerts/schedule/disable/weekly_stability_check
```

### Enhanced Status Response

```json
{
  "success": true,
  "data": {
    "scheduler_running": true,
    "configuration": {
      "daily_pnl_time": "17:00",
      "weekly_stability_time": "08:00",
      "weekly_stability_day": "monday",
      "retry_config": {
        "max_attempts": 3,
        "delay_seconds": 60,
        "backoff_multiplier": 2.0
      }
    },
    "scheduled_alerts": [
      {
        "name": "daily_pnl_check",
        "frequency": "daily",
        "enabled": true,
        "time_of_day": "17:00 UTC",
        "last_run": "2025-09-24T17:00:15Z",
        "next_run": "2025-09-25T17:00:00Z",
        "retry_config": {
          "max_attempts": 3,
          "initial_delay": 60.0,
          "backoff_multiplier": 2.0
        },
        "recent_executions": [
          {
            "execution_id": "daily_pnl_check_20250924_170015",
            "started_at": "2025-09-24T17:00:15Z",
            "completed_at": "2025-09-24T17:00:45Z",
            "success": true,
            "attempt_count": 1,
            "error_message": null
          }
        ]
      }
    ]
  },
  "timestamp": "2025-09-24T18:30:00Z",
  "authenticated_user": "admin"
}
```

---

## 🏗️ **Architecture Improvements**

### File Structure

```
orchestrator/app/
├── alert_schedule_config.py          # Configurable schedule times
├── async_alert_scheduler.py          # Async scheduler with context management
├── alert_auth.py                     # Authentication & authorization
├── performance_alert_scheduler.py    # Legacy scheduler (kept for compatibility)
├── performance_alerts.py             # Core alert system (unchanged)
└── main.py                           # Updated API endpoints with auth
```

### Key Improvements

1. **Separation of Concerns**
   - Configuration management in separate module
   - Authentication logic isolated
   - Async scheduler with proper context management
   - Legacy scheduler maintained for backward compatibility

2. **Production-Ready Features**
   - Comprehensive error handling and logging
   - Graceful shutdown procedures
   - Resource cleanup and cancellation handling
   - Execution history tracking

3. **Security Enhancements**
   - Role-based access control
   - API key hashing for secure storage
   - JWT token authentication with expiration
   - Configurable authentication requirements

4. **Operational Excellence**
   - Detailed execution tracking and history
   - Comprehensive status reporting
   - Failed execution retry with backoff
   - Configurable schedule times for different environments

---

## 🚀 **Deployment Guide**

### 1. Environment Setup

```bash
# Minimal configuration (auth disabled)
export ALERT_AUTH_ENABLED="false"
export ALERT_DAILY_PNL_TIME="17:00"

# Production configuration (auth enabled)
export ALERT_AUTH_ENABLED="true"
export ALERT_ADMIN_API_KEY="$(openssl rand -hex 32)"
export ALERT_OPERATOR_API_KEY="$(openssl rand -hex 32)"
export ALERT_VIEWER_API_KEY="$(openssl rand -hex 32)"
export ALERT_JWT_SECRET="$(openssl rand -base64 32)"

# Schedule customization
export ALERT_DAILY_PNL_TIME="21:00"        # 9 PM UTC for US markets
export ALERT_WEEKLY_STABILITY_DAY="tuesday" # Tuesday for weekly reports
export ALERT_MAX_RETRY_ATTEMPTS="5"        # More retries for production
```

### 2. Startup Verification

```bash
# 1. Start orchestrator (includes async scheduler)
cd orchestrator && PORT=8089 python -m app.main

# 2. Verify scheduler is running
curl http://localhost:8089/api/performance-alerts/schedule/status

# 3. Test authentication (if enabled)
curl -H "X-Alert-API-Key: your-admin-key" \
  http://localhost:8089/api/performance-alerts/auth/me

# 4. Test manual trigger
curl -X POST -H "X-Alert-API-Key: your-admin-key" \
  http://localhost:8089/api/performance-alerts/schedule/trigger/daily_pnl_check
```

### 3. Monitoring

```bash
# Check execution history
curl http://localhost:8089/api/performance-alerts/schedule/status | jq '.data.scheduled_alerts[0].recent_executions'

# Monitor alert history files
ls -la performance_alerts/scheduled/

# Check logs for retry attempts
grep -i "retry" logs/orchestrator.log
```

---

## 🔧 **Migration from v1.0**

### Backward Compatibility

The v2.0 system maintains backward compatibility:
- Original `performance_alert_scheduler.py` is preserved
- Environment variables have sensible defaults
- Authentication can be completely disabled
- API endpoints maintain same basic structure

### Migration Steps

1. **Update imports** (if using scheduler directly):
   ```python
   # Old
   from .performance_alert_scheduler import get_alert_scheduler

   # New
   from .async_alert_scheduler import get_async_alert_scheduler
   ```

2. **Add new dependencies**:
   ```bash
   pip install PyJWT==2.8.0
   ```

3. **Configure environment** (optional):
   ```bash
   # Add to .env or environment
   ALERT_DAILY_PNL_TIME="17:00"
   ALERT_AUTH_ENABLED="false"  # Start with auth disabled
   ```

4. **Test migration**:
   ```bash
   # Verify scheduler starts successfully
   # Check API endpoints still work
   # Validate alert execution
   ```

---

## ✅ **Action Items Status**

All merge requirements have been addressed:

| Action Item | Status | Implementation |
|-------------|---------|---------------|
| ✅ **Configurable Schedule Times** | Complete | `alert_schedule_config.py` with environment variables |
| ✅ **Proper Async Context Management** | Complete | `async_alert_scheduler.py` with context managers |
| ✅ **API Authentication/Authorization** | Complete | `alert_auth.py` with role-based access control |
| ✅ **Retry Logic for Failed Executions** | Complete | Exponential backoff retry in async scheduler |

### Additional Improvements

- ✅ **Enhanced Error Handling** - Comprehensive exception handling and logging
- ✅ **Execution History Tracking** - Detailed execution records with success/failure tracking
- ✅ **Graceful Shutdown** - Proper async task cleanup and resource management
- ✅ **Production Security** - API key hashing, JWT tokens, configurable authentication
- ✅ **Operational Monitoring** - Enhanced status reporting and execution tracking

---

## 🎯 **Ready for Production**

The enhanced Performance Alerts System v2.0 is production-ready with:

- **Enterprise Security**: Role-based access control with API keys and JWT tokens
- **High Availability**: Async implementation with proper context management
- **Operational Excellence**: Configurable schedules, retry logic, and comprehensive monitoring
- **Backward Compatibility**: Smooth migration path from v1.0

This implementation addresses all merge requirements and provides a robust, scalable foundation for production deployment.

**Status**: 🟢 **READY FOR MERGE & PRODUCTION DEPLOYMENT**