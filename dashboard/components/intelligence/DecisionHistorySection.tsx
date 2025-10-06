/**
 * Decision History Section
 * Wrapper component that fetches and displays agent decision history
 */

'use client';

import React, { useEffect, useState } from 'react';
import { EnhancedTradeRecord } from '@/types/intelligence';
import { AgentDecisionHistoryCard } from './AgentDecisionHistoryCard';

interface DecisionHistorySectionProps {
  symbol?: string;
}

// Mock trade data for demonstration
function createMockTrade(symbol: string): EnhancedTradeRecord {
  return {
    id: 'mock-trade-1',
    symbol,
    action: 'BUY',
    price: 1.0850,
    quantity: 10000,
    timestamp: Date.now() - 3600000, // 1 hour ago
    outcome: 'WIN',
    profitLoss: 145.50,
    agentAttribution: {
      primaryAgent: {
        agentId: 'market-analysis',
        agentName: 'Market Analysis',
        confidence: 85,
        reasoning: [
          'Strong bullish momentum detected on 4H timeframe',
          'Price broke above key resistance at 1.0820',
          'Volume confirms breakout validity'
        ]
      },
      confirmingAgents: [
        {
          agentId: 'pattern-detection',
          agentName: 'Pattern Detection',
          confidence: 78,
          reasoning: [
            'Wyckoff accumulation Phase E identified',
            'Sign of Strength (SOS) confirmed at 1.0815'
          ]
        },
        {
          agentId: 'strategy-analysis',
          agentName: 'Strategy Analysis',
          confidence: 72,
          reasoning: [
            'London session provides optimal liquidity',
            'Risk-reward ratio of 3.2 meets criteria'
          ]
        }
      ],
      consensusPercentage: 78,
      finalDecision: 'BUY',
      sessionContext: 'London'
    },
    patternDetected: {
      patternType: 'wyckoff-accumulation',
      confidence: 78,
      keyLevels: {
        entry: 1.0850,
        target: 1.0920,
        stopLoss: 1.0825
      }
    }
  };
}

export function DecisionHistorySection({ symbol = 'EUR/USD' }: DecisionHistorySectionProps) {
  const [trade, setTrade] = useState<EnhancedTradeRecord | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API call
    const fetchTradeHistory = async () => {
      setLoading(true);
      try {
        // TODO: Replace with actual API call to fetch recent trade with agent attribution
        // const response = await fetch(`/api/trades/history?symbol=${symbol}&withAttribution=true&limit=1`);
        // const data = await response.json();

        // For now, use mock data
        await new Promise(resolve => setTimeout(resolve, 500));
        const mockTrade = createMockTrade(symbol);
        setTrade(mockTrade);
      } catch (error) {
        console.error('Failed to fetch trade history:', error);
        // Still show mock data on error
        setTrade(createMockTrade(symbol));
      } finally {
        setLoading(false);
      }
    };

    fetchTradeHistory();
  }, [symbol]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 dark:border-blue-400"></div>
      </div>
    );
  }

  if (!trade) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 dark:text-gray-400">No trade history available</p>
      </div>
    );
  }

  return <AgentDecisionHistoryCard trade={trade} />;
}
