/**
 * Unit tests for AgentDecisionHistoryCard component
 * Story 7.2: AC2
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { AgentDecisionHistoryCard } from '@/components/intelligence/AgentDecisionHistoryCard';
import { EnhancedTradeRecord } from '@/types/intelligence';

describe('AgentDecisionHistoryCard', () => {
  const mockTradeWithAttribution: EnhancedTradeRecord = {
    id: 'trade-12345',
    symbol: 'EUR_USD',
    action: 'BUY',
    price: 1.0850,
    quantity: 10000,
    timestamp: 1696000000000,
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
          'London session optimal for EUR strength'
        ]
      },
      confirmingAgents: [
        {
          agentId: 'pattern-detection',
          agentName: 'Pattern Detection',
          confidence: 78,
          reasoning: [
            'Wyckoff accumulation Phase E detected',
            'Sign of Strength (SOS) confirmed'
          ]
        }
      ],
      consensusPercentage: 75,
      finalDecision: 'BUY',
      sessionContext: 'London session'
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
    id: 'trade-67890',
    symbol: 'GBP_USD',
    action: 'SELL',
    price: 1.2650,
    quantity: 5000,
    timestamp: 1696100000000
  };

  test('renders card with agent attribution', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithAttribution} />);

    expect(screen.getByText('Agent Decision History')).toBeInTheDocument();
    expect(screen.getByTestId('agent-decision-history-card')).toBeInTheDocument();
  });

  test('displays primary agent information', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithAttribution} />);

    expect(screen.getByText('Market Analysis')).toBeInTheDocument();
    expect(screen.getByText(/Strong bullish momentum/)).toBeInTheDocument();
  });

  test('displays confirming agents', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithAttribution} />);

    expect(screen.getByText(/Confirming Agents \(1\)/)).toBeInTheDocument();
    expect(screen.getByText('Pattern Detection')).toBeInTheDocument();
  });

  test('displays consensus percentage', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithAttribution} />);

    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('Consensus at Trade Time')).toBeInTheDocument();
  });

  test('displays session context when available', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithAttribution} />);

    expect(screen.getByText('London session')).toBeInTheDocument();
  });

  test('displays outcome badge when outcome exists', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithAttribution} />);

    expect(screen.getByTestId('outcome-badge')).toBeInTheDocument();
    expect(screen.getByText('WIN')).toBeInTheDocument();
    expect(screen.getByText('+$125.50')).toBeInTheDocument();
  });

  test('displays pattern detected section when pattern exists', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithAttribution} />);

    expect(screen.getByText('Pattern Detected')).toBeInTheDocument();
    expect(screen.getByText('Wyckoff Accumulation Phase E')).toBeInTheDocument();
    expect(screen.getByText('1.085')).toBeInTheDocument(); // Entry
    expect(screen.getByText('1.092')).toBeInTheDocument(); // Target
    expect(screen.getByText('1.08')).toBeInTheDocument(); // Stop Loss
  });

  test('shows empty state when no agent attribution', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithoutAttribution} />);

    expect(screen.getByText(/No agent attribution data available/)).toBeInTheDocument();
  });

  test('renders all reasoning points for primary agent', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithAttribution} />);

    expect(screen.getByText(/Strong bullish momentum/)).toBeInTheDocument();
    expect(screen.getByText(/Price broke above resistance/)).toBeInTheDocument();
    expect(screen.getByText(/London session optimal/)).toBeInTheDocument();
  });

  test('renders confirming agent card for each confirming agent', () => {
    render(<AgentDecisionHistoryCard trade={mockTradeWithAttribution} />);

    expect(screen.getByTestId('confirming-agent-pattern-detection')).toBeInTheDocument();
  });

  test('does not show confirming agents section when no confirming agents', () => {
    const tradeWithoutConfirmingAgents = {
      ...mockTradeWithAttribution,
      agentAttribution: {
        ...mockTradeWithAttribution.agentAttribution!,
        confirmingAgents: []
      }
    };

    render(<AgentDecisionHistoryCard trade={tradeWithoutConfirmingAgents} />);

    expect(screen.queryByText(/Confirming Agents/)).not.toBeInTheDocument();
  });

  test('does not show pattern section when no pattern detected', () => {
    const tradeWithoutPattern = {
      ...mockTradeWithAttribution,
      patternDetected: undefined
    };

    render(<AgentDecisionHistoryCard trade={tradeWithoutPattern} />);

    expect(screen.queryByText('Pattern Detected')).not.toBeInTheDocument();
  });
});
