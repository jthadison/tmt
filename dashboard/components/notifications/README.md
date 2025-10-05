# Notification Center

Intelligent notification system with priority-based alerts and smart grouping.

## Features

- ✅ Priority-based notifications (Critical, Warning, Success, Info)
- ✅ Smart grouping (similar events within 30 minutes)
- ✅ Date-based organization (Today, Yesterday, This Week, Older)
- ✅ localStorage persistence with 30-day retention
- ✅ Mark as read/unread functionality
- ✅ Individual and bulk dismiss actions
- ✅ Accessibility support (ARIA labels, keyboard navigation)

## Usage

### Adding Notifications

```typescript
import { useNotifications } from '@/context/NotificationContext'
import { NotificationPriority } from '@/types/notifications'

function MyComponent() {
  const { addNotification } = useNotifications()

  const handleTradeClose = () => {
    addNotification({
      priority: NotificationPriority.SUCCESS,
      title: 'Trade Closed',
      message: 'EUR/USD position closed with +$150 profit',
      timestamp: new Date(),
      groupKey: 'trade_closed', // Optional: for smart grouping
      relatedUrl: '/history', // Optional: navigation on click
      actions: [ // Optional: custom action buttons
        {
          label: 'View Trade',
          action: () => router.push('/history'),
          variant: 'primary'
        }
      ]
    })
  }

  return <button onClick={handleTradeClose}>Close Trade</button>
}
```

### Notification Priorities

| Priority | Use Case | Color | Auto-Group |
|----------|----------|-------|------------|
| `CRITICAL` | System failures, circuit breakers | Red | Never |
| `WARNING` | Thresholds approaching, degraded agents | Yellow | Yes |
| `SUCCESS` | Trades closed profitably, system recovery | Green | Yes |
| `INFO` | Trades opened, agent lifecycle events | Blue | Yes |

### Smart Grouping

Notifications with the same `groupKey` within a 30-minute window are automatically grouped:

```typescript
// These will be grouped together
addNotification({
  title: 'Trade Closed',
  groupKey: 'trade_closed',
  timestamp: new Date()
})

addNotification({
  title: 'Trade Closed',
  groupKey: 'trade_closed',
  timestamp: new Date() // Within 30 minutes
})
```

**Note:** Critical priority notifications are NEVER grouped.

### Available Actions

```typescript
const {
  notifications,        // Visible (non-dismissed) notifications
  groupedByDate,       // Grouped by today/yesterday/week/older
  unreadCount,         // Number of unread notifications
  hasNotifications,    // Boolean: any notifications exist
  addNotification,     // Add new notification
  markRead,           // Mark single notification as read
  markAllRead,        // Mark all as read
  markGroupRead,      // Mark entire group as read
  dismiss,            // Dismiss single notification
  clearAll            // Dismiss all notifications
} = useNotifications()
```

## Components

- **NotificationCenter**: Main component (already integrated in Header)
- **NotificationBellIcon**: Bell icon with unread badge
- **NotificationPanel**: Slide-out panel with notification list
- **NotificationCard**: Individual notification display
- **GroupedNotification**: Grouped notification with expand/collapse

## Storage

Notifications are automatically saved to localStorage:
- Key: `notifications_history`
- Retention: 30 days
- Max limit: 500 notifications (FIFO)
- Auto-cleanup: Old notifications removed on load

## Accessibility

- Screen reader support with ARIA labels
- Keyboard navigation (Tab, Enter, Escape)
- Color contrast meets WCAG 2.1 AA standards
- Focus management for modal interactions

## Example: Creating Event-Based Notifications

```typescript
// In a service or component that monitors events
useEffect(() => {
  const handleCircuitBreakerEvent = (event: CircuitBreakerEvent) => {
    addNotification({
      priority: NotificationPriority.CRITICAL,
      title: 'Circuit Breaker Triggered',
      message: `Trading halted: ${event.reason}`,
      timestamp: new Date(),
      relatedUrl: '/system',
      actions: [
        {
          label: 'View Details',
          action: () => router.push('/system'),
          variant: 'primary'
        },
        {
          label: 'Acknowledge',
          action: () => acknowledgeCircuitBreaker(event.id),
          variant: 'secondary'
        }
      ]
    })
  }

  // Subscribe to events
  eventBus.on('circuitBreaker', handleCircuitBreakerEvent)

  return () => {
    eventBus.off('circuitBreaker', handleCircuitBreakerEvent)
  }
}, [])
```

## Integration with Story 4.2

This notification center is designed to integrate with event streams in Story 4.2:
- WebSocket connections for real-time events
- Agent health status changes
- Trade lifecycle events
- System alerts and warnings
