/**
 * AlertDashboard Component - Story 11.8, Task 7
 *
 * Centralized view of all validation alerts with filtering and actions
 */

'use client';

import React, { useState } from 'react';
import Card from '@/components/ui/Card';
import { format, parseISO } from 'date-fns';
import type { ValidationAlert, AlertLevel } from '@/types/validation';

interface AlertDashboardProps {
  alerts: ValidationAlert[];
  loading?: boolean;
  onAcknowledge?: (alertId: string) => Promise<void>;
  onDismiss?: (alertId: string) => Promise<void>;
}

export function AlertDashboard({
  alerts,
  loading = false,
  onAcknowledge,
  onDismiss,
}: AlertDashboardProps) {
  const [filter, setFilter] = useState<'all' | 'unacknowledged' | 'critical'>('all');
  const [severityFilter, setSeverityFilter] = useState<AlertLevel | 'all'>('all');

  if (loading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/3"></div>
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-gray-200 rounded"></div>
          ))}
        </div>
      </Card>
    );
  }

  // Apply filters
  const filteredAlerts = alerts.filter((alert) => {
    if (filter === 'unacknowledged' && alert.acknowledged) return false;
    if (filter === 'critical' && alert.severity !== 'CRITICAL') return false;
    if (severityFilter !== 'all' && alert.severity !== severityFilter) return false;
    return true;
  });

  const getSeverityColor = (severity: AlertLevel) => {
    switch (severity) {
      case 'CRITICAL':
        return { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300' };
      case 'WARNING':
        return { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-300' };
      case 'INFO':
        return { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300' };
      default:
        return { bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-300' };
    }
  };

  const getAlertTypeIcon = (type: string) => {
    switch (type) {
      case 'OVERFITTING':
        return '📊';
      case 'PERFORMANCE_DEGRADATION':
        return '📉';
      case 'PARAMETER_DRIFT':
        return '⚠️';
      case 'VALIDATION_FAILURE':
        return '❌';
      default:
        return '🔔';
    }
  };

  return (
    <Card className="p-6">
      <div className="flex flex-col h-full">
        {/* Header with filters */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Validation Alerts</h3>
            <p className="text-sm text-gray-500 mt-1">
              {filteredAlerts.length} of {alerts.length} alerts
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="all">All Alerts</option>
              <option value="unacknowledged">Unacknowledged</option>
              <option value="critical">Critical Only</option>
            </select>

            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            >
              <option value="all">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="WARNING">Warning</option>
              <option value="INFO">Info</option>
            </select>
          </div>
        </div>

        {/* Alerts list */}
        <div className="space-y-3 max-h-[600px] overflow-y-auto">
          {filteredAlerts.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>✅ No alerts matching your filters</p>
            </div>
          ) : (
            filteredAlerts.map((alert) => {
              const colors = getSeverityColor(alert.severity);
              const icon = getAlertTypeIcon(alert.alert_type);

              return (
                <div
                  key={alert.id}
                  className={`border ${colors.border} ${alert.acknowledged ? 'opacity-60' : ''
                    } rounded-lg p-4 transition-all hover:shadow-md`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {/* Alert header */}
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-2xl">{icon}</span>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${colors.bg} ${colors.text}`}>
                          {alert.severity}
                        </span>
                        <span className="text-xs text-gray-500">
                          {alert.alert_type.replace(/_/g, ' ')}
                        </span>
                        {alert.acknowledged && (
                          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                            ✓ Acknowledged
                          </span>
                        )}
                        {alert.resolved && (
                          <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                            Resolved
                          </span>
                        )}
                      </div>

                      {/* Alert message */}
                      <p className="text-gray-900 mb-2">{alert.message}</p>

                      {/* Timestamp */}
                      <p className="text-xs text-gray-500">
                        {format(parseISO(alert.timestamp), 'MMM dd, yyyy HH:mm:ss')}
                      </p>

                      {/* Resolution note */}
                      {alert.resolution_note && (
                        <div className="mt-2 p-2 bg-gray-50 rounded text-sm text-gray-700">
                          <strong>Resolution:</strong> {alert.resolution_note}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="ml-4 flex flex-col space-y-2">
                      {!alert.acknowledged && onAcknowledge && (
                        <button
                          onClick={() => onAcknowledge(alert.id)}
                          className="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                        >
                          Acknowledge
                        </button>
                      )}
                      {!alert.resolved && onDismiss && (
                        <button
                          onClick={() => onDismiss(alert.id)}
                          className="px-3 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
                        >
                          Dismiss
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Summary statistics */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="text-center p-3 bg-red-50 rounded">
              <div className="text-xs text-gray-600">Critical</div>
              <div className="text-xl font-bold text-red-600">
                {alerts.filter((a) => a.severity === 'CRITICAL').length}
              </div>
            </div>
            <div className="text-center p-3 bg-yellow-50 rounded">
              <div className="text-xs text-gray-600">Warning</div>
              <div className="text-xl font-bold text-yellow-600">
                {alerts.filter((a) => a.severity === 'WARNING').length}
              </div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded">
              <div className="text-xs text-gray-600">Acknowledged</div>
              <div className="text-xl font-bold text-green-600">
                {alerts.filter((a) => a.acknowledged).length}
              </div>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded">
              <div className="text-xs text-gray-600">Resolved</div>
              <div className="text-xl font-bold text-gray-700">
                {alerts.filter((a) => a.resolved).length}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
