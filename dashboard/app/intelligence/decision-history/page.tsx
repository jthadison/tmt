/**
 * Agent Decision History Demo Page
 * Showcases Story 7.2 features: decision history and pattern overlays
 */

'use client';

import React, { useState } from 'react';
import { AgentDecisionHistoryCard } from '@/components/intelligence/AgentDecisionHistoryCard';
import { SimilarPatternsModal } from '@/components/intelligence/SimilarPatternsModal';
import { EnhancedTradeRecord } from '@/types/intelligence';

export default function DecisionHistoryPage() {
  const [showSimilarPatterns, setShowSimilarPatterns] = useState(false);
  const [selectedPattern, setSelectedPattern] = useState<string>('wyckoff-accumulation');

  // Mock trade data for demonstration
  const mockTrade: EnhancedTradeRecord = {
    id: 'trade-demo-001',
    symbol: 'EUR_USD',
    action: 'BUY',
    price: 1.0850,
    quantity: 10000,
    timestamp: Date.now() - 2 * 60 * 60 * 1000, // 2 hours ago
    outcome: 'WIN',
    profitLoss: 125.50,
    agentAttribution: {
      primaryAgent: {
        agentId: 'market-analysis',
        agentName: 'Market Analysis',
        confidence: 85,
        reasoning: [
          'Strong bullish momentum (RSI: 72)',
          'Price broke above resistance at 1.0850',
          'London session optimal for EUR strength',
          'Volume spike confirms buying pressure'
        ]
      },
      confirmingAgents: [
        {
          agentId: 'pattern-detection',
          agentName: 'Pattern Detection',
          confidence: 78,
          reasoning: [
            'Wyckoff accumulation Phase E detected',
            'Sign of Strength (SOS) confirmed',
            'Spring pattern completed successfully'
          ]
        },
        {
          agentId: 'strategy-analysis',
          agentName: 'Strategy Analysis',
          confidence: 72,
          reasoning: [
            'London session win rate: 68%',
            'EUR_USD performance strong this week',
            'Risk-reward ratio favorable at 3.5:1'
          ]
        }
      ],
      consensusPercentage: 78,
      finalDecision: 'BUY',
      sessionContext: 'London Session'
    },
    patternDetected: {
      patternType: 'Wyckoff Accumulation Phase E',
      confidence: 78,
      keyLevels: {
        entry: 1.0850,
        target: 1.0920,
        stopLoss: 1.0800
      }
    }
  };

  const mockTradeWithoutAttribution: EnhancedTradeRecord = {
    id: 'trade-demo-002',
    symbol: 'GBP_USD',
    action: 'SELL',
    price: 1.2650,
    quantity: 5000,
    timestamp: Date.now() - 5 * 60 * 60 * 1000, // 5 hours ago
    outcome: 'LOSS',
    profitLoss: -45.20
  };

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          Agent Decision History & Pattern Detection
        </h1>
        <p className="text-secondary">
          Story 7.2: View historical agent reasoning and pattern detection overlays
        </p>
      </div>

      {/* Trade with full attribution */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4 text-foreground">
          Example 1: Trade with Full Agent Attribution
        </h2>
        <AgentDecisionHistoryCard trade={mockTrade} />

        <div className="mt-4 flex gap-3">
          <button
            onClick={() => {
              setSelectedPattern('wyckoff-accumulation');
              setShowSimilarPatterns(true);
            }}
            className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
          >
            View Similar Wyckoff Patterns
          </button>
          <button
            onClick={() => {
              setSelectedPattern('spring');
              setShowSimilarPatterns(true);
            }}
            className="px-4 py-2 bg-secondary text-white rounded-lg hover:bg-secondary/90 transition-colors"
          >
            View Similar Spring Patterns
          </button>
        </div>
      </div>

      {/* Trade without attribution */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold mb-4 text-foreground">
          Example 2: Trade Without Agent Attribution (Backward Compatible)
        </h2>
        <AgentDecisionHistoryCard trade={mockTradeWithoutAttribution} />
      </div>

      {/* Feature Overview */}
      <div className="mb-8 p-6 bg-card border border-border rounded-lg">
        <h2 className="text-xl font-semibold mb-4 text-foreground">Story 7.2 Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FeatureCard
            title="Agent Decision History"
            description="View which agents triggered trades, their confidence levels, and reasoning"
            status="Implemented"
          />
          <FeatureCard
            title="Pattern Detection Overlays"
            description="Visual annotations on charts showing entry points, targets, and support/resistance"
            status="Implemented"
          />
          <FeatureCard
            title="Pattern Tooltips"
            description="Hover over pattern annotations to see detailed pattern analysis"
            status="Implemented"
          />
          <FeatureCard
            title="Similar Patterns Modal"
            description="View historical trades with similar patterns and performance statistics"
            status="Implemented"
          />
        </div>
      </div>

      {/* Similar Patterns Modal */}
      <SimilarPatternsModal
        patternType={selectedPattern}
        isOpen={showSimilarPatterns}
        onClose={() => setShowSimilarPatterns(false)}
        symbol="EUR_USD"
      />
    </div>
  );
}

interface FeatureCardProps {
  title: string;
  description: string;
  status: string;
}

function FeatureCard({ title, description, status }: FeatureCardProps) {
  return (
    <div className="p-4 bg-surface border border-border rounded-lg">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-foreground">{title}</h3>
        <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 text-xs rounded">
          {status}
        </span>
      </div>
      <p className="text-sm text-secondary">{description}</p>
    </div>
  );
}
