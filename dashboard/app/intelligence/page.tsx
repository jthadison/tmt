/**
 * Agent Intelligence Insights Page
 * Houses all Epic 7 stories in tabbed interface
 */

'use client';

import { useState } from 'react';
import { AgentDisagreementPanel } from '@/components/intelligence/AgentDisagreementPanel';
import { DecisionHistorySection } from '@/components/intelligence/DecisionHistorySection';
import { AgentPerformanceDashboard } from '@/components/intelligence/AgentPerformanceDashboard';
import { AgentActivityFeed } from '@/components/intelligence/AgentActivityFeed';

type TabId = 'disagreement' | 'history' | 'performance';

interface Tab {
  id: TabId;
  label: string;
  description: string;
  icon: string;
}

const tabs: Tab[] = [
  {
    id: 'disagreement',
    label: 'Agent Disagreement',
    description: 'View agent consensus and disagreement analysis',
    icon: '🤝'
  },
  {
    id: 'history',
    label: 'Decision History',
    description: 'Explore agent decisions and pattern detection',
    icon: '📜'
  },
  {
    id: 'performance',
    label: 'Performance & Activity',
    description: 'Compare agent performance and monitor real-time activity',
    icon: '📊'
  }
];

export default function IntelligencePage() {
  const [activeTab, setActiveTab] = useState<TabId>('performance');

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center gap-3">
            <div className="text-4xl">🧠</div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                Agent Intelligence Insights
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Comprehensive AI agent analysis and monitoring
              </p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-1 border-b border-gray-200 dark:border-gray-700">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  relative px-6 py-3 font-medium text-sm transition-colors
                  ${
                    activeTab === tab.id
                      ? 'text-blue-600 dark:text-blue-400'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                  }
                `}
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">{tab.icon}</span>
                  <span>{tab.label}</span>
                </div>
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600 dark:bg-blue-400" />
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab Description */}
        <div className="mb-6">
          <p className="text-gray-600 dark:text-gray-400">
            {tabs.find((t) => t.id === activeTab)?.description}
          </p>
        </div>

        {/* Story 7.1: Agent Disagreement */}
        {activeTab === 'disagreement' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Agent Disagreement Analysis
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Monitor consensus levels across all 8 AI agents. View individual agent positions,
                confidence levels, and reasoning to understand decision-making diversity.
              </p>
              <AgentDisagreementPanel symbol="EUR/USD" />
            </div>

            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="text-2xl">💡</div>
                <div>
                  <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                    Understanding Consensus
                  </h3>
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    High consensus (≥70%) indicates strong agreement among agents. Lower consensus
                    suggests divergent opinions and requires careful analysis before trading.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Story 7.2: Decision History */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Agent Decision History
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Review past agent decisions with pattern detection overlays. Analyze Wyckoff patterns,
                entry/exit points, and trade outcomes to understand agent performance over time.
              </p>
              <DecisionHistorySection symbol="EUR/USD" />
            </div>

            <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="text-2xl">🔍</div>
                <div>
                  <h3 className="font-semibold text-purple-900 dark:text-purple-100 mb-1">
                    Pattern Recognition
                  </h3>
                  <p className="text-sm text-purple-800 dark:text-purple-200">
                    Click on any trade to view detailed pattern overlays. Wyckoff methodology patterns
                    include accumulation, distribution, spring, and upthrust formations.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Story 7.3: Performance & Activity */}
        {activeTab === 'performance' && (
          <div className="space-y-6">
            {/* Performance Dashboard */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <AgentPerformanceDashboard />
            </div>

            {/* Activity Feed */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  Real-Time Agent Activity
                </h2>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  Live feed of agent signals, trades, patterns, and decisions
                </p>
              </div>
              <div style={{ height: '600px' }}>
                <AgentActivityFeed />
              </div>
            </div>

            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <div className="text-2xl">🏆</div>
                <div>
                  <h3 className="font-semibold text-green-900 dark:text-green-100 mb-1">
                    Performance Metrics
                  </h3>
                  <p className="text-sm text-green-800 dark:text-green-200">
                    Top performers are ranked by win rate. Expand cards to see best trading pairs,
                    session-specific performance, and recent activity. Use time period selector to
                    analyze different timeframes.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
