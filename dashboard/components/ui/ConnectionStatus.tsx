'use client'

import { ConnectionStatus as Status } from '@/types/websocket'

interface ConnectionStatusProps {
  status: Status
  className?: string
}

/**
 * Visual indicator for WebSocket connection status
 * @param status - Current connection status
 * @param className - Additional CSS classes
 * @returns Connection status indicator with icon and text
 */
function ConnectionStatus({ status, className = '' }: ConnectionStatusProps) {
  const getStatusConfig = (status: Status) => {
    switch (status) {
      case Status.CONNECTED:
        return {
          icon: '●',
          text: 'Connected',
          color: 'text-green-400'
        }
      case Status.CONNECTING:
        return {
          icon: '○',
          text: 'Connecting',
          color: 'text-yellow-400'
        }
      case Status.RECONNECTING:
        return {
          icon: '◑',
          text: 'Reconnecting',
          color: 'text-orange-400'
        }
      case Status.DISCONNECTED:
        return {
          icon: '○',
          text: 'Disconnected',
          color: 'text-gray-400'
        }
      case Status.ERROR:
        return {
          icon: '●',
          text: 'Error',
          color: 'text-red-400'
        }
      default:
        return {
          icon: '○',
          text: 'Unknown',
          color: 'text-gray-400'
        }
    }
  }

  const config = getStatusConfig(status)

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <span className={`${config.color} text-lg leading-none`}>
        {config.icon}
      </span>
      <span className={`text-sm ${config.color}`}>
        {config.text}
      </span>
    </div>
  )
}

export default ConnectionStatus
export { ConnectionStatus }
export type { ConnectionStatusProps }