# Emergency Rollback Dashboard Component Specification

**Component**: EmergencyRollbackPanel
**Framework**: Next.js 14+ with TypeScript
**Location**: `/dashboard/src/components/emergency/EmergencyRollbackPanel.tsx`

## Component Architecture

### 1. Main Component Structure

```typescript
// EmergencyRollbackPanel.tsx
import { useState, useEffect } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { EmergencyRollbackService } from '@/services/emergencyRollback'

interface RollbackStatus {
  status: 'ready' | 'executing' | 'completed'
  ready_for_rollback: boolean
  last_rollback: RollbackEvent | null
  rollback_count: number
  monitoring_active: boolean
  timestamp: string
}

interface TriggerStatus {
  walk_forward_stability: number
  overfitting_score: number
  consecutive_losses: number
  max_drawdown_percent: number
  triggers_detected: string[]
  trigger_active: boolean
}

interface RollbackEvent {
  event_id: string
  trigger_type: string
  reason: string
  status: string
  timestamp: string
  validation_successful: boolean
  recovery_validation: {
    status: 'passed' | 'failed'
    score: number
    recovery_confirmed: boolean
  }
}

export const EmergencyRollbackPanel: React.FC = () => {
  const [rollbackStatus, setRollbackStatus] = useState<RollbackStatus | null>(null)
  const [triggerStatus, setTriggerStatus] = useState<TriggerStatus | null>(null)
  const [rollbackHistory, setRollbackHistory] = useState<RollbackEvent[]>([])
  const [isExecuting, setIsExecuting] = useState(false)

  // WebSocket for real-time updates
  const { sendMessage, lastMessage } = useWebSocket('ws://localhost:8089/ws/rollback')

  useEffect(() => {
    // Load initial data
    loadRollbackStatus()
    loadTriggerStatus()
    loadRollbackHistory()

    // Set up polling as fallback
    const interval = setInterval(() => {
      loadTriggerStatus()
    }, 30000) // 30-second updates

    return () => clearInterval(interval)
  }, [])

  // WebSocket message handling
  useEffect(() => {
    if (lastMessage?.data) {
      const data = JSON.parse(lastMessage.data)
      if (data.type === 'trigger_update') {
        setTriggerStatus(data.payload)
      } else if (data.type === 'rollback_event') {
        setRollbackHistory(prev => [data.payload, ...prev])
        loadRollbackStatus()
      }
    }
  }, [lastMessage])

  return (
    <div className="emergency-rollback-panel">
      <PanelHeader status={rollbackStatus} />
      <TriggerMonitorGrid triggers={triggerStatus} />
      <RollbackControls
        status={rollbackStatus}
        isExecuting={isExecuting}
        onExecute={handleEmergencyRollback}
        onStartMonitoring={handleStartMonitoring}
        onStopMonitoring={handleStopMonitoring}
      />
      <RollbackHistory events={rollbackHistory} />
    </div>
  )
}
```

### 2. Sub-Components

#### A. Panel Header Component
```typescript
// components/emergency/PanelHeader.tsx
interface PanelHeaderProps {
  status: RollbackStatus | null
}

export const PanelHeader: React.FC<PanelHeaderProps> = ({ status }) => {
  const getCurrentMode = () => {
    // Determine current trading mode based on system state
    return status?.last_rollback?.status === 'completed' ? 'universal_cycle_4' : 'session_targeted'
  }

  const getStatusIndicator = () => {
    if (!status) return { color: 'gray', text: 'Loading...' }
    if (!status.ready_for_rollback) return { color: 'red', text: 'Not Ready' }
    if (status.monitoring_active) return { color: 'green', text: 'Monitoring Active' }
    return { color: 'yellow', text: 'Ready' }
  }

  return (
    <div className="panel-header">
      <div className="system-status">
        <h2>Emergency Rollback System</h2>
        <div className="status-indicators">
          <StatusBadge
            label="Current Mode"
            value={getCurrentMode()}
            color={getCurrentMode() === 'universal_cycle_4' ? 'orange' : 'blue'}
          />
          <StatusBadge
            label="System Status"
            value={getStatusIndicator().text}
            color={getStatusIndicator().color}
          />
          <StatusBadge
            label="Total Rollbacks"
            value={status?.rollback_count || 0}
            color="neutral"
          />
        </div>
      </div>
      <div className="last-activity">
        {status?.last_rollback && (
          <div className="last-rollback-info">
            <span>Last Rollback: {new Date(status.last_rollback.timestamp).toLocaleString()}</span>
            <span className={`validation-status ${status.last_rollback.validation_successful ? 'success' : 'warning'}`}>
              Validation: {status.last_rollback.validation_successful ? '✅ Passed' : '⚠️ Review'}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
```

