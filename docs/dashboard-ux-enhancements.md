# TMT Trading System - Dashboard UX Enhancement Specifications

**Version:** 1.0
**Date:** 2025-09-28
**Author:** Sally (UX Expert)
**Status:** Draft for Review

---

## Table of Contents

1. [Real-Time Status Visibility](#1-real-time-status-visibility)
2. [Emergency Controls](#2-emergency-controls)
3. [Trading Performance Dashboard](#3-trading-performance-dashboard)
4. [Intelligent Notifications](#4-intelligent-notifications)
5. [Dark Mode & Accessibility](#5-dark-mode--accessibility)
6. [Mobile Responsiveness](#6-mobile-responsiveness)
7. [Agent Intelligence Insights](#7-agent-intelligence-insights)
8. [Performance Analytics](#8-performance-analytics)
9. [Loading States & Error Handling](#9-loading-states--error-handling)
10. [Customization & Preferences](#10-customization--preferences)

---

## 1. Real-Time Status Visibility

### Overview
Create a persistent, always-visible health status system that provides instant awareness of all critical system components without overwhelming the user.

### User Goals
- Instantly assess system health without navigating away from current task
- Identify problems before they impact trading
- Maintain confidence in system reliability

### Components

#### 1.1 Global Status Bar
**Location:** Persistent header bar, top of all pages
**Behavior:** Always visible, does not scroll away

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│ 🟢 System Healthy  │  ⚡ 25ms  │  🔌 OANDA  │  🤖 8/8 Agents │
└─────────────────────────────────────────────────────────────┘
```

**States:**
- 🟢 **Healthy** (Green): All systems operational
- 🟡 **Degraded** (Yellow): Some non-critical issues
- 🔴 **Critical** (Red): Trading impacted or disabled
- ⚪ **Unknown** (Gray): System starting/loading

**Interaction:**
- Hover: Tooltip with detailed breakdown
- Click: Expand detailed health panel (drawer from top)

#### 1.2 Detailed Health Panel
**Trigger:** Click global status bar
**Animation:** Slide down from top, 300ms ease-out

**Content Structure:**
```
┌─────────────────────────────────────────────────────────┐
│ System Health Details                        [Close ×]  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  🤖 AI Agents (8/8 Active)                              │
│  ├─ 🟢 Market Analysis        25ms  ✓ Connected         │
│  ├─ 🟢 Strategy Analysis      32ms  ✓ Connected         │
│  ├─ 🟢 Parameter Optimization 28ms  ✓ Connected         │
│  ├─ 🟢 Learning Safety        19ms  ✓ Connected         │
│  ├─ 🟢 Disagreement Engine    31ms  ✓ Connected         │
│  ├─ 🟢 Data Collection        22ms  ✓ Connected         │
│  ├─ 🟢 Continuous Improvement 27ms  ✓ Connected         │
│  └─ 🟢 Pattern Detection      24ms  ✓ Connected         │
│                                                          │
│  🔌 External Services                                    │
│  ├─ 🟢 OANDA API             18ms  ✓ Connected          │
│  ├─ 🟢 Redis Cache            <1ms  ✓ Connected          │
│  └─ 🟢 Execution Engine       12ms  ✓ Connected          │
│                                                          │
│  ⚡ Circuit Breakers                                     │
│  ├─ ✓ Daily Loss Limit    $-245 / $1,000 (24%)         │
│  ├─ ✓ Account Drawdown    $-870 / $2,000 (43%)         │
│  └─ ✓ Consecutive Losses  1 / 3 trades                  │
│                                                          │
│  📊 System Performance                                   │
│  ├─ Uptime: 15d 7h 23m                                  │
│  ├─ Signal Latency: 45ms avg                           │
│  └─ Order Execution: 125ms avg                          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- Real-time WebSocket updates (no polling)
- Latency sparklines for each service (last 60 readings)
- Color-coded status indicators
- Click any agent/service for detailed logs

#### 1.3 Agent Health Cards
**Location:** System dashboard page (existing)
**Enhancement:** Add mini health cards to all pages

**Mini Card Design:**
```
┌──────────────────────┐
│ 🤖 Market Analysis   │
│ 🟢 Active · 25ms     │
│ ▁▃▄▃▂▃▅▃▂ Latency    │
└──────────────────────┘
```

**Card States:**
- **Active**: Green dot, showing latency
- **Slow**: Yellow dot, latency >100ms
- **Error**: Red dot, connection lost
- **Reconnecting**: Animated pulse

#### 1.4 Connection Quality Indicator
**Location:** Footer bar, right side
**Visual:** Simple connection icon with quality level

```
🔋 ●●●●○ Excellent    (All systems <50ms)
🔋 ●●●○○ Good         (All systems <100ms)
🔋 ●●○○○ Fair         (Some delays >100ms)
🔋 ●○○○○ Poor         (Critical delays >500ms)
```

### Technical Requirements
- WebSocket connection for real-time updates
- Fallback to polling (5s interval) if WebSocket fails
- Local state management for instant UI updates
- Health check API endpoint: `/health/detailed`
- Maximum 1 second stale data tolerance

### Success Metrics
- Users can identify system issues within 2 seconds
- 95% of users understand status colors without training
- Reduce time-to-detect issues by 80%

---

## 2. Emergency Controls

### Overview
Provide instant, accessible emergency controls that prevent accidental activation while enabling rapid response to critical situations.

### User Goals
- Stop all trading immediately when needed
- Close positions quickly in adverse conditions
- Reset circuit breakers safely
- Rollback to safe configurations

### Components

#### 2.1 Emergency Stop Button
**Location:** Persistent in header bar, right side
**Visual Priority:** High visibility, cannot be missed

**Button Design:**
```
┌──────────────────────┐
│   🛑 EMERGENCY STOP  │  ← Large, red, always visible
└──────────────────────┘
```

**Interaction Flow:**
1. Click button → Confirmation modal appears
2. Modal requires typing "STOP" to confirm
3. Progress indicator shows action executing
4. Success confirmation with options to close positions

**Confirmation Modal:**
```
┌──────────────────────────────────────────────────┐
│  ⚠️  EMERGENCY STOP CONFIRMATION                 │
├──────────────────────────────────────────────────┤
│                                                   │
│  This will immediately:                           │
│  • Stop all new trade signals                     │
│  • Prevent new positions from opening            │
│  • Keep existing positions open                  │
│                                                   │
│  Type STOP to confirm:                           │
│  ┌─────────────────────────────────────────┐    │
│  │                                          │    │
│  └─────────────────────────────────────────┘    │
│                                                   │
│  ☐ Also close all open positions immediately    │
│                                                   │
│  [ Cancel ]              [ EXECUTE STOP ] ←Red  │
└──────────────────────────────────────────────────┘
```

**Keyboard Shortcut:** `Ctrl+Shift+S` (with same confirmation)

#### 2.2 Emergency Actions Panel
**Location:** Slide-out panel from right side
**Trigger:** "Emergency" button in header or `Alt+E`

**Panel Design:**
```
┌─────────────────────────────────────────────────┐
│ Emergency Controls                     [Close] │
├─────────────────────────────────────────────────┤
│                                                  │
│  Quick Actions                                   │
│  ┌────────────────────────────────────────────┐│
│  │  🛑 Stop All Trading          [ACTIVATE]   ││
│  └────────────────────────────────────────────┘│
│  ┌────────────────────────────────────────────┐│
│  │  💰 Close All Positions       [EXECUTE]    ││
│  └────────────────────────────────────────────┘│
│  ┌────────────────────────────────────────────┐│
│  │  🔄 Emergency Rollback        [TRIGGER]    ││
│  │     Return to Cycle 4 parameters           ││
│  └────────────────────────────────────────────┘│
│                                                  │
│  Current Status                                  │
│  • Trading: ✅ ENABLED                          │
│  • Open Positions: 3 trades                     │
│  • Unrealized P&L: -$145.00                     │
│                                                  │
│  Circuit Breakers                                │
│  ┌────────────────────────────────────────────┐│
│  │  Daily Loss:    $-245 / $1,000  (24%) ✓   ││
│  │  Account DD:    $-870 / $2,000  (43%) ✓   ││
│  │  Consec. Loss:  1 / 3 trades         ✓   ││
│  └────────────────────────────────────────────┘│
│  [ Reset All Breakers ]                         │
│                                                  │
│  Recent Emergency Actions                        │
│  • None in last 24 hours                        │
│                                                  │
└─────────────────────────────────────────────────┘
```

#### 2.3 Circuit Breaker Dashboard
**Location:** Dedicated widget on main dashboard
**Size:** 2x2 grid space (responsive)

**Widget Design:**
```
┌─────────────────────────────────────────┐
│  ⚡ Circuit Breakers          [Details] │
├─────────────────────────────────────────┤
│                                          │
│  Daily Loss Limit                        │
│  ████████░░░░░░░░░░  24%                │
│  $245 / $1,000                           │
│                                          │
│  Account Drawdown                        │
│  ████████████████████░░  43%            │
│  $870 / $2,000                           │
│                                          │
│  Consecutive Losses                      │
│  ████░░░░░░░░  1 / 3 trades             │
│                                          │
│  ✓ All breakers normal                  │
│                                          │
└─────────────────────────────────────────┘
```

**Breaker Trip Animation:**
- Bar turns red with pulsing animation
- Alert sound (optional, user-configurable)
- Push notification sent
- Modal overlay appears with options

#### 2.4 Emergency Rollback Control
**Location:** System Control Panel page
**Integration:** Connected to emergency rollback system

**Control Interface:**
```
┌──────────────────────────────────────────────────┐
│  🔄 Emergency Rollback System                    │
├──────────────────────────────────────────────────┤
│                                                   │
│  Current Mode: Session-Targeted Trading          │
│  Active Since: 2025-09-20 14:30:00 UTC          │
│                                                   │
│  ┌────────────────────────────────────────────┐ │
│  │  Rollback to Cycle 4 Universal Parameters  │ │
│  │                                             │ │
│  │  This will:                                 │ │
│  │  ✓ Restore proven configuration            │ │
│  │  ✓ Maintain all open positions             │ │
│  │  ✓ Switch to universal trading              │ │
│  │  ✓ Log event for audit trail               │ │
│  │                                             │ │
│  │  [ Execute Rollback ]                       │ │
│  └────────────────────────────────────────────┘ │
│                                                   │
│  Rollback History                                │
│  • No rollbacks in last 30 days                  │
│                                                   │
│  Automated Triggers (Monitoring)                 │
│  ☐ Performance decline > 15%                     │
│  ☐ Confidence interval breach (2+ days)         │
│  ☐ Overfitting score > 0.8                      │
│  ☐ Walk-forward stability < 30                   │
│                                                   │
└──────────────────────────────────────────────────┘
```

### Keyboard Shortcuts
- `Ctrl+Shift+S` - Emergency stop
- `Ctrl+Shift+C` - Close all positions
- `Ctrl+Shift+R` - Emergency rollback
- `Alt+E` - Open emergency panel

### Safety Features
- **Confirmation Required**: All destructive actions require explicit confirmation
- **Audit Trail**: Every emergency action logged with timestamp and user
- **Undo Option**: Where possible, provide rollback for accidental actions
- **Rate Limiting**: Prevent rapid repeated emergency actions
- **Auto-disable**: Emergency stop button disabled while action in progress

### Success Metrics
- Emergency actions executable within 3 seconds (including confirmation)
- Zero accidental emergency stops in production
- 100% of emergency actions logged and auditable

---

## 3. Trading Performance Dashboard

### Overview
Create a comprehensive, real-time performance tracking interface that helps traders understand P&L, positions, and performance trends at a glance.

### User Goals
- Monitor P&L in real-time across all accounts
- Track position performance individually and collectively
- Understand performance by trading session
- Identify profitable patterns and periods

### Components

#### 3.1 Live P&L Ticker
**Location:** Header bar, center position
**Behavior:** Updates in real-time via WebSocket

**Ticker Design:**
```
┌────────────────────────────────────────────────┐
│  Today: +$1,245.50 (+1.25%)  ↗  Live Update   │
└────────────────────────────────────────────────┘
```

**Features:**
- Color-coded: Green (positive), Red (negative), Gray (zero)
- Animated transitions when value changes
- Arrow indicator showing direction trend
- Sparkline showing today's P&L trajectory
- Click to expand full P&L breakdown

**Expanded View Modal:**
```
┌─────────────────────────────────────────────────┐
│  📊 P&L Breakdown                     [Close ×] │
├─────────────────────────────────────────────────┤
│                                                  │
│  Current P&L: +$1,245.50 (+1.25%)               │
│  ▁▂▃▅▆▇█▇▆▅▃▂▁ Real-time chart                 │
│                                                  │
│  Breakdown:                                      │
│  • Realized:    +$980.00   (3 closed trades)    │
│  • Unrealized:  +$265.50   (2 open positions)   │
│                                                  │
│  Period Comparison:                              │
│  • Today:       +$1,245.50                      │
│  • Week:        +$3,890.25                      │
│  • Month:       +$12,567.80                     │
│  • All-Time:    +$45,234.60                     │
│                                                  │
│  Best Trade Today: EUR/USD +$450.00             │
│  Worst Trade Today: GBP/USD -$123.00            │
│                                                  │
│  [ View Detailed Analytics ]                    │
└─────────────────────────────────────────────────┘
```

#### 3.2 Position Cards Grid
**Location:** Main dashboard page
**Layout:** Responsive grid (3 columns desktop, 2 tablet, 1 mobile)

**Position Card Design:**
```
┌──────────────────────────────────────────┐
│  EUR/USD • BUY                    [•••]  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  +$265.50 (+2.45%)         🟢 Winning   │
├──────────────────────────────────────────┤
│  Entry:     1.0845                       │
│  Current:   1.0872  (+27 pips)          │
│  SL:        1.0820  (-25 pips)          │
│  TP:        1.0920  (+75 pips)          │
│  ─────────────────────────────────       │
│  🎯 TP: ████████░░  48% to target       │
│  🛑 SL: ░░████████  52% from stop        │
│  ─────────────────────────────────       │
│  Size: 10,000 units • Age: 2h 15m       │
│  Agent: Pattern Detection               │
│  ─────────────────────────────────       │
│  [ Close Position ]    [ Modify ]       │
└──────────────────────────────────────────┘
```

**Card States:**
- **Winning**: Green accent, positive P&L
- **Losing**: Red accent, negative P&L
- **Near TP**: Gold accent, >75% to take profit
- **Near SL**: Orange accent, <25% from stop loss

**Interaction:**
- Click card → Expand full position details
- Hover → Show real-time price chart tooltip
- Click [•••] → Quick actions menu (modify, close, add to TP/SL)

#### 3.3 Session Performance Breakdown
**Location:** Performance page, prominent widget
**Size:** Full-width section

**Session Widget Design:**
```
┌────────────────────────────────────────────────────────────────┐
│  📅 Trading Session Performance         [Today] [Week] [Month] │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Sydney Session (22:00-07:00 GMT)                              │
│  ████████░░░░░░  +$123.50  (1 trade)  78% confidence          │
│                                                                 │
│  Tokyo Session (00:00-09:00 GMT)                               │
│  ████████████░░  +$445.00  (2 trades)  85% confidence         │
│                                                                 │
│  London Session (08:00-17:00 GMT)       ⭐ Best Performer      │
│  ██████████████  +$892.30  (5 trades)  72% confidence         │
│                                                                 │
│  New York Session (13:00-22:00 GMT)                            │
│  ████████░░░░░░  +$234.70  (3 trades)  70% confidence         │
│                                                                 │
│  Overlap Sessions (08:00-17:00 GMT)                            │
│  ██████████░░░░  +$556.20  (4 trades)  70% confidence         │
│                                                                 │
│  Total: +$2,251.70 • 15 trades • 86.7% win rate               │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

**Features:**
- Color-coded bars showing P&L magnitude
- Session-specific confidence thresholds displayed
- Click session to see detailed breakdown
- Filter by date range
- Export session data

#### 3.4 Performance Metrics Dashboard
**Location:** Dedicated "Performance" page
**Layout:** Multi-widget dashboard

**Key Metrics Displayed:**

**Win Rate Gauge:**
```
┌─────────────────────┐
│  🎯 Win Rate        │
│      ┌───┐          │
│    ┌─┤ 87│─┐        │
│  ┌─┤ └───┘ ├─┐      │
│  │ 0   %   100│      │
│  └─────────────┘     │
│  87% (13/15 trades) │
└─────────────────────┘
```

**Profit Factor Display:**
```
┌─────────────────────┐
│  💰 Profit Factor   │
│      2.45           │
│  ───────────────    │
│  Gross Profit:      │
│  $3,245.00          │
│  Gross Loss:        │
│  $1,325.00          │
└─────────────────────┘
```

**Average Trade Metrics:**
```
┌─────────────────────┐
│  📈 Avg Trade       │
│  Win:  +$250.00     │
│  Loss: -$165.00     │
│  R:R:  1.5:1        │
│  Duration: 3h 25m   │
└─────────────────────┘
```

**Equity Curve Chart:**
```
┌────────────────────────────────────────┐
│  📊 Equity Curve (30 Days)             │
│  $105,000 ┤           ╭──╮             │
│           │         ╭─╯  ╰─╮           │
│           │       ╭─╯      ╰─╮         │
│  $100,000 ├─────╯─          ╰───      │
│           └─────────────────────       │
│           0d    15d    30d             │
│                                         │
│  Current: $104,567  (+4.57%)           │
└────────────────────────────────────────┘
```

### Real-Time Updates
- P&L updates: Every tick (WebSocket)
- Position status: Every 1 second
- Charts: Every 5 seconds
- Session breakdowns: Every trade completion

### Success Metrics
- Users can assess performance within 5 seconds of opening dashboard
- 95% of traders use session breakdown feature weekly
- Reduce time spent checking positions by 40%

---

## 4. Intelligent Notifications

### Overview
Implement a smart notification system that alerts users to important events without creating alert fatigue, using progressive disclosure and intelligent grouping.

### User Goals
- Stay informed of critical events without constant monitoring
- Reduce notification noise and alert fatigue
- Understand what action (if any) is needed
- Customize notification preferences by priority

### Components

#### 4.1 Notification Center
**Location:** Header bar, bell icon with badge counter
**Badge:** Shows unread count (max display: 9+)

**Bell Icon States:**
```
🔔     - No unread notifications
🔔 3   - 3 unread notifications
🔔 9+  - 9 or more unread
🔴 !   - Critical alert (pulsing red)
```

**Notification Panel:**
```
┌────────────────────────────────────────────────┐
│  🔔 Notifications              [Mark All Read] │
├────────────────────────────────────────────────┤
│  Today                                          │
│                                                 │
│  🔴 Critical · 2m ago                          │
│  ┌───────────────────────────────────────────┐│
│  │ ⚠️ Circuit Breaker Triggered               ││
│  │ Daily loss limit reached: $1,000           ││
│  │ [ View Details ] [ Reset Breaker ]         ││
│  └───────────────────────────────────────────┘│
│                                                 │
│  🟢 Success · 15m ago                          │
│  ┌───────────────────────────────────────────┐│
│  │ ✅ Position Closed: EUR/USD                ││
│  │ Profit: +$445.00 (+4.1%)                   ││
│  │ [ View Trade ] [ Dismiss ]                 ││
│  └───────────────────────────────────────────┘│
│                                                 │
│  🟡 Warning · 1h ago                           │
│  ┌───────────────────────────────────────────┐│
│  │ ⚡ High Latency Detected                   ││
│  │ Market Analysis agent: 450ms avg           ││
│  │ [ View Health ] [ Dismiss ]                ││
│  └───────────────────────────────────────────┘│
│                                                 │
│  Earlier Today                                  │
│  (3 more notifications)                         │
│                                                 │
│  [ Show All Notifications ]                    │
└────────────────────────────────────────────────┘
```

#### 4.2 Notification Types & Priority

**Critical (Red) - Immediate attention required:**
- Circuit breaker triggered
- Emergency stop activated
- Connection lost to OANDA
- System error affecting trading
- Position in danger (near stop loss)

**Warning (Yellow) - Attention recommended:**
- Agent performance degraded
- High latency detected
- Circuit breaker approaching threshold
- Unusual market conditions detected

**Success (Green) - Informational, positive:**
- Trade closed with profit
- Target profit reached
- System update completed
- Performance milestone achieved

**Info (Blue) - General information:**
- Trade opened
- Order filled
- System status update
- Scheduled maintenance reminder

#### 4.3 Smart Grouping
**Automatic grouping to reduce noise:**

**Example: Multiple trades grouped:**
```
┌────────────────────────────────────────┐
│  📊 5 Trades Completed · Last 30min    │
│  Net P&L: +$1,234.50                  │
│  [ View All Trades ] [ Dismiss ]      │
└────────────────────────────────────────┘
```

**Example: System events grouped:**
```
┌────────────────────────────────────────┐
│  ⚙️ 3 Agents Reconnected · Last 10min │
│  All systems operational               │
│  [ View Health ] [ Dismiss ]          │
└────────────────────────────────────────┘
```

**Grouping Rules:**
- Similar events within 30 minutes → Group
- More than 5 info notifications → Collapse
- Critical alerts NEVER grouped
- User can expand groups to see individual notifications

#### 4.4 Toast Notifications
**Location:** Top-right corner of screen
**Behavior:** Auto-dismiss after timeout (configurable)

**Toast Design:**
```
┌──────────────────────────────────┐
│  ✅ Trade Executed               │
│  EUR/USD BUY opened at 1.0845   │
│  [×]                             │
└──────────────────────────────────┘
```

**Toast Durations:**
- Critical: No auto-dismiss (manual close only)
- Warning: 10 seconds
- Success: 5 seconds
- Info: 3 seconds

**Toast Position Stack:**
- Multiple toasts stack vertically
- Maximum 3 visible at once
- Older toasts slide down and fade
- Click toast → Open full notification details

#### 4.5 Action-Oriented Messages
**Every notification includes suggested actions:**

**Bad Example (vague):**
```
❌ "Agent disconnected"
```

**Good Example (actionable):**
```
✅ "Market Analysis agent disconnected"
   [ Reconnect Agent ] [ View Logs ] [ Contact Support ]
```

**Template Structure:**
```
[Icon] [Title]
[Description explaining impact]
[Suggested Actions as Buttons]
[Timestamp]
```

#### 4.6 Notification Preferences
**Location:** Settings page → Notifications section

**Preference Controls:**
```
┌──────────────────────────────────────────────┐
│  Notification Preferences                    │
├──────────────────────────────────────────────┤
│                                               │
│  Delivery Methods:                            │
│  ☑ In-app notifications                      │
│  ☑ Browser push notifications                │
│  ☑ Email notifications                       │
│  ☐ Slack notifications                       │
│  ☐ SMS notifications (Critical only)         │
│                                               │
│  Priority Filters:                            │
│  ┌──────────────────────────────────────┐   │
│  │ Critical  ☑ In-app  ☑ Push  ☑ Email │   │
│  │ Warning   ☑ In-app  ☑ Push  ☐ Email │   │
│  │ Success   ☑ In-app  ☐ Push  ☐ Email │   │
│  │ Info      ☑ In-app  ☐ Push  ☐ Email │   │
│  └──────────────────────────────────────┘   │
│                                               │
│  Quiet Hours:                                 │
│  ☑ Enable quiet hours                        │
│  From: [22:00] To: [07:00]                   │
│  ☑ Allow critical alerts during quiet hours  │
│                                               │
│  Grouping:                                    │
│  ☑ Group similar notifications               │
│  ☑ Smart digest (bundle low-priority)        │
│  Digest frequency: [Every 30 minutes ▾]      │
│                                               │
│  Event-Specific Settings:                    │
│  ┌──────────────────────────────────────┐   │
│  │ Trade Events                          │   │
│  │ ☑ Trade opened                        │   │
│  │ ☑ Trade closed (profit)               │   │
│  │ ☑ Trade closed (loss)                 │   │
│  │ ☑ Stop loss triggered                 │   │
│  │ ☑ Take profit reached                 │   │
│  │                                        │   │
│  │ System Events                          │   │
│  │ ☑ Agent status changes                │   │
│  │ ☑ Circuit breaker triggers            │   │
│  │ ☑ Connection issues                   │   │
│  │ ☑ Performance alerts                  │   │
│  └──────────────────────────────────────┘   │
│                                               │
│  [ Reset to Defaults ]      [ Save Changes ] │
└──────────────────────────────────────────────┘
```

### Notification Sound Policy
- Critical: Distinct alert sound (urgent)
- Warning: Softer notification sound
- Success: Positive chime
- Info: Subtle notification sound
- All sounds user-configurable or can be muted

### Browser Push Notifications
**Requires user permission on first load**

**Permission Request Modal:**
```
┌────────────────────────────────────────┐
│  🔔 Enable Notifications?              │
├────────────────────────────────────────┤
│  Stay informed about:                   │
│  • Critical system alerts               │
│  • Trade completions                    │
│  • Circuit breaker triggers             │
│  • Connection issues                    │
│                                         │
│  You can customize what notifications  │
│  you receive in Settings.              │
│                                         │
│  [ Maybe Later ]      [ Enable ]       │
└────────────────────────────────────────┘
```

### Success Metrics
- Reduce alert fatigue: <3 non-critical notifications per hour
- 90% of critical alerts acknowledged within 2 minutes
- <5% of notifications dismissed without reading
- User satisfaction with notification relevance >4.5/5

---

## 5. Dark Mode & Accessibility

### Overview
Implement a comprehensive dark mode theme and accessibility features that support extended trading sessions and ensure the dashboard is usable by all traders.

### User Goals
- Reduce eye strain during long trading sessions
- Work comfortably in low-light environments
- Use keyboard navigation efficiently
- Access all features regardless of ability

### Components

#### 5.1 Theme Toggle
**Location:** Header bar, near settings icon
**Behavior:** Instant theme switch, persisted to local storage

**Toggle Design:**
```
Light Mode: ☀️
Dark Mode:  🌙
Auto:       🌓 (follows system preference)
```

**Toggle Interaction:**
- Click to cycle: Light → Dark → Auto
- Keyboard shortcut: `Ctrl+Shift+D`
- Smooth transition animation (300ms)
- No page flash or content reflow

#### 5.2 Color Palette

**Light Theme:**
```
Background:     #FFFFFF (White)
Surface:        #F5F5F5 (Light Gray)
Card:           #FFFFFF (White)
Border:         #E0E0E0 (Medium Gray)

Text Primary:   #212121 (Near Black)
Text Secondary: #757575 (Medium Gray)
Text Disabled:  #BDBDBD (Light Gray)

Primary:        #1976D2 (Blue)
Success:        #2E7D32 (Green)
Warning:        #F57C00 (Orange)
Error:          #C62828 (Red)
Info:           #0288D1 (Light Blue)
```

**Dark Theme:**
```
Background:     #121212 (Near Black)
Surface:        #1E1E1E (Dark Gray)
Card:           #2C2C2C (Lighter Dark Gray)
Border:         #3C3C3C (Medium Dark Gray)

Text Primary:   #FFFFFF (White)
Text Secondary: #B0B0B0 (Light Gray)
Text Disabled:  #666666 (Dark Gray)

Primary:        #42A5F5 (Light Blue)
Success:        #66BB6A (Light Green)
Warning:        #FFA726 (Light Orange)
Error:          #EF5350 (Light Red)
Info:           #29B6F6 (Sky Blue)
```

**High Contrast Theme:**
- Available as accessibility option
- Maximum contrast ratios for text
- Bold borders and separators
- Larger focus indicators

#### 5.3 Accessibility Features

**Keyboard Navigation:**
- **Tab Order**: Logical flow through all interactive elements
- **Focus Indicators**: 3px solid border on focused elements
- **Skip Links**: "Skip to main content" at top of page

**Keyboard Shortcuts:**
```
Navigation:
- Alt+1: Dashboard
- Alt+2: Performance
- Alt+3: System Control
- Alt+4: Settings

Actions:
- Ctrl+Shift+S: Emergency Stop
- Ctrl+Shift+N: Notifications
- Ctrl+Shift+D: Toggle Dark Mode
- Ctrl+K: Command palette (quick actions)

Global:
- Escape: Close modal/drawer
- /: Focus search
- ?: Show keyboard shortcuts help
```

**Keyboard Shortcuts Help Modal:**
```
┌──────────────────────────────────────────┐
│  ⌨️  Keyboard Shortcuts         [Close ×] │
├──────────────────────────────────────────┤
│                                           │
│  Navigation                               │
│  Alt+1        Dashboard                   │
│  Alt+2        Performance                 │
│  Alt+3        System Control              │
│  Alt+4        Settings                    │
│                                           │
│  Actions                                  │
│  Ctrl+Shift+S Emergency Stop              │
│  Ctrl+Shift+N Open Notifications          │
│  Ctrl+Shift+D Toggle Dark Mode            │
│  Ctrl+K       Command Palette             │
│                                           │
│  Global                                   │
│  Escape       Close Modal                 │
│  /            Focus Search                │
│  ?            Show This Help              │
│                                           │
│  Hint: Press ? anytime to see shortcuts  │
└──────────────────────────────────────────┘
```

**Screen Reader Support:**
- All images have descriptive `alt` text
- ARIA labels for icon buttons
- ARIA live regions for real-time updates
- Semantic HTML structure (headings, landmarks)
- Status announcements for important changes

**Visual Accessibility:**
- **Text Sizing**: User can adjust from 12px to 20px
- **Line Spacing**: Generous 1.5 line height minimum
- **Color Contrast**: WCAG AAA compliance (7:1 ratio for text)
- **Focus Indicators**: High visibility, never removed
- **Motion**: Respects `prefers-reduced-motion`

**Touch Targets:**
- Minimum 44x44px touch target size
- Adequate spacing between buttons
- Large tap areas for primary actions

#### 5.4 Accessibility Settings Panel
**Location:** Settings → Accessibility

**Settings Interface:**
```
┌──────────────────────────────────────────────┐
│  Accessibility Settings                      │
├──────────────────────────────────────────────┤
│                                               │
│  Visual                                       │
│  ☑ High contrast mode                        │
│  ☑ Reduce motion effects                     │
│  ☐ Large text (increase base font size)      │
│                                               │
│  Text Size:                                   │
│  Small  [─●─────────] Large                  │
│  Current: 16px                                │
│                                               │
│  Color Vision                                 │
│  ☐ Deuteranopia (red-green)                  │
│  ☐ Protanopia (red-green)                    │
│  ☐ Tritanopia (blue-yellow)                  │
│  ☐ Monochromacy (total color blindness)      │
│                                               │
│  Interaction                                  │
│  ☑ Keyboard shortcuts enabled                │
│  ☑ Show keyboard focus indicators            │
│  ☑ Enable command palette (Ctrl+K)           │
│                                               │
│  Audio                                        │
│  ☑ Sound effects enabled                     │
│  ☑ Screen reader announcements               │
│  ☐ Voice alerts for critical events          │
│                                               │
│  [ Test Settings ]      [ Reset to Defaults ]│
└──────────────────────────────────────────────┘
```

#### 5.5 Command Palette
**Trigger:** `Ctrl+K` or click search icon
**Purpose:** Quick access to all features and actions

**Command Palette Design:**
```
┌─────────────────────────────────────────────┐
│  🔍 Quick Actions                           │
│  ┌─────────────────────────────────────────┐│
│  │ Search commands...                      ││
│  └─────────────────────────────────────────┘│
│                                              │
│  Suggestions                                 │
│  ⚡ Emergency Stop                          │
│  📊 View Performance Dashboard              │
│  🔄 Refresh All Data                        │
│  ⚙️  Open Settings                           │
│  🌙 Toggle Dark Mode                        │
│                                              │
│  Recent                                      │
│  📈 View Trade History                      │
│  🤖 Agent Health Check                      │
│                                              │
│  Navigate with ↑↓, select with Enter        │
└─────────────────────────────────────────────┘
```

**Features:**
- Fuzzy search (finds "emer" for "emergency")
- Recent actions memory
- Contextual suggestions
- Keyboard-first interaction

### Success Metrics
- 100% WCAG 2.1 AA compliance (AAA for contrast)
- Keyboard navigation covers 100% of features
- Screen reader compatible (tested with JAWS, NVDA)
- Dark mode adoption >60% of users
- Zero accessibility-related support tickets

---

## 6. Mobile Responsiveness

### Overview
Create a fully responsive dashboard that works seamlessly on tablets and provides essential monitoring capabilities for on-the-go traders.

### User Goals
- Monitor system health from mobile devices
- View critical alerts immediately
- Execute emergency actions remotely
- Check position status and P&L

### Breakpoints

```
Mobile:   320px - 767px
Tablet:   768px - 1023px
Desktop:  1024px - 1439px
Wide:     1440px+
```

### Components

#### 6.1 Responsive Header
**Desktop (1024px+):**
```
┌─────────────────────────────────────────────────────────────┐
│ TMT Logo │ Dashboard │ Performance │ System │ Settings │ 🔔 │
└─────────────────────────────────────────────────────────────┘
```

**Tablet (768px - 1023px):**
```
┌──────────────────────────────────────────────────┐
│ TMT Logo │ Dashboard │ System │ ≡ Menu │ 🔔 │
└──────────────────────────────────────────────────┘
```

**Mobile (< 768px):**
```
┌────────────────────────────────┐
│ ≡ │ TMT Dashboard │ 🔔 │ 🛑 │
└────────────────────────────────┘
```

**Mobile Navigation:** Hamburger menu opens slide-out navigation drawer

#### 6.2 Mobile Navigation Drawer
**Trigger:** Tap hamburger icon
**Animation:** Slide from left, 250ms

**Drawer Design:**
```
┌─────────────────────────┐
│ [×]                     │
│                         │
│ 📊 Dashboard            │
│ 📈 Performance          │
│ 🤖 Agents               │
│ ⚙️  System Control       │
│ 📁 Trade History        │
│ ⚡ Emergency            │
│ ─────────────           │
│ 👤 Account              │
│ ⚙️  Settings             │
│ 🌙 Dark Mode            │
│ ─────────────           │
│ 📖 Help                 │
│ 🚪 Logout               │
│                         │
└─────────────────────────┘
```

#### 6.3 Responsive Dashboard Layout

**Desktop Layout (3-column grid):**
```
┌─────────────┬─────────────┬─────────────┐
│   Status    │   Status    │   Agents    │
│   Card 1    │   Card 2    │   Monitor   │
├─────────────┴─────────────┴─────────────┤
│                                          │
│         Position Cards Grid              │
│         (3 columns)                      │
│                                          │
├──────────────────────────────────────────┤
│              Performance Chart           │
└──────────────────────────────────────────┘
```

**Tablet Layout (2-column grid):**
```
┌─────────────┬─────────────┐
│   Status    │   Agents    │
│   Cards     │   Monitor   │
├─────────────┴─────────────┤
│   Position Cards Grid     │
│   (2 columns)             │
├───────────────────────────┤
│   Performance Chart       │
└───────────────────────────┘
```

**Mobile Layout (1-column stack):**
```
┌───────────────┐
│ System Status │
├───────────────┤
│ Quick Stats   │
├───────────────┤
│ Position 1    │
├───────────────┤
│ Position 2    │
├───────────────┤
│ Position 3    │
├───────────────┤
│ Performance   │
└───────────────┘
```

#### 6.4 Touch-Optimized Interactions

**Touch Targets:**
- Minimum size: 44x44px
- Spacing between targets: 8px minimum
- Large buttons for critical actions

**Gestures:**
- **Swipe left on position card:** Quick close position
- **Swipe right on notification:** Dismiss
- **Pull down on page:** Refresh data
- **Swipe from left edge:** Open navigation drawer

**Touch Feedback:**
- Visual ripple effect on tap
- Haptic feedback on critical actions (if supported)
- Loading indicators during actions

#### 6.5 Mobile-Specific Components

**Floating Action Button (FAB):**
```
Position: Bottom-right corner
Purpose: Quick access to critical actions

┌────────────┐
│            │
│            │
│            │
│         ┌──┤
│         │🛑││  ← Emergency stop
│         └──┤
│            │
└────────────┘
```

**Bottom Navigation Bar (Alternative):**
```
┌───────────────────────────────────┐
│  📊    │  📈    │  ⚡    │  ⚙️     │
│  Home  │  P&L   │  Alert │  More  │
└───────────────────────────────────┘
```

#### 6.6 Mobile Dashboard Widgets

**Compact System Status:**
```
┌──────────────────────────────┐
│ 🟢 System Healthy            │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━   │
│ 🤖 8/8 Agents  │  ⚡ 25ms   │
│ 💰 Today: +$1,245 (+1.25%)  │
└──────────────────────────────┘
```

**Compact Position Card:**
```
┌──────────────────────────────┐
│ EUR/USD BUY      [•••]       │
│ +$265.50 🟢      1.0872      │
│ SL: 1.0820  │  TP: 1.0920   │
│ ████████░░ 48% to TP         │
└──────────────────────────────┘
```

**Quick Actions Bar:**
```
┌──────────────────────────────┐
│ [📊 View] [✏️ Edit] [✕ Close] │
└──────────────────────────────┘
```

#### 6.7 Performance Optimizations

**Mobile-Specific:**
- Lazy load below-the-fold content
- Reduce animation complexity on mobile
- Lower refresh rates (10s instead of 1s)
- Compress images for mobile
- Use system fonts to reduce load time

**Progressive Web App (PWA) Features:**
- Install as app on home screen
- Offline mode (view cached data)
- Push notifications
- Background sync

### Responsive Behavior Rules

**Content Priority:**
1. Emergency controls - always visible
2. System health status - top of page
3. Open positions - immediate visibility
4. P&L summary - quick access
5. Detailed analytics - scroll/tab access

**Hidden on Mobile:**
- Detailed agent logs (link to full view)
- Advanced charts (simplified versions shown)
- Sidebar navigation (moved to drawer)
- Breadcrumbs (use back button instead)

**Simplified on Tablet:**
- 2-column grids instead of 3
- Compact form layouts
- Tabbed sections instead of side-by-side

### Success Metrics
- 100% features accessible on tablet
- Core monitoring functions work on mobile
- Touch target compliance: 100%
- Mobile page load time <3 seconds
- PWA install rate >20% of mobile users

---

## 7. Agent Intelligence Insights

### Overview
Provide transparency into AI agent decision-making, confidence levels, and disagreement patterns to help traders understand and trust the system.

### User Goals
- Understand why agents made specific decisions
- See when agents disagree and their reasoning
- Monitor agent performance and confidence
- Identify patterns in agent behavior

### Components

#### 7.1 Agent Disagreement Visualization
**Location:** Dedicated "Agent Intelligence" page
**Purpose:** Show when agents disagree on signals

**Disagreement Dashboard:**
```
┌────────────────────────────────────────────────────────┐
│  🤖 Agent Disagreement Analysis            [Live View] │
├────────────────────────────────────────────────────────┤
│                                                         │
│  Current Signal: EUR/USD                                │
│  Timestamp: 2025-09-28 17:42:15 UTC                    │
│                                                         │
│  Consensus: WEAK BUY (5/8 agree)                       │
│  ━━━━━━━━━━░░░░░░  62.5% agreement                     │
│                                                         │
│  Agent Positions:                                       │
│                                                         │
│  🟢 BUY (5 agents)                                      │
│  ├─ Market Analysis       85% confidence               │
│  │   "Strong uptrend, key support holding"             │
│  │                                                      │
│  ├─ Pattern Detection     78% confidence               │
│  │   "Wyckoff accumulation pattern detected"           │
│  │                                                      │
│  ├─ Strategy Analysis     72% confidence               │
│  │   "Aligns with London session strategy"             │
│  │                                                      │
│  ├─ Parameter Optimization 68% confidence              │
│  │   "Risk/reward ratio favorable: 3.2:1"              │
│  │                                                      │
│  └─ Continuous Improvement 65% confidence              │
│      "Recent similar patterns 75% win rate"            │
│                                                         │
│  🔴 SELL (2 agents)                                     │
│  ├─ Disagreement Engine   58% confidence               │
│  │   "Overbought on RSI, divergence on MACD"           │
│  │                                                      │
│  └─ Learning Safety       52% confidence               │
│      "Market volatility above threshold"               │
│                                                         │
│  ⚪ NEUTRAL (1 agent)                                   │
│  └─ Data Collection       N/A                          │
│      "Insufficient data for confident signal"          │
│                                                         │
│  ────────────────────────────────────────              │
│                                                         │
│  Final Decision: HOLD                                  │
│  Reason: Insufficient consensus (62.5% < 70% threshold)│
│                                                         │
│  [ View Detailed Analysis ] [ Export Report ]          │
└────────────────────────────────────────────────────────┘
```

#### 7.2 Confidence Meters
**Location:** Signal cards, agent dashboard
**Purpose:** Visual representation of agent confidence

**Confidence Meter Design:**
```
┌─────────────────────────────────┐
│  Market Analysis                │
│  ━━━━━━━━━━━━━━━━━░░░  85%     │
│  Very High Confidence           │
└─────────────────────────────────┘

Confidence Levels:
90-100%: ━━━━━━━━━━━━━━━━━━━━  Very High (Dark Green)
70-89%:  ━━━━━━━━━━━━━━░░░░░░  High (Green)
50-69%:  ━━━━━━━━░░░░░░░░░░░░  Medium (Yellow)
30-49%:  ━━━░░░░░░░░░░░░░░░░░  Low (Orange)
0-29%:   ░░░░░░░░░░░░░░░░░░░░  Very Low (Red)
```

#### 7.3 Agent Decision History
**Location:** Trade detail modal, agent page
**Purpose:** Show agent reasoning for past trades

**Decision History Card:**
```
┌──────────────────────────────────────────────────┐
│  Trade #1523: EUR/USD BUY                        │
│  Opened: 2025-09-28 14:30:15 UTC                │
│  Result: +$445.00 (+4.1%) ✅                    │
├──────────────────────────────────────────────────┤
│                                                   │
│  Agent Signals:                                   │
│                                                   │
│  🎯 Pattern Detection (PRIMARY)                   │
│  Confidence: 82%                                  │
│  Pattern: Wyckoff Accumulation Phase C           │
│  Reasoning:                                       │
│  • Spring detected at 1.0820 support             │
│  • Volume increasing on upward moves             │
│  • Sign of Strength (SOS) confirmed              │
│  • Entry: 1.0845 (after successful test)         │
│                                                   │
│  ✅ Market Analysis (CONFIRMING)                  │
│  Confidence: 75%                                  │
│  Trend: Bullish momentum building                │
│  • Daily: Uptrend, above 20/50 EMA               │
│  • 4H: Higher highs, higher lows                 │
│  • Key resistance: 1.0920                        │
│                                                   │
│  ✅ Strategy Analysis (CONFIRMING)                │
│  Confidence: 71%                                  │
│  Session: London (optimal for EUR/USD)           │
│  • London session = 72% win rate EUR/USD         │
│  • Spread conditions optimal (1.2 pips)          │
│  • Liquidity high, execution reliable            │
│                                                   │
│  ⚠️ Risk Management                               │
│  Position size: 10,000 units (1% risk)           │
│  Stop loss: 1.0820 (-25 pips / -$25)            │
│  Take profit: 1.0920 (+75 pips / +$75)          │
│  Risk:Reward ratio: 1:3                          │
│                                                   │
│  Outcome:                                         │
│  ✅ Take profit hit at 1.0918 (close enough)     │
│  Duration: 3h 45m                                │
│  Profit: +$445.00 (+4.1%)                        │
│                                                   │
│  [ View Full Analysis ] [ Similar Patterns ]     │
└──────────────────────────────────────────────────┘
```

#### 7.4 Pattern Detection Overlay
**Location:** Price charts on trade execution page
**Purpose:** Visual overlay showing detected patterns

**Chart Annotation Example:**
```
┌────────────────────────────────────────────┐
│  EUR/USD 4H Chart                          │
│                                            │
│  1.0920 ┤           ╭───○ TP Target       │
│         │         ╭─╯                      │
│  1.0845 ├───●───○  ← BUY Entry           │
│         │   │   │                          │
│  1.0820 ┤   ╰───╯ Spring ✓               │
│         │       └─ SOS ✓                  │
│         │                                  │
│         └──────────────────────────        │
│                                            │
│  🎯 Wyckoff Accumulation                  │
│  Phase C → Phase D transition             │
│  Confidence: 82%                          │
│                                            │
│  Key Levels:                              │
│  • Support: 1.0820 (tested 3x) ✓         │
│  • Resistance: 1.0920 (volume pocket)     │
│  • Entry: 1.0845 (after spring test)      │
└────────────────────────────────────────────┘
```

**Pattern Annotations:**
- ● Entry point
- ○ Target levels
- ╰─╯ Support/resistance zones
- ✓ Confirmed signals
- ⚠ Warning areas

#### 7.5 Agent Performance Comparison
**Location:** Agent Intelligence page
**Purpose:** Compare individual agent performance

**Comparison Dashboard:**
```
┌──────────────────────────────────────────────────────────┐
│  🏆 Agent Performance Comparison (Last 30 Days)          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Agent               Win Rate   Avg Profit   Signals     │
│  ────────────────────────────────────────────────────    │
│  Pattern Detection    87%      $245         45  🥇       │
│  Market Analysis      82%      $223         52  🥈       │
│  Strategy Analysis    79%      $198         41  🥉       │
│  Parameter Opt.       76%      $189         38           │
│  Learning Safety      74%      $167         29           │
│  Continuous Improv.   71%      $156         35           │
│  Disagreement Eng.    68%      $145         23           │
│  Data Collection      N/A      N/A          N/A          │
│                                                           │
│  Combined System:     83%      $212         263          │
│                                                           │
│  ────────────────────────────────────────────────────    │
│                                                           │
│  Best Performing Pairs:                                   │
│  • Pattern Detection: EUR/USD (92% win rate)              │
│  • Market Analysis: GBP/USD (88% win rate)                │
│  • Strategy Analysis: USD/JPY (85% win rate)              │
│                                                           │
│  [ View Detailed Breakdown ] [ Export Report ]           │
└──────────────────────────────────────────────────────────┘
```

#### 7.6 Real-Time Agent Activity Feed
**Location:** Dashboard sidebar or dedicated page
**Purpose:** Live feed of agent decisions and reasoning

**Activity Feed Design:**
```
┌────────────────────────────────────────┐
│  🤖 Agent Activity Feed       [Live]   │
├────────────────────────────────────────┤
│                                         │
│  Just now                               │
│  🎯 Pattern Detection                   │
│  Analyzing EUR/USD...                  │
│  Wyckoff pattern detected (85%)        │
│  Recommending BUY entry at 1.0845      │
│  ───────────────────────────────       │
│                                         │
│  2 seconds ago                          │
│  📊 Market Analysis                     │
│  Trend analysis complete               │
│  Bullish momentum confirmed (78%)       │
│  Supporting BUY recommendation         │
│  ───────────────────────────────       │
│                                         │
│  5 seconds ago                          │
│  ⚠️ Disagreement Engine                │
│  Flagging potential divergence         │
│  RSI overbought, suggesting caution    │
│  Confidence: 58%                       │
│  ───────────────────────────────       │
│                                         │
│  8 seconds ago                          │
│  ✅ Final Decision                      │
│  Signal: HOLD (consensus not reached)  │
│  5/8 agents favored BUY (62.5%)        │
│  Threshold: 70% required               │
│  ───────────────────────────────       │
│                                         │
│  [ Pause ] [ Filter Agents ]           │
└────────────────────────────────────────┘
```

### Success Metrics
- Users understand agent reasoning >90% of time
- Disagreement analysis used before manual overrides 80%+
- Trust in automated decisions increases by 25%
- Confidence meter clarity rated >4.5/5

---

## 8. Performance Analytics

### Overview
Provide comprehensive performance analytics including Sharpe ratio monitoring, Monte Carlo projections, and forward test vs. backtest comparisons.

### User Goals
- Track risk-adjusted returns (Sharpe ratio)
- Compare actual performance to projections
- Identify performance degradation early
- Make data-driven decisions about strategy changes

### Components

#### 8.1 Sharpe Ratio Dashboard
**Location:** Performance Analytics page, top section
**Purpose:** Monitor risk-adjusted performance

**Sharpe Ratio Widget:**
```
┌──────────────────────────────────────────────────┐
│  📊 Sharpe Ratio Monitoring                      │
├──────────────────────────────────────────────────┤
│                                                   │
│  Current 30-Day Sharpe Ratio                     │
│           ┌───────┐                              │
│       ┌───┤  1.67 ├───┐                          │
│   ┌───┤   └───────┘   ├───┐                      │
│   │ 0.0              3.0  │                       │
│   └───────────────────────┘                       │
│                                                   │
│  ⭐ Excellent (Target: >1.5)                     │
│                                                   │
│  Rolling Windows:                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━         │
│  7-Day:   1.89  ▲ +0.22  🟢 Improving           │
│  14-Day:  1.73  ▲ +0.06  🟢 Stable              │
│  30-Day:  1.67  ━ ±0.00  🟡 Target Met          │
│  90-Day:  1.54  ▼ -0.13  🟡 Near Target         │
│                                                   │
│  Historical Trend (Last 90 Days):                │
│  2.0 ┤     ╭──╮                                  │
│      │   ╭─╯  ╰─╮  ╭─╮                          │
│  1.5 ├──╯       ╰─╯ ╰──────                      │
│      │                                            │
│  1.0 ┤                                           │
│      └────────────────────────────                │
│      30d    60d    90d                           │
│                                                   │
│  Interpretation:                                  │
│  Your 30-day Sharpe ratio of 1.67 indicates     │
│  excellent risk-adjusted returns. The strategy   │
│  generates strong returns relative to volatility.│
│                                                   │
│  [ View Detailed Analysis ] [ Set Alert ]        │
└──────────────────────────────────────────────────┘
```

**Sharpe Ratio Thresholds:**
- **>2.0**: Outstanding (Dark Green)
- **1.5-2.0**: Excellent (Green)
- **1.0-1.5**: Good (Light Green)
- **0.5-1.0**: Acceptable (Yellow)
- **<0.5**: Poor (Red)

#### 8.2 Monte Carlo Projection Overlay
**Location:** Performance Analytics page
**Purpose:** Compare actual performance to statistical projections

**Monte Carlo Dashboard:**
```
┌──────────────────────────────────────────────────────────┐
│  🎲 Monte Carlo Projection vs. Actual Performance        │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  6-Month Forward Test Progress                           │
│  Day 28 of 180 (15.6% complete)                         │
│                                                           │
│  Current P&L: $12,450                                    │
│  Expected P&L: $79,563 (at 6 months)                    │
│  Daily Expected: $442.02                                 │
│                                                           │
│  Confidence Intervals:                                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │                                                  │    │
│  │ $100K ┤           ╱╲  99% Upper                │    │
│  │       │         ╱    ╲                          │    │
│  │  $80K ├───────╱──────╲────── 95% Upper        │    │
│  │       │   ╱──────────────╲                     │    │
│  │  $60K ├─╱─Expected────────╲── Mean Projection │    │
│  │       │╱         ●          ╲                   │    │
│  │  $40K ├──────────┼───────────╲── 95% Lower    │    │
│  │       │          │             ╲                │    │
│  │  $20K ┤          │              ╲─── 99% Lower │    │
│  │       │          │                              │    │
│  │    $0 ├──────────┴──────────────────────       │    │
│  │       0d       30d      90d     180d            │    │
│  │                 ↑                                │    │
│  │             Today                                │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  Performance Status: ✅ Within 95% Confidence Interval  │
│  Actual: $12,450 vs Expected: $13,286 ± $2,100          │
│  Variance: -6.3% (within normal range)                   │
│                                                           │
│  Key Metrics:                                            │
│  • Walk-Forward Stability: 34.4 (Target: >30) ✓         │
│  • Overfitting Score: 0.634 (Target: <0.8) ✓           │
│  • Out-of-Sample Validation: 78.5% (Target: >70%) ✓     │
│                                                           │
│  Alerts:                                                  │
│  ⚠️ Performance below expected for 2 consecutive days    │
│     Current: -6.3% | Threshold: -10%                     │
│                                                           │
│  [ View Full Projection Report ] [ Adjust Parameters ]   │
└──────────────────────────────────────────────────────────┘
```

#### 8.3 Forward Test vs. Backtest Comparison
**Location:** Performance Analytics page
**Purpose:** Validate strategy performance against historical testing

**Comparison Dashboard:**
```
┌──────────────────────────────────────────────────────────┐
│  📈 Forward Test vs. Backtest Comparison                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Metric Comparison                                        │
│  ─────────────────────────────────────────────────       │
│  Metric              Backtest   Forward    Variance      │
│  ───────────────────────────────────────────────────     │
│  Win Rate            83.2%      87.0%      +4.6% ✅      │
│  Avg Win             $250       $245       -2.0% ✓       │
│  Avg Loss            -$165      -$158      +4.2% ✅      │
│  Profit Factor       2.45       2.52       +2.9% ✅      │
│  Max Drawdown        $2,450     $1,890     +22.9% ✅     │
│  Sharpe Ratio        1.54       1.67       +8.4% ✅      │
│  Recovery Factor     3.2        4.1        +28.1% ✅     │
│  ───────────────────────────────────────────────────     │
│                                                           │
│  ✅ Forward test outperforming backtest expectations     │
│                                                           │
│  Performance Stability Analysis:                          │
│  ┌───────────────────────────────────────────────┐      │
│  │                                                │      │
│  │  Cumulative Returns Comparison                │      │
│  │  ┌─────────────────────────────────────────┐  │      │
│  │  │ $80K ┤       ┌──── Forward (Live) ──●   │  │      │
│  │  │      │     ┌─┘                          │  │      │
│  │  │ $60K ├────╯                             │  │      │
│  │  │      │   ╱                               │  │      │
│  │  │ $40K ├──╯                                │  │      │
│  │  │      │ ╱ ─── Backtest (Historical)      │  │      │
│  │  │ $20K ├╯                                  │  │      │
│  │  │      │                                    │  │      │
│  │  │   $0 └────────────────────────────       │  │      │
│  │  │      0d    30d    60d    90d    120d    │  │      │
│  │  └─────────────────────────────────────────┘  │      │
│  │                                                │      │
│  └───────────────────────────────────────────────┘      │
│                                                           │
│  Observations:                                            │
│  ✅ Forward test tracking above backtest projections     │
│  ✅ Lower drawdown than historical testing               │
│  ✅ Improved win rate and Sharpe ratio                   │
│  ⚠️ Monitor: Slightly lower avg win (within variance)    │
│                                                           │
│  Overfitting Analysis:                                    │
│  Score: 0.634 (Low overfitting risk) ✅                  │
│  • In-sample performance: 85.2%                          │
│  • Out-of-sample performance: 78.5%                      │
│  • Degradation: 6.7% (acceptable, <15% threshold)        │
│                                                           │
│  [ Export Comparison Report ] [ View Detailed Stats ]    │
└──────────────────────────────────────────────────────────┘
```

#### 8.4 Performance Degradation Alerts
**Location:** Performance Analytics page, alert panel
**Purpose:** Early warning system for strategy degradation

**Alert Dashboard:**
```
┌──────────────────────────────────────────────────┐
│  🚨 Performance Alerts                           │
├──────────────────────────────────────────────────┤
│                                                   │
│  Active Alerts (1):                               │
│                                                   │
│  ⚠️ MEDIUM PRIORITY · 2h ago                     │
│  ┌────────────────────────────────────────────┐ │
│  │ Performance Deviation Detected              │ │
│  │                                             │ │
│  │ Current P&L: $12,450                       │ │
│  │ Expected P&L: $13,286 ± $2,100             │ │
│  │ Variance: -6.3%                            │ │
│  │                                             │ │
│  │ Status: WITHIN TOLERANCE                   │ │
│  │ (Alert threshold: -10%)                    │ │
│  │                                             │ │
│  │ Trend: Performance below expected for      │ │
│  │ 2 consecutive days. Monitoring closely.    │ │
│  │                                             │ │
│  │ [ View Details ] [ Acknowledge ]           │ │
│  └────────────────────────────────────────────┘ │
│                                                   │
│  Monitoring Thresholds:                          │
│  ☑ Performance decline > 10%                     │
│  ☑ Confidence interval breach (2+ days)          │
│  ☑ Overfitting score > 0.8                      │
│  ☑ Walk-forward stability < 30                   │
│  ☑ Sharpe ratio drop > 20%                      │
│  ☑ Win rate decline > 15%                       │
│                                                   │
│  Recent History (Last 30 Days):                  │
│  • 3 alerts triggered (all resolved)            │
│  • Avg time to resolution: 6 hours              │
│  • No emergency rollbacks required              │
│                                                   │
│  [ Configure Thresholds ] [ Alert History ]     │
└──────────────────────────────────────────────────┘
```

**Alert Severity Levels:**
- 🔴 **Critical**: Immediate action required (auto-rollback trigger)
- 🟠 **High**: Attention needed within 24 hours
- 🟡 **Medium**: Monitor closely, investigate if persists
- 🔵 **Low**: Informational, no action needed

#### 8.5 Risk-Adjusted Metrics Dashboard
**Location:** Performance Analytics page
**Purpose:** Comprehensive risk analysis

**Risk Metrics Widget:**
```
┌──────────────────────────────────────────────────┐
│  📊 Risk-Adjusted Performance Metrics            │
├──────────────────────────────────────────────────┤
│                                                   │
│  Sharpe Ratio:        1.67  ⭐ Excellent         │
│  Sortino Ratio:       2.34  ⭐ Excellent         │
│  Calmar Ratio:        4.12  ⭐ Outstanding       │
│                                                   │
│  ───────────────────────────────────────────     │
│                                                   │
│  Drawdown Analysis:                               │
│  Max Drawdown:        $1,890  (1.89%)            │
│  Avg Drawdown:        $452    (0.45%)            │
│  Recovery Time:       12 hours avg               │
│                                                   │
│  Drawdown Distribution:                           │
│  ████████████████████░░ 0-1%:  85% of days       │
│  ████░░░░░░░░░░░░░░░░░ 1-2%:  12% of days       │
│  █░░░░░░░░░░░░░░░░░░░░ 2-3%:   3% of days       │
│  ░░░░░░░░░░░░░░░░░░░░░ >3%:    0% of days       │
│                                                   │
│  ───────────────────────────────────────────     │
│                                                   │
│  Volatility Metrics:                              │
│  Daily Volatility:    0.8%                       │
│  Monthly Volatility:  3.2%                       │
│  Volatility Trend:    ▼ Decreasing (good)       │
│                                                   │
│  ───────────────────────────────────────────     │
│                                                   │
│  Risk/Reward Profile:                             │
│  Avg R:R Ratio:       3.2:1                      │
│  Win Ratio:           87%                        │
│  Expectancy:          $212 per trade             │
│                                                   │
│  [ View Detailed Risk Report ] [ Export Data ]   │
└──────────────────────────────────────────────────┘
```

### Success Metrics
- Performance tracking reduces detection time by 70%
- Early warning alerts catch degradation 90%+ of time
- Risk-adjusted metrics inform 80% of strategy adjustments
- User confidence in performance data >4.7/5

---

## 9. Loading States & Error Handling

### Overview
Implement comprehensive loading states, skeleton screens, and graceful error handling to maintain user confidence during failures and data fetching.

### User Goals
- Understand system is working during operations
- See meaningful feedback during waits
- Recover gracefully from errors
- Never lose context or data due to failures

### Components

#### 9.1 Skeleton Screens
**Purpose:** Show content structure while loading
**Benefit:** Perceived performance improvement

**Dashboard Skeleton:**
```
┌────────────────────────────────────────────────┐
│  ░░░░░░░░░░░░  Dashboard Loading...            │
├────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┬─────────────┬─────────────┐  │
│  │ ░░░░░░░░░░  │ ░░░░░░░░░░  │ ░░░░░░░░░░  │  │
│  │ ░░░░░       │ ░░░░░       │ ░░░░░       │  │
│  │             │             │             │  │
│  │ ░░░░░░░░    │ ░░░░░░░░    │ ░░░░░░░░    │  │
│  │ ░░░░        │ ░░░░        │ ░░░░        │  │
│  └─────────────┴─────────────┴─────────────┘  │
│                                                 │
│  ┌─────────────┬─────────────┐                │
│  │ ░░░░░░░░░░  │ ░░░░░░░░░░  │                │
│  │ ░░░░░░░░    │ ░░░░░░░░    │                │
│  │             │             │                │
│  │ ░░░░░░      │ ░░░░░░      │                │
│  │ ░░░        │ ░░░        │                │
│  └─────────────┴─────────────┘                │
│                                                 │
└────────────────────────────────────────────────┘
```

**Skeleton Animation:** Subtle shimmer effect (left to right gradient)

**Position Card Skeleton:**
```
┌──────────────────────────────────┐
│  ░░░░░░░░ • ░░░░       [•••]    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│  ░░░░░░░░ ░░░░░░                │
├──────────────────────────────────┤
│  ░░░░░░    ░░░░░░                │
│  ░░░░░░    ░░░░░░                │
│  ░░░░░░    ░░░░░░                │
│  ░░░░░░    ░░░░░░                │
│  ──────────────────────────       │
│  ░░░░░░░░░░░░░░░░  ░░% to target │
│  ──────────────────────────       │
│  ░░░░░░░░░░ • ░░░░░░░░░░          │
└──────────────────────────────────┘
```

#### 9.2 Loading Indicators

**Inline Spinner (Small components):**
```
⟳  Loading...
```

**Modal Overlay (Full page operations):**
```
┌─────────────────────────────────┐
│                                  │
│                                  │
│         ⟳                        │
│    Processing...                │
│                                  │
│  Please wait while we execute   │
│  your emergency stop request.   │
│                                  │
│                                  │
└─────────────────────────────────┘
```

**Progress Bar (Known duration operations):**
```
┌─────────────────────────────────┐
│  Closing positions...            │
│  ████████████░░░░░░  60%        │
│  2 of 3 positions closed         │
└─────────────────────────────────┘
```

**Button Loading States:**
```
Before:  [ Close Position ]
During:  [ ⟳ Closing... ]  ← Disabled, spinner
After:   [ ✓ Closed ]      ← Brief success state
```

#### 9.3 Error States

**Error Message Design Principles:**
1. Explain what happened (clearly, no jargon)
2. Explain why it matters (impact)
3. Provide next steps (actionable)
4. Offer recovery options (retry, support)

**Component Error (Inline):**
```
┌────────────────────────────────────────┐
│  ⚠️ Unable to Load Positions           │
│  ───────────────────────────────       │
│  We couldn't retrieve your open        │
│  positions from OANDA. Your trades     │
│  are safe, but we can't display        │
│  them right now.                       │
│                                         │
│  [ Try Again ] [ View System Health ]  │
└────────────────────────────────────────┘
```

**Critical Error (Full page):**
```
┌────────────────────────────────────────────┐
│                                             │
│                   ⚠️                        │
│                                             │
│          Connection Lost                    │
│                                             │
│  We've lost connection to the trading      │
│  system. This could affect your ability    │
│  to monitor and control trades.            │
│                                             │
│  What's happening:                          │
│  • Dashboard will attempt to reconnect     │
│  • Trading system continues operating      │
│  • Existing positions are maintained       │
│                                             │
│  What you can do:                           │
│  • Wait for automatic reconnection (15s)   │
│  • Refresh the page manually               │
│  • Check your internet connection          │
│                                             │
│  Reconnecting in 12 seconds...             │
│  [━━━━━━━━░░░░░░░░░░░░]                    │
│                                             │
│  [ Refresh Now ] [ Emergency Contact ]     │
│                                             │
└────────────────────────────────────────────┘
```

**Form Validation Error:**
```
┌────────────────────────────────────┐
│  Stop Loss                          │
│  ┌──────────────────────────────┐  │
│  │ 1.0850                       │  │
│  └──────────────────────────────┘  │
│  ⚠️ Stop loss must be below entry │
│  Your entry: 1.0845               │
│  Your SL: 1.0850 (5 pips above)   │
│  Suggestion: Try 1.0820           │
└────────────────────────────────────┘
```

#### 9.4 Empty States

**No Data (Informative):**
```
┌────────────────────────────────────┐
│                                     │
│            📭                       │
│                                     │
│      No Open Positions              │
│                                     │
│  You don't have any open trades    │
│  at the moment.                    │
│                                     │
│  New positions will appear here    │
│  when agents generate signals.     │
│                                     │
│  [ View Trade History ]            │
│                                     │
└────────────────────────────────────┘
```

**No Results (Filtered):**
```
┌────────────────────────────────────┐
│            🔍                       │
│                                     │
│    No Results Found                 │
│                                     │
│  No trades match your filters:     │
│  • Instrument: EUR/USD              │
│  • Status: Open                     │
│  • Date: Last 7 days                │
│                                     │
│  [ Clear Filters ] [ Try Different ]│
└────────────────────────────────────┘
```

#### 9.5 Graceful Degradation

**Agent Offline (Degraded):**
```
┌──────────────────────────────────┐
│  🤖 Market Analysis      [•••]   │
│  🔴 Offline · 5m ago             │
│  ─────────────────────────────   │
│  This agent is temporarily       │
│  unavailable. Trading continues  │
│  using other agents.             │
│                                   │
│  Last Signal: 15m ago ✓          │
│  Status: Non-critical            │
│                                   │
│  [ Reconnect ] [ View Logs ]     │
└──────────────────────────────────┘
```

**WebSocket Fallback:**
```
┌────────────────────────────────────┐
│  ℹ️ Real-time Updates Unavailable  │
│  ─────────────────────────────     │
│  Using slower polling updates      │
│  (refresh every 5 seconds)         │
│                                     │
│  [ Try Reconnecting ]              │
└────────────────────────────────────┘
```

#### 9.6 Optimistic UI Updates

**Immediate Feedback (before server response):**

**Trade Close Request:**
```
Step 1: User clicks "Close Position"
┌──────────────────────────────┐
│  EUR/USD • BUY               │
│  [ ⟳ Closing... ]            │  ← Immediate feedback
└──────────────────────────────┘

Step 2: Server confirms (500ms later)
┌──────────────────────────────┐
│  EUR/USD • BUY               │
│  [ ✓ Closed ]                │  ← Success confirmation
└──────────────────────────────┘

Step 3: Card removed (1s after success)
Card fades out and removes from UI
```

**Error Recovery (if server fails):**
```
┌──────────────────────────────┐
│  EUR/USD • BUY               │
│  [ ✗ Close Failed ]          │  ← Revert to original state
│  ⚠️ Couldn't close position  │
│  [ Try Again ]               │
└──────────────────────────────┘
```

#### 9.7 Retry Logic

**Automatic Retry (Background):**
- Failed API calls: 3 retries with exponential backoff
- WebSocket reconnection: Automatic with increasing intervals
- User-visible retries: Manual retry button

**Manual Retry Button:**
```
┌────────────────────────────────────┐
│  ⚠️ Load Failed                    │
│  Unable to fetch trade history     │
│                                     │
│  [ ↻ Try Again ] [ Report Issue ]  │
│                                     │
│  Attempt 1 of 3                    │
└────────────────────────────────────┘
```

### Success Metrics
- Perceived load time reduced by 40% (skeleton screens)
- Error recovery rate >85% (user can resolve)
- <2% of users abandon after error
- Error message clarity rated >4.5/5

---

## 10. Customization & Preferences

### Overview
Enable traders to customize their workspace, create saved layouts, adjust dashboard configurations, and set personalized alert thresholds.

### User Goals
- Arrange dashboard to match workflow
- Save different layouts for different tasks
- Customize alerts and notifications
- Adjust visual preferences

### Components

#### 10.1 Widget System
**Purpose:** Draggable, resizable dashboard widgets
**Technology:** React Grid Layout or similar

**Widget Grid System:**
```
Grid: 12 columns × Flexible rows
Widget sizes: 1x1, 2x1, 2x2, 3x2, 4x2, 6x2, 12x1, etc.
Responsive: Auto-adjust on smaller screens
```

**Edit Mode Toggle:**
```
┌────────────────────────────────────────┐
│  Dashboard             [ Edit Layout ] │  ← Toggle edit mode
└────────────────────────────────────────┘

Edit Mode Active:
┌────────────────────────────────────────┐
│  Dashboard    [ ✓ Save ]  [ ✗ Cancel ] │
│                                         │
│  Drag widgets to rearrange             │
│  Resize handles appear on corners      │
└────────────────────────────────────────┘
```

**Widget Controls (Edit Mode):**
```
┌──────────────────────────────────┐
│ ⋮⋮ System Status        [×] [−]  │  ← Drag handle, remove, minimize
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  🟢 All Systems Healthy          │
│  8/8 Agents Active               │
│                                   │
│  ⇲ Resize handle                 │  ← Bottom-right corner
└──────────────────────────────────┘
```

#### 10.2 Layout Presets
**Location:** Layout dropdown in header
**Purpose:** Quick switching between saved configurations

**Preset Selector:**
```
┌────────────────────────────────────┐
│  Layout: [Default ▾]               │
├────────────────────────────────────┤
│  ✓ Default                         │
│    Trading Focus                   │
│    Analysis View                   │
│    Monitoring Only                 │
│    Mobile Compact                  │
│  ──────────────────────            │
│  + Create New Layout               │
│    Manage Layouts...               │
└────────────────────────────────────┘
```

**Preset Descriptions:**

**1. Default Layout:**
- Balanced view of all features
- 3-column grid with status, positions, performance

**2. Trading Focus:**
- Large position cards
- Quick access to emergency controls
- Live P&L prominent
- Charts maximized

**3. Analysis View:**
- Large charts and analytics
- Agent intelligence visible
- Performance metrics emphasized
- Trade history accessible

**4. Monitoring Only:**
- Minimal interface
- System health focus
- Alert center prominent
- Compact positions list

**5. Mobile Compact:**
- Single column layout
- Most critical info only
- Large touch targets

#### 10.3 Widget Library
**Location:** "Add Widget" button in edit mode
**Purpose:** Choose which widgets to display

**Widget Picker:**
```
┌──────────────────────────────────────┐
│  Add Widget to Dashboard             │
├──────────────────────────────────────┤
│                                       │
│  Status & Monitoring                  │
│  ☐ System Health Status              │
│  ☑ Agent Monitor                     │
│  ☐ Connection Status                 │
│  ☐ Circuit Breakers                  │
│                                       │
│  Trading                              │
│  ☑ Position Cards Grid               │
│  ☐ Live P&L Ticker                   │
│  ☑ Session Performance               │
│  ☐ Quick Trade Actions               │
│                                       │
│  Analytics                            │
│  ☐ Sharpe Ratio Dashboard            │
│  ☑ Performance Chart                 │
│  ☐ Monte Carlo Projections           │
│  ☐ Risk Metrics                      │
│                                       │
│  Intelligence                         │
│  ☐ Agent Disagreement                │
│  ☐ Pattern Detection                 │
│  ☐ Confidence Meters                 │
│  ☐ Activity Feed                     │
│                                       │
│  [ Add Selected Widgets ]            │
└──────────────────────────────────────┘
```

#### 10.4 Customizable Alert Thresholds
**Location:** Settings → Alerts & Thresholds
**Purpose:** Personalize when alerts trigger

**Threshold Configuration:**
```
┌──────────────────────────────────────────────┐
│  Alert Thresholds                            │
├──────────────────────────────────────────────┤
│                                               │
│  P&L Alerts                                   │
│  Daily Loss Alert:                            │
│  Trigger at: [$_____] or [___%] loss        │
│  Current: $500 / 0.5%                        │
│                                               │
│  Daily Profit Alert:                          │
│  Trigger at: [$_____] profit                 │
│  Current: $1,000                             │
│                                               │
│  Position Alerts                              │
│  Position approaching stop loss:              │
│  Alert when within [___] pips                │
│  Current: 10 pips                            │
│                                               │
│  Position approaching take profit:            │
│  Alert when within [___] pips                │
│  Current: 15 pips                            │
│                                               │
│  System Health Alerts                         │
│  Agent latency threshold:                     │
│  Alert when latency exceeds [___] ms         │
│  Current: 200ms                              │
│                                               │
│  Connection timeout:                          │
│  Alert after [___] seconds offline           │
│  Current: 30 seconds                         │
│                                               │
│  Circuit Breaker Alerts                       │
│  Daily loss approaching limit:                │
│  Warn at [___%] of limit                     │
│  Current: 80%                                │
│                                               │
│  [ Reset to Defaults ]      [ Save Changes ] │
└──────────────────────────────────────────────┘
```

#### 10.5 Visual Customization
**Location:** Settings → Appearance
**Purpose:** Adjust colors, density, animations

**Appearance Settings:**
```
┌──────────────────────────────────────────────┐
│  Appearance Settings                         │
├──────────────────────────────────────────────┤
│                                               │
│  Theme                                        │
│  ◉ Light    ○ Dark    ○ Auto                │
│  ☐ High contrast mode                        │
│                                               │
│  Color Accents                                │
│  Primary: [████] Blue  ▾                     │
│  Success: [████] Green ▾                     │
│  Warning: [████] Orange ▾                    │
│  Error:   [████] Red   ▾                     │
│                                               │
│  Density                                      │
│  ○ Compact    ◉ Comfortable    ○ Spacious   │
│                                               │
│  Font Size                                    │
│  Small  [──●────] Large                      │
│  Current: 16px                               │
│                                               │
│  Animations                                   │
│  ☑ Enable smooth transitions                 │
│  ☑ Chart animations                          │
│  ☐ Reduce motion (accessibility)             │
│                                               │
│  Data Display                                 │
│  Number format: [1,234.56] ▾                 │
│  Currency symbol: [$] ▾                      │
│  Date format: [MM/DD/YYYY] ▾                 │
│  Time format: [12-hour] ▾                    │
│  Timezone: [GMT] ▾                           │
│                                               │
│  [ Preview Changes ]       [ Save Settings ] │
└──────────────────────────────────────────────┘
```

#### 10.6 Workspace Export/Import
**Location:** Settings → Layouts
**Purpose:** Backup and share configurations

**Export/Import Interface:**
```
┌──────────────────────────────────────────────┐
│  Layout Management                           │
├──────────────────────────────────────────────┤
│                                               │
│  Saved Layouts:                               │
│                                               │
│  ┌──────────────────────────────────────┐   │
│  │ Default Layout                        │   │
│  │ Last modified: 2025-09-28            │   │
│  │ Widgets: 8 | Columns: 3              │   │
│  │ [ Edit ] [ Export ] [ Duplicate ]    │   │
│  └──────────────────────────────────────┘   │
│                                               │
│  ┌──────────────────────────────────────┐   │
│  │ Trading Focus                         │   │
│  │ Last modified: 2025-09-25            │   │
│  │ Widgets: 6 | Columns: 2              │   │
│  │ [ Edit ] [ Export ] [ Delete ]       │   │
│  └──────────────────────────────────────┘   │
│                                               │
│  Actions:                                     │
│  [ + New Layout ]                            │
│  [ 📥 Import Layout ]                        │
│  [ 📦 Export All Layouts ]                   │
│                                               │
│  Import Layout File:                          │
│  ┌──────────────────────────────────────┐   │
│  │ Drop .layout file here or click      │   │
│  │ [Browse Files]                        │   │
│  └──────────────────────────────────────┘   │
│                                               │
└──────────────────────────────────────────────┘
```

**Layout File Format:**
```json
{
  "version": "1.0",
  "name": "Trading Focus",
  "created": "2025-09-28T15:30:00Z",
  "widgets": [
    {
      "id": "positions",
      "type": "position-grid",
      "x": 0,
      "y": 0,
      "w": 8,
      "h": 4,
      "config": {
        "columns": 3,
        "sortBy": "pnl"
      }
    }
  ],
  "preferences": {
    "theme": "dark",
    "density": "comfortable"
  }
}
```

#### 10.7 Quick Settings Panel
**Location:** Settings icon in header → Quick Settings
**Purpose:** Fast access to common settings

**Quick Settings Dropdown:**
```
┌────────────────────────────────────┐
│  Quick Settings                    │
├────────────────────────────────────┤
│                                     │
│  🌙 Theme                           │
│  ○ Light  ●  Dark  ○ Auto         │
│                                     │
│  🔔 Notifications                   │
│  ●  Enabled                         │
│  ○ Quiet Mode                      │
│  ○ Critical Only                   │
│                                     │
│  ⚡ Performance                     │
│  Update frequency:                  │
│  ○ Real-time (1s)                  │
│  ● Balanced (5s)                   │
│  ○ Power Saver (30s)               │
│                                     │
│  🔊 Sound Effects                   │
│  ●  Enabled                         │
│                                     │
│  ⌨️  Keyboard Shortcuts             │
│  ●  Enabled                         │
│                                     │
│  ─────────────────────             │
│  [ Full Settings ]                 │
└────────────────────────────────────┘
```

### Success Metrics
- 70%+ users customize default layout
- Average 2.5 saved layouts per active user
- Layout customization reduces task time by 30%
- User satisfaction with customization >4.6/5

---

## Implementation Roadmap

### Phase 1: Critical UX Improvements (Weeks 1-2)
**Priority: Immediate Impact**
1. Real-Time Status Visibility (Header bar, health panel)
2. Emergency Controls (Emergency stop, circuit breaker panel)
3. Loading States & Error Handling (Skeleton screens, error states)

**Why First:** Essential for system monitoring and safety

### Phase 2: Performance & Analytics (Weeks 3-4)
**Priority: High Value**
4. Trading Performance Dashboard (P&L ticker, position cards)
5. Performance Analytics (Sharpe ratio, Monte Carlo)
6. Intelligent Notifications (Notification center, smart grouping)

**Why Second:** Provides critical performance insights

### Phase 3: Accessibility & Responsiveness (Weeks 5-6)
**Priority: Reach & Usability**
7. Dark Mode & Accessibility (Theme toggle, keyboard nav)
8. Mobile Responsiveness (Responsive layouts, touch optimization)

**Why Third:** Expands usability and audience

### Phase 4: Advanced Features (Weeks 7-8)
**Priority: Power User Features**
9. Agent Intelligence Insights (Disagreement viz, confidence meters)
10. Customization & Preferences (Widget system, saved layouts)

**Why Fourth:** Advanced features for experienced users

---

## Design System Integration

### Component Library Alignment
All enhancements should use existing dashboard components where possible:
- `<Card>` from `components/ui/Card.tsx`
- `<Button>` variants from UI library
- `<StatusIndicator>` from `components/dashboard/StatusIndicator.tsx`
- `<Modal>` from `components/ui/Modal.tsx`
- `<Toast>` from `components/ui/Toast.tsx`

### New Components Needed
1. `<SkeletonScreen>` - Loading placeholders
2. `<ConfidenceMeter>` - Agent confidence visualization
3. `<DisagreementVisualization>` - Agent disagreement display
4. `<SharpeRatioGauge>` - Risk-adjusted performance meter
5. `<MonteCarloChart>` - Projection overlay chart
6. `<WidgetGrid>` - Draggable widget container
7. `<CommandPalette>` - Quick actions search

### Typography Scale
```
H1: 32px / 600 weight - Page titles
H2: 24px / 600 weight - Section headers
H3: 20px / 600 weight - Widget titles
Body: 16px / 400 weight - General text
Small: 14px / 400 weight - Secondary info
Tiny: 12px / 400 weight - Timestamps, labels
```

### Spacing System
```
xs:  4px   - Tight spacing within elements
sm:  8px   - Related elements
md:  16px  - Section spacing
lg:  24px  - Major sections
xl:  32px  - Page sections
xxl: 48px  - Page margins
```

---

## Testing Requirements

### Functional Testing
- [ ] All emergency controls work as expected
- [ ] Keyboard navigation covers all interactions
- [ ] Notifications display correctly for all types
- [ ] Dark mode applies consistently across all pages
- [ ] Mobile gestures work reliably
- [ ] Widget drag/drop functions properly
- [ ] Error recovery mechanisms function correctly

### Performance Testing
- [ ] Skeleton screens reduce perceived load time
- [ ] Real-time updates don't cause lag
- [ ] Large datasets (100+ positions) render smoothly
- [ ] Mobile performance acceptable (60fps)
- [ ] Memory usage remains stable during extended use

### Accessibility Testing
- [ ] WCAG 2.1 AA compliance verified
- [ ] Screen reader compatibility (JAWS, NVDA)
- [ ] Keyboard-only navigation fully functional
- [ ] Color contrast ratios meet standards
- [ ] Touch targets meet minimum size requirements

### Usability Testing
- [ ] Users can find emergency controls within 3 seconds
- [ ] Notification preferences are clear and effective
- [ ] Layout customization is intuitive
- [ ] Error messages are understandable
- [ ] Mobile interface is usable without training

---

## Success Metrics Summary

### Adoption Metrics
- Dark mode adoption: >60%
- Layout customization: >70%
- Mobile usage: >30%
- Keyboard shortcuts usage: >40%

### Performance Metrics
- Perceived load time reduction: 40%
- Task completion time reduction: 30%
- Error recovery rate: >85%
- Time to detect issues: -80%

### Satisfaction Metrics
- Overall UX satisfaction: >4.5/5
- Feature discoverability: >4.3/5
- Error message clarity: >4.5/5
- Mobile experience: >4.2/5

---

## Next Steps

1. **Review & Approval**
   - Stakeholder review of specifications
   - Technical feasibility assessment
   - Timeline and resource allocation

2. **Design Phase**
   - Create high-fidelity mockups in Figma
   - Build interactive prototypes
   - Conduct user testing with mockups

3. **Development Phase**
   - Implement Phase 1 (Weeks 1-2)
   - Iterate based on user feedback
   - Progress through remaining phases

4. **Launch & Iteration**
   - Beta testing with select users
   - Gradual rollout of features
   - Continuous improvement based on analytics

---

**Document Status:** ✅ Complete - Ready for Review
**Next Action:** Stakeholder review and design phase kickoff