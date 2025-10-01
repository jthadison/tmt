'use client';

import React, { useState, useEffect } from 'react';
import { getRollbackConditions, updateRollbackCondition, RollbackCondition } from '@/api/rollback';

export default function AutomatedTriggerMonitoring() {
  const [conditions, setConditions] = useState<RollbackCondition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingCondition, setUpdatingCondition] = useState<string | null>(null);

  useEffect(() => {
    fetchConditions();
  }, []);

  const fetchConditions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getRollbackConditions();
      setConditions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch rollback conditions');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (triggerType: string, currentlyEnabled: boolean) => {
    try {
      setUpdatingCondition(triggerType);
      await updateRollbackCondition(triggerType, !currentlyEnabled);

      // Update local state
      setConditions(
        conditions.map((cond) =>
          cond.trigger_type === triggerType ? { ...cond, enabled: !currentlyEnabled } : cond
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update condition');
    } finally {
      setUpdatingCondition(null);
    }
  };

  const getStatusColor = (currentValue: number, thresholdValue: number, enabled: boolean) => {
    if (!enabled) return 'border-gray-600';
    if (currentValue >= thresholdValue) return 'border-red-500';
    if (currentValue >= thresholdValue * 0.8) return 'border-yellow-500';
    return 'border-green-500';
  };

  const getProgressPercentage = (currentValue: number, thresholdValue: number) => {
    return Math.min((currentValue / thresholdValue) * 100, 100);
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-8 text-center text-gray-400">
        Loading automated triggers...
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-8 text-center text-red-400">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {conditions.map((condition) => {
        const statusColor = getStatusColor(
          condition.current_value,
          condition.threshold_value,
          condition.enabled
        );
        const progress = getProgressPercentage(condition.current_value, condition.threshold_value);

        return (
          <div
            key={condition.trigger_type}
            className={`bg-gray-800 rounded-lg p-6 border-l-4 ${statusColor} border-r border-t border-b border-gray-700`}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white mb-1">
                  {condition.description}
                </h3>
                <p className="text-sm text-gray-400">
                  Priority: {condition.priority} | Consecutive Periods:{' '}
                  {condition.consecutive_periods}
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <span
                  className={`text-xs font-medium ${
                    condition.enabled ? 'text-green-400' : 'text-gray-500'
                  }`}
                >
                  {condition.enabled ? 'Active' : 'Inactive'}
                </span>
                <button
                  onClick={() => handleToggle(condition.trigger_type, condition.enabled)}
                  disabled={updatingCondition === condition.trigger_type}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    condition.enabled ? 'bg-green-600' : 'bg-gray-600'
                  } ${
                    updatingCondition === condition.trigger_type ? 'opacity-50 cursor-wait' : ''
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      condition.enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </div>

            <div className="space-y-3">
              {/* Current Value vs Threshold */}
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Current Value:</span>
                <span className="text-white font-medium">
                  {condition.current_value} {condition.threshold_unit}
                </span>
              </div>

              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Threshold:</span>
                <span className="text-white font-medium">
                  {condition.threshold_value} {condition.threshold_unit}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="mt-4">
                <div className="w-full bg-gray-700 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-3 transition-all duration-300 ${
                      progress >= 100
                        ? 'bg-red-500'
                        : progress >= 80
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0%</span>
                  <span>{progress.toFixed(1)}%</span>
                  <span>100%</span>
                </div>
              </div>

              {/* Status Message */}
              {condition.enabled && (
                <div className="mt-3">
                  {progress >= 100 ? (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2 text-xs text-red-400">
                      ⚠️ Threshold exceeded - rollback may be triggered
                    </div>
                  ) : progress >= 80 ? (
                    <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-2 text-xs text-yellow-400">
                      ⚠️ Approaching threshold
                    </div>
                  ) : (
                    <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-2 text-xs text-green-400">
                      ✓ Within safe limits
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