#### B. Trigger Monitor Grid Component
```typescript
// components/emergency/TriggerMonitorGrid.tsx
interface TriggerMonitorGridProps {
  triggers: TriggerStatus | null
}

interface MetricCardProps {
  title: string
  value: number
  threshold: number
  unit?: string
  format?: 'decimal' | 'percentage'
  dangerBelow?: boolean // true for walk-forward stability (danger when below threshold)
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  threshold,
  unit = '',
  format = 'decimal',
  dangerBelow = false
}) => {
  const getStatus = () => {
    const isTriggered = dangerBelow ? value < threshold : value > threshold
    if (isTriggered) return 'critical'

    // Warning zone (within 20% of threshold)
    const warningZone = threshold * 0.2
    const nearThreshold = dangerBelow
      ? value < (threshold + warningZone)
      : value > (threshold - warningZone)

    return nearThreshold ? 'warning' : 'normal'
  }

  const formatValue = () => {
    if (format === 'percentage') return `${(value * 100).toFixed(1)}%`
    return `${value.toFixed(1)}${unit}`
  }

  const status = getStatus()
  const statusColors = {
    normal: 'bg-green-100 border-green-300 text-green-800',
    warning: 'bg-yellow-100 border-yellow-300 text-yellow-800',
    critical: 'bg-red-100 border-red-300 text-red-800'
  }

  return (
    <div className={`metric-card ${statusColors[status]} border-2 rounded-lg p-4`}>
      <div className="metric-header">
        <h3 className="text-sm font-medium">{title}</h3>
        <div className="status-indicator">
          {status === 'critical' && '🔴'}
          {status === 'warning' && '🟡'}
          {status === 'normal' && '🟢'}
        </div>
      </div>
      <div className="metric-value">
        <span className="text-2xl font-bold">{formatValue()}</span>
      </div>
      <div className="metric-threshold">
        <span className="text-xs">
          Threshold: {dangerBelow ? '<' : '>'} {formatValue()}
        </span>
      </div>
      <div className="metric-trend">
        {/* Add trend indicators based on historical data */}
        <TrendIndicator value={value} threshold={threshold} />
      </div>
    </div>
  )
}

export const TriggerMonitorGrid: React.FC<TriggerMonitorGridProps> = ({ triggers }) => {
  if (!triggers) return <div className="loading">Loading trigger status...</div>

  return (
    <div className="trigger-monitor-grid">
      <h3 className="section-title">Automatic Trigger Conditions</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Walk-Forward Stability"
          value={triggers.walk_forward_stability}
          threshold={40.0}
          unit="/100"
          dangerBelow={true}
        />
        <MetricCard
          title="Overfitting Score"
          value={triggers.overfitting_score}
          threshold={0.5}
          format="decimal"
          dangerBelow={false}
        />
        <MetricCard
          title="Consecutive Losses"
          value={triggers.consecutive_losses}
          threshold={5}
          unit=" losses"
          dangerBelow={false}
        />
        <MetricCard
          title="Max Drawdown"
          value={triggers.max_drawdown_percent}
          threshold={5.0}
          unit="%"
          dangerBelow={false}
        />
      </div>

      {triggers.triggers_detected.length > 0 && (
        <div className="active-triggers-alert">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
            <div className="flex items-center">
              <span className="text-red-600 font-semibold">⚠️ Active Triggers Detected:</span>
            </div>
            <ul className="mt-2 text-red-700">
              {triggers.triggers_detected.map(trigger => (
                <li key={trigger} className="flex items-center">
                  <span className="mr-2">•</span>
                  <span>{trigger.replace('_', ' ').toUpperCase()}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
```

