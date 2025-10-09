/**
 * ParameterHistoryTimeline Component - Story 11.8, Task 5
 *
 * Interactive timeline showing all parameter changes with version comparison
 */

'use client';

import React, { useState } from 'react';
import Card from '@/components/ui/Card';
import { format, parseISO } from 'date-fns';
import type { ParameterVersion } from '@/types/validation';

interface ParameterHistoryTimelineProps {
  versions: ParameterVersion[];
  loading?: boolean;
  onVersionClick?: (version: ParameterVersion) => void;
}

export function ParameterHistoryTimeline({
  versions,
  loading = false,
  onVersionClick,
}: ParameterHistoryTimelineProps) {
  const [selectedVersions, setSelectedVersions] = useState<string[]>([]);

  if (loading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex space-x-4">
              <div className="w-2 bg-gray-200 rounded"></div>
              <div className="flex-1 h-20 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  const handleVersionSelect = (version: string) => {
    setSelectedVersions((prev) => {
      if (prev.includes(version)) {
        return prev.filter((v) => v !== version);
      }
      if (prev.length >= 2) {
        return [prev[1], version]; // Keep only last selected and new one
      }
      return [...prev, version];
    });
  };

  const getScoreColor = (score: number) => {
    if (score < 0.3) return 'text-green-600';
    if (score < 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <Card className="p-6">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Parameter History</h3>
            <p className="text-sm text-gray-500 mt-1">
              Click versions to compare (select up to 2)
            </p>
          </div>
          {selectedVersions.length === 2 && (
            <button
              onClick={() => setSelectedVersions([])}
              className="px-4 py-2 text-sm bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Clear Selection
            </button>
          )}
        </div>

        {/* Timeline */}
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
          {versions.map((version, index) => {
            const isSelected = selectedVersions.includes(version.version);
            const isLatest = index === 0;

            return (
              <div
                key={version.version}
                className={`relative pl-8 pb-6 ${index === versions.length - 1 ? 'pb-0' : ''
                  }`}
              >
                {/* Timeline line */}
                {index < versions.length - 1 && (
                  <div className="absolute left-3 top-6 bottom-0 w-0.5 bg-gray-200"></div>
                )}

                {/* Timeline dot */}
                <div
                  className={`absolute left-0 top-2 w-6 h-6 rounded-full border-4 ${isLatest
                      ? 'bg-blue-500 border-blue-200'
                      : isSelected
                        ? 'bg-green-500 border-green-200'
                        : 'bg-white border-gray-300'
                    }`}
                ></div>

                {/* Version card */}
                <div
                  onClick={() => {
                    handleVersionSelect(version.version);
                    onVersionClick?.(version);
                  }}
                  className={`cursor-pointer border rounded-lg p-4 transition-all ${isSelected
                      ? 'border-green-500 bg-green-50 shadow-md'
                      : 'border-gray-200 bg-white hover:shadow-md hover:border-gray-300'
                    }`}
                >
                  {/* Version header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-gray-900">
                          {version.version}
                        </span>
                        {isLatest && (
                          <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                            Latest
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {format(parseISO(version.date), 'MMM dd, yyyy HH:mm')}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-500">Author</div>
                      <div className="text-sm font-medium text-gray-700">
                        {version.author}
                      </div>
                    </div>
                  </div>

                  {/* Reason */}
                  <div className="mb-3 p-2 bg-gray-50 rounded text-sm text-gray-700">
                    {version.reason}
                  </div>

                  {/* Metrics grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div className="text-center p-2 bg-white rounded border border-gray-200">
                      <div className="text-xs text-gray-500">Backtest Sharpe</div>
                      <div className="text-sm font-bold text-gray-900">
                        {version.metrics.backtest_sharpe.toFixed(2)}
                      </div>
                    </div>
                    <div className="text-center p-2 bg-white rounded border border-gray-200">
                      <div className="text-xs text-gray-500">OOS Sharpe</div>
                      <div className="text-sm font-bold text-gray-900">
                        {version.metrics.out_of_sample_sharpe.toFixed(2)}
                      </div>
                    </div>
                    <div className="text-center p-2 bg-white rounded border border-gray-200">
                      <div className="text-xs text-gray-500">Overfitting</div>
                      <div className={`text-sm font-bold ${getScoreColor(version.metrics.overfitting_score)}`}>
                        {version.metrics.overfitting_score.toFixed(3)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Comparison view */}
        {selectedVersions.length === 2 && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h4 className="font-semibold text-gray-900 mb-4">Version Comparison</h4>
            <div className="grid grid-cols-2 gap-4">
              {selectedVersions.map((versionId) => {
                const version = versions.find((v) => v.version === versionId);
                if (!version) return null;

                return (
                  <div key={versionId} className="p-4 bg-gray-50 rounded-lg">
                    <div className="font-medium text-gray-900 mb-2">
                      {version.version}
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Backtest Sharpe:</span>
                        <span className="font-semibold">
                          {version.metrics.backtest_sharpe.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">OOS Sharpe:</span>
                        <span className="font-semibold">
                          {version.metrics.out_of_sample_sharpe.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Overfitting:</span>
                        <span className={`font-semibold ${getScoreColor(version.metrics.overfitting_score)}`}>
                          {version.metrics.overfitting_score.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
