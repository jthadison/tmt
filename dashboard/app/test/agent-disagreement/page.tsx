/**
 * Test Page for Agent Disagreement Panel
 * E2E Testing with Playwright
 */

'use client';

import { useState } from 'react';
import { AgentDisagreementPanel } from '@/components/intelligence';

export default function AgentDisagreementTestPage() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Agent Disagreement Panel - Test Page
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            This page is used for E2E testing with Playwright. It demonstrates the
            Agent Disagreement Visualization and Confidence Meters (Story 7.1).
          </p>

          <div className="flex gap-4">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {isExpanded ? 'Hide Agent Disagreement' : 'View Agent Disagreement'}
            </button>

            <button
              onClick={() => setIsExpanded(false)}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              disabled={!isExpanded}
            >
              Close Panel
            </button>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              EUR/USD Signal Analysis
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Click "View Agent Disagreement" to see how the 8 AI agents analyze this signal
            </p>
          </div>

          <AgentDisagreementPanel
            symbol="EUR_USD"
            isExpanded={isExpanded}
            refreshInterval={10000}
          />
        </div>

        {/* Test Information Panel */}
        <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-3">
            Test Information
          </h3>
          <div className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
            <p><strong>Symbol:</strong> EUR_USD</p>
            <p><strong>Panel State:</strong> {isExpanded ? 'Expanded' : 'Collapsed'}</p>
            <p><strong>Auto-Refresh:</strong> 10 seconds</p>
            <p><strong>Agents:</strong> 8 (Market Analysis, Strategy Analysis, Parameter Optimization, Learning Safety, Disagreement Engine, Data Collection, Continuous Improvement, Pattern Detection)</p>
          </div>
        </div>

        {/* Component Features List */}
        <div className="mt-8 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-green-900 dark:text-green-100 mb-3">
            Features Demonstrated
          </h3>
          <ul className="space-y-2 text-sm text-green-800 dark:text-green-200">
            <li>✅ Consensus Meter - Circular progress indicator showing 75% agreement</li>
            <li>✅ Confidence Meters - 5-level color coding (Very Low to Very High)</li>
            <li>✅ Agent Position Cards - 8 cards showing individual agent decisions</li>
            <li>✅ Decision Badge - Final BUY decision with threshold status</li>
            <li>✅ Agent Icons - Emoji icons for each agent</li>
            <li>✅ Reasoning Display - 2-3 bullet points per agent explaining their decision</li>
            <li>✅ Color Coding - BUY (green), SELL (red), NEUTRAL (gray)</li>
            <li>✅ Loading States - Skeleton loader while fetching data</li>
            <li>✅ Error Handling - Graceful error messages on API failures</li>
            <li>✅ Dark Mode - Full dark mode support</li>
            <li>✅ Responsive - Mobile and desktop layouts</li>
            <li>✅ Accessibility - ARIA labels and semantic HTML</li>
          </ul>
        </div>

        {/* API Mock Information */}
        <div className="mt-8 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-yellow-900 dark:text-yellow-100 mb-3">
            API Endpoint Information
          </h3>
          <div className="space-y-2 text-sm text-yellow-800 dark:text-yellow-200">
            <p><strong>Endpoint:</strong> GET /disagreement/current/EUR_USD</p>
            <p><strong>Mock Data:</strong> Playwright intercepts and returns mock disagreement data</p>
            <p><strong>Expected Response:</strong></p>
            <pre className="mt-2 p-3 bg-yellow-100 dark:bg-yellow-900/40 rounded text-xs overflow-x-auto">
{`{
  symbol: "EUR_USD",
  consensusPercentage: 75,
  finalDecision: "BUY",
  thresholdMet: true,
  requiredThreshold: 70,
  agentPositions: [/* 8 agent positions */]
}`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