#### C. Rollback Controls Component
```typescript
// components/emergency/RollbackControls.tsx
interface RollbackControlsProps {
  status: RollbackStatus | null
  isExecuting: boolean
  onExecute: (reason: string) => Promise<void>
  onStartMonitoring: () => Promise<void>
  onStopMonitoring: () => Promise<void>
}

export const RollbackControls: React.FC<RollbackControlsProps> = ({
  status,
  isExecuting,
  onExecute,
  onStartMonitoring,
  onStopMonitoring
}) => {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [rollbackReason, setRollbackReason] = useState('')

  const handleEmergencyRollback = async () => {
    if (!rollbackReason.trim()) {
      alert('Please provide a reason for the emergency rollback')
      return
    }

    setShowConfirmDialog(false)
    await onExecute(rollbackReason)
    setRollbackReason('')
  }

  return (
    <div className="rollback-controls">
      <h3 className="section-title">Emergency Controls</h3>

      <div className="control-grid">
        {/* Emergency Rollback Button */}
        <div className="emergency-rollback-section">
          <button
            onClick={() => setShowConfirmDialog(true)}
            disabled={!status?.ready_for_rollback || isExecuting}
            className={`emergency-button ${
              status?.ready_for_rollback && !isExecuting
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            } px-6 py-3 rounded-lg font-semibold flex items-center`}
          >
            {isExecuting ? (
              <>
                <Spinner className="mr-2" />
                Executing Rollback...
              </>
            ) : (
              <>
                🚨 Emergency Rollback to Cycle 4
              </>
            )}
          </button>

          <div className="button-help-text">
            <span className="text-sm text-gray-600">
              Immediately switches system to conservative Cycle 4 parameters (55% confidence, 1.8 R:R)
            </span>
          </div>
        </div>

        {/* Monitoring Controls */}
        <div className="monitoring-controls">
          <div className="flex gap-3">
            <button
              onClick={onStartMonitoring}
              disabled={status?.monitoring_active}
              className={`px-4 py-2 rounded ${
                status?.monitoring_active
                  ? 'bg-gray-300 text-gray-500'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              Start Monitoring
            </button>

            <button
              onClick={onStopMonitoring}
              disabled={!status?.monitoring_active}
              className={`px-4 py-2 rounded ${
                !status?.monitoring_active
                  ? 'bg-gray-300 text-gray-500'
                  : 'bg-orange-600 hover:bg-orange-700 text-white'
              }`}
            >
              Stop Monitoring
            </button>
          </div>

          <div className="monitoring-status mt-2">
            <span className={`text-sm ${status?.monitoring_active ? 'text-green-600' : 'text-gray-600'}`}>
              Automatic monitoring: {status?.monitoring_active ? '✅ Active' : '⭕ Inactive'}
            </span>
          </div>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmDialog && (
        <ConfirmationDialog
          title="Confirm Emergency Rollback"
          message="This will immediately switch the trading system to conservative Cycle 4 parameters. This action cannot be undone automatically."
          onConfirm={handleEmergencyRollback}
          onCancel={() => setShowConfirmDialog(false)}
          requiresReason={true}
          reason={rollbackReason}
          onReasonChange={setRollbackReason}
        />
      )}
    </div>
  )
}
```

#### D. Rollback History Component
```typescript
// components/emergency/RollbackHistory.tsx
interface RollbackHistoryProps {
  events: RollbackEvent[]
}

