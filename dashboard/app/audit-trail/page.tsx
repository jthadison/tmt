'use client';

import React, { useState, useEffect } from 'react';
import { getAuditLogs, exportAuditLogs, AuditLog, AuditLogFilters } from '@/api/audit';

export default function AuditTrailPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<AuditLogFilters>({
    status: 'all'
  });

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAuditLogs(filters, 100);
      setLogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch audit logs');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = (format: 'csv' | 'json') => {
    exportAuditLogs(logs, format);
  };

  const getActionBadgeColor = (actionType: string) => {
    switch (actionType) {
      case 'rollback':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'emergency_stop':
        return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'close_positions':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      case 'reset_breakers':
        return 'bg-green-500/10 text-green-400 border-green-500/20';
      default:
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Audit Trail</h1>
            <p className="text-gray-400">
              Comprehensive log of all emergency actions and system events
            </p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => handleExport('csv')}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Export CSV
            </button>
            <button
              onClick={() => handleExport('json')}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Export JSON
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Filters</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Action Type
              </label>
              <select
                value={filters.action_type || ''}
                onChange={(e) =>
                  setFilters({ ...filters, action_type: e.target.value || undefined })
                }
                className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Actions</option>
                <option value="rollback">Rollback</option>
                <option value="emergency_stop">Emergency Stop</option>
                <option value="close_positions">Close Positions</option>
                <option value="reset_breakers">Reset Breakers</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Status
              </label>
              <select
                value={filters.status || 'all'}
                onChange={(e) =>
                  setFilters({
                    ...filters,
                    status: e.target.value as 'success' | 'failed' | 'all'
                  })
                }
                className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Start Date
              </label>
              <input
                type="datetime-local"
                value={filters.start_date || ''}
                onChange={(e) =>
                  setFilters({ ...filters, start_date: e.target.value || undefined })
                }
                className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                End Date
              </label>
              <input
                type="datetime-local"
                value={filters.end_date || ''}
                onChange={(e) =>
                  setFilters({ ...filters, end_date: e.target.value || undefined })
                }
                className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Audit Log Table */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
          {loading ? (
            <div className="p-8 text-center text-gray-400">Loading audit logs...</div>
          ) : error ? (
            <div className="p-8 text-center text-red-400">Error: {error}</div>
          ) : logs.length === 0 ? (
            <div className="p-8 text-center text-gray-400">No audit logs found</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-700 border-b border-gray-600">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Timestamp
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Action
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      User
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Details
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {logs.map((log) => (
                    <tr
                      key={log.log_id}
                      className="hover:bg-gray-750 transition-colors"
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getActionBadgeColor(
                            log.action_type
                          )}`}
                        >
                          {log.action_type.replace('_', ' ').toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {log.user}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                            log.success
                              ? 'bg-green-500/10 text-green-400 border-green-500/20'
                              : 'bg-red-500/10 text-red-400 border-red-500/20'
                          }`}
                        >
                          {log.success ? 'Success' : 'Failed'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300 max-w-md truncate">
                        {JSON.stringify(log.action_details)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="text-sm text-gray-400 text-center">
          Showing {logs.length} audit log entries
        </div>
      </div>
    </div>
  );
}
