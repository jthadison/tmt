'use client';

import React, { useState, useEffect } from 'react';
import { getRollbackHistory, RollbackEvent } from '@/api/rollback';

export default function RollbackHistoryTable() {
  const [history, setHistory] = useState<RollbackEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getRollbackHistory(20);
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch rollback history');
    } finally {
      setLoading(false);
    }
  };

  const getTriggerBadgeColor = (triggerType: string) => {
    switch (triggerType) {
      case 'manual':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'walk_forward_failure':
      case 'overfitting_detected':
        return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'performance_degradation':
      case 'consecutive_losses':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      default:
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-500/10 text-green-400 border-green-500/20';
      case 'failed':
        return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'in_progress':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      default:
        return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
    }
  };

  const formatTriggerType = (triggerType: string) => {
    return triggerType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {loading ? (
        <div className="p-8 text-center text-gray-400">Loading rollback history...</div>
      ) : error ? (
        <div className="p-8 text-center text-red-400">Error: {error}</div>
      ) : history.length === 0 ? (
        <div className="p-8 text-center text-gray-400">No rollback events found</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-700 border-b border-gray-600">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Trigger
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  From Mode
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  To Mode
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Reason
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  User
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {history.map((event) => (
                <tr key={event.event_id} className="hover:bg-gray-750 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {new Date(event.timestamp).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getTriggerBadgeColor(
                        event.trigger_type
                      )}`}
                    >
                      {formatTriggerType(event.trigger_type)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {event.previous_mode}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {event.new_mode}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-300 max-w-md">
                    <div className="truncate" title={event.trigger_reason}>
                      {event.trigger_reason}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusBadgeColor(
                        event.status
                      )}`}
                    >
                      {event.success ? 'Success' : event.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {event.user || 'System'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="px-6 py-4 bg-gray-750 border-t border-gray-700 flex justify-between items-center">
        <span className="text-sm text-gray-400">
          Showing {history.length} rollback events (last 20)
        </span>
        <button
          onClick={fetchHistory}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
        >
          Refresh
        </button>
      </div>
    </div>
  );
}
