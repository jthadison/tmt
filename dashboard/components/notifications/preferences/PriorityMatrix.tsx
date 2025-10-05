/**
 * Priority matrix component for notification preferences
 * 4x5 grid controlling which priorities are sent to which delivery methods
 */

'use client'

import {
  DeliveryMethod,
  DELIVERY_METHOD_LABELS,
  PriorityMatrix as PriorityMatrixType
} from '@/types/notificationPreferences'
import { NotificationPriority, PRIORITY_CONFIG } from '@/types/notifications'

interface PriorityMatrixProps {
  priorityMatrix: PriorityMatrixType
  onToggle: (method: DeliveryMethod, priority: NotificationPriority, enabled: boolean) => void
}

export function PriorityMatrix({ priorityMatrix, onToggle }: PriorityMatrixProps) {
  const methods: DeliveryMethod[] = ['inApp', 'browserPush', 'email', 'slack', 'sms']
  const priorities: NotificationPriority[] = [
    NotificationPriority.CRITICAL,
    NotificationPriority.WARNING,
    NotificationPriority.SUCCESS,
    NotificationPriority.INFO
  ]

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-white">Priority Filtering</h3>
        <p className="text-sm text-gray-400 mt-1">
          Control which priority levels are sent to each delivery method
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-3 text-left bg-gray-800 border border-gray-700">
                <span className="text-sm font-medium text-gray-300">Delivery Method</span>
              </th>
              {priorities.map((priority) => (
                <th
                  key={priority}
                  className="p-3 text-center bg-gray-800 border border-gray-700"
                >
                  <div className="flex flex-col items-center gap-1">
                    <span
                      className={`text-lg ${PRIORITY_CONFIG[priority].textColor}`}
                      aria-label={priority}
                    >
                      {PRIORITY_CONFIG[priority].icon}
                    </span>
                    <span className="text-xs font-medium text-gray-300 capitalize">
                      {priority}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {methods.map((method) => (
              <tr key={method} className="hover:bg-gray-800/30 transition-colors">
                <td className="p-3 border border-gray-700 bg-gray-800/50">
                  <span className="text-sm font-medium text-white">
                    {DELIVERY_METHOD_LABELS[method]}
                  </span>
                </td>
                {priorities.map((priority) => (
                  <td
                    key={`${method}-${priority}`}
                    className="p-3 text-center border border-gray-700"
                  >
                    <label className="inline-flex items-center justify-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={priorityMatrix[method]?.[priority] ?? false}
                        onChange={(e) => onToggle(method, priority, e.target.checked)}
                        disabled={method === 'inApp'} // In-App always enabled for all priorities
                        className="w-5 h-5 rounded border-gray-600 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                        aria-label={`Enable ${priority} notifications for ${DELIVERY_METHOD_LABELS[method]}`}
                      />
                    </label>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded">
        <p className="text-sm text-blue-400">
          <strong>Note:</strong> In-app notifications are always enabled for all priority levels
          and cannot be disabled.
        </p>
      </div>
    </div>
  )
}