export const RollbackHistory: React.FC<RollbackHistoryProps> = ({ events }) => {
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null)

  const getEventTypeIcon = (triggerType: string) => {
    const icons = {
      'manual': '👤',
      'performance_degradation': '📉',
      'walk_forward_failure': '📊',
      'overfitting_detected': '🎯',
      'consecutive_losses': '📉',
      'drawdown_breach': '🔻'
    }
    return icons[triggerType] || '⚠️'
  }

  const getValidationStatusBadge = (validation: RollbackEvent['recovery_validation']) => {
    if (validation.status === 'passed') {
      return <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">✅ Validated</span>
    } else {
      return <span className="bg-red-100 text-red-800 px-2 py-1 rounded text-xs">❌ Failed</span>
    }
  }

  return (
    <div className="rollback-history">
      <h3 className="section-title">Recent Rollback Events</h3>

      {events.length === 0 ? (
        <div className="no-events">
          <p className="text-gray-500 text-center py-8">No rollback events recorded</p>
        </div>
      ) : (
        <div className="events-timeline">
          {events.slice(0, 10).map(event => (
            <div key={event.event_id} className="timeline-event border rounded-lg p-4 mb-3">
              <div
                className="event-header cursor-pointer"
                onClick={() => setExpandedEvent(
                  expandedEvent === event.event_id ? null : event.event_id
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="event-summary flex items-center">
                    <span className="event-icon text-xl mr-3">
                      {getEventTypeIcon(event.trigger_type)}
                    </span>
                    <div>
                      <span className="font-semibold">{event.trigger_type.replace('_', ' ')}</span>
                      <span className="text-gray-500 ml-2">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <div className="event-status flex items-center gap-2">
                    {getValidationStatusBadge(event.recovery_validation)}
                    <span className="text-sm text-gray-400">
                      {expandedEvent === event.event_id ? '▼' : '▶'}
                    </span>
                  </div>
                </div>
              </div>

              {expandedEvent === event.event_id && (
                <div className="event-details mt-3 pt-3 border-t">
                  <div className="detail-grid grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h5 className="font-medium text-gray-700">Event Details</h5>
                      <ul className="text-sm text-gray-600 mt-1">
                        <li>Event ID: {event.event_id}</li>
                        <li>Reason: {event.reason}</li>
                        <li>Status: {event.status}</li>
                      </ul>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-700">Recovery Validation</h5>
                      <ul className="text-sm text-gray-600 mt-1">
                        <li>Score: {event.recovery_validation.score}/100</li>
                        <li>Status: {event.recovery_validation.status}</li>
                        <li>Recovery Confirmed: {event.recovery_validation.recovery_confirmed ? 'Yes' : 'No'}</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}

          {events.length > 10 && (
            <div className="view-all-link text-center mt-4">
              <button className="text-blue-600 hover:text-blue-800">
                View All Rollback History
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

### 3. Services Layer

```typescript
// services/emergencyRollback.ts
export class EmergencyRollbackService {
  private baseUrl = 'http://localhost:8089'

  async getRollbackStatus(): Promise<RollbackStatus> {
    const response = await fetch(`${this.baseUrl}/emergency-rollback/status`)
    if (!response.ok) throw new Error('Failed to fetch rollback status')
    return response.json()
  }

  async getTriggerStatus(): Promise<TriggerStatus> {
    const response = await fetch(`${this.baseUrl}/emergency-rollback/check-triggers`, {
      method: 'POST'
    })
    if (!response.ok) throw new Error('Failed to check trigger status')
    return response.json()
  }

  async executeEmergencyRollback(reason: string, notifyContacts = true): Promise<RollbackEvent> {
    const response = await fetch(`${this.baseUrl}/emergency-rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason, notify_contacts: notifyContacts })
    })
    if (!response.ok) throw new Error('Failed to execute emergency rollback')
    return response.json()
  }

  async startMonitoring(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/rollback-monitor/start`, {
      method: 'POST'
    })
    if (!response.ok) throw new Error('Failed to start monitoring')
  }

  async stopMonitoring(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/rollback-monitor/stop`, {
      method: 'POST'
    })
    if (!response.ok) throw new Error('Failed to stop monitoring')
  }

  async getRollbackHistory(): Promise<RollbackEvent[]> {
    const response = await fetch(`${this.baseUrl}/emergency-rollback/history`)
    if (!response.ok) throw new Error('Failed to fetch rollback history')
    const data = await response.json()
    return data.history
  }
}
```

### 4. Styling (Tailwind CSS)

```css
/* styles/emergency-rollback.css */
.emergency-rollback-panel {
  @apply bg-white rounded-lg shadow-lg p-6;
}

.panel-header {
  @apply border-b pb-4 mb-6;
}

.status-indicators {
  @apply flex gap-3 mt-2;
}

.trigger-monitor-grid {
  @apply mb-6;
}

.section-title {
  @apply text-lg font-semibold text-gray-800 mb-4;
}

.metric-card {
  @apply transition-all duration-200 hover:shadow-md;
}

.emergency-button {
  @apply transition-all duration-200 transform hover:scale-105;
}

.timeline-event {
  @apply transition-all duration-200 hover:shadow-md;
}

.control-grid {
  @apply space-y-4;
}

.emergency-rollback-section {
  @apply text-center;
}

.button-help-text {
  @apply mt-2;
}
```

This comprehensive dashboard component specification provides a complete implementation plan for integrating the emergency rollback system into the existing Next.js dashboard with real-time monitoring, intuitive controls, and comprehensive status visualization.