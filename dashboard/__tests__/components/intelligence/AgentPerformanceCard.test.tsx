/**
 * AgentPerformanceCard Component Tests
 * Story 7.3: AC3 - Agent Performance Card with Details
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { AgentPerformanceCard } from '@/components/intelligence/AgentPerformanceCard';
import { AgentPerformanceData } from '@/types/intelligence';

const mockAgent: AgentPerformanceData = {
  agentId: 'market-analysis',
  agentName: 'Market Analysis',
  metrics: {
    winRate: 75.5,
    avgProfit: 145.30,
    avgLoss: -82.50,
    totalSignals: 450,
    totalTrades: 280,
    profitFactor: 2.4,
    maxDrawdown: -1250.00
  },
  bestPairs: [
    { symbol: 'EUR/USD', winRate: 72.0, totalTrades: 85, avgProfit: 165.20 },
    { symbol: 'GBP/USD', winRate: 65.5, totalTrades: 62, avgProfit: 138.75 }
  ],
  sessionPerformance: [
    { session: 'London', winRate: 75.0, totalTrades: 120 },
    { session: 'NY', winRate: 63.2, totalTrades: 95 }
  ],
  recentActivity: {
    last7Days: 42,
    last30Days: 180
  }
};

describe('AgentPerformanceCard', () => {
  describe('Display', () => {
    it('displays agent name and rank', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={true} />);

      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
      expect(screen.getByText('Rank #1')).toBeInTheDocument();
    });

    it('displays win rate with correct formatting', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      expect(screen.getByText('75.5%')).toBeInTheDocument();
    });

    it('displays average profit', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      expect(screen.getByText('$145.30')).toBeInTheDocument();
    });

    it('displays total signals', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      expect(screen.getByText('450')).toBeInTheDocument();
    });
  });

  describe('Win Rate Color Coding', () => {
    it('displays green for win rate >= 70%', () => {
      const highWinAgent = { ...mockAgent, metrics: { ...mockAgent.metrics, winRate: 75 } };
      const { container } = render(<AgentPerformanceCard agent={highWinAgent} rank={1} showMedal={false} />);

      const winRateBadge = screen.getByText('75.0%').parentElement;
      expect(winRateBadge).toHaveClass('text-green-600');
    });

    it('displays yellow for win rate 60-69%', () => {
      const mediumWinAgent = { ...mockAgent, metrics: { ...mockAgent.metrics, winRate: 65 } };
      render(<AgentPerformanceCard agent={mediumWinAgent} rank={1} showMedal={false} />);

      const winRateBadge = screen.getByText('65.0%').parentElement;
      expect(winRateBadge).toHaveClass('text-yellow-600');
    });

    it('displays red for win rate < 60%', () => {
      const lowWinAgent = { ...mockAgent, metrics: { ...mockAgent.metrics, winRate: 55 } };
      render(<AgentPerformanceCard agent={lowWinAgent} rank={1} showMedal={false} />);

      const winRateBadge = screen.getByText('55.0%').parentElement;
      expect(winRateBadge).toHaveClass('text-red-600');
    });
  });

  describe('Medal Display', () => {
    it('shows gold medal for rank 1', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={true} />);

      const medal = screen.getByTestId('medal-icon');
      expect(medal).toHaveTextContent('🥇');
    });

    it('shows silver medal for rank 2', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={2} showMedal={true} />);

      const medal = screen.getByTestId('medal-icon');
      expect(medal).toHaveTextContent('🥈');
    });

    it('shows bronze medal for rank 3', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={3} showMedal={true} />);

      const medal = screen.getByTestId('medal-icon');
      expect(medal).toHaveTextContent('🥉');
    });

    it('does not show medal when showMedal is false', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      const medal = screen.queryByTestId('medal-icon');
      expect(medal).not.toBeInTheDocument();
    });
  });

  describe('Expandable Details', () => {
    it('shows "View Details" button initially', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      expect(screen.getByText('View Details')).toBeInTheDocument();
    });

    it('expands to show best pairs when clicked', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      const viewButton = screen.getByText('View Details');
      fireEvent.click(viewButton);

      expect(screen.getByText('Best Performing Pairs')).toBeInTheDocument();
      expect(screen.getByText('EUR/USD')).toBeInTheDocument();
      expect(screen.getByText('GBP/USD')).toBeInTheDocument();
    });

    it('expands to show session performance when clicked', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      const viewButton = screen.getByText('View Details');
      fireEvent.click(viewButton);

      expect(screen.getByText('Session Performance')).toBeInTheDocument();
      expect(screen.getByText('London')).toBeInTheDocument();
      expect(screen.getByText('NY')).toBeInTheDocument();
    });

    it('shows profit factor and trades when expanded', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      const viewButton = screen.getByText('View Details');
      fireEvent.click(viewButton);

      expect(screen.getByText('Profit Factor')).toBeInTheDocument();
      expect(screen.getByText('2.40')).toBeInTheDocument();
      expect(screen.getByText('Trades (30d)')).toBeInTheDocument();
      expect(screen.getByText('180')).toBeInTheDocument();
    });

    it('changes button text to "Hide Details" when expanded', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      const viewButton = screen.getByText('View Details');
      fireEvent.click(viewButton);

      expect(screen.getByText('Hide Details')).toBeInTheDocument();
    });

    it('collapses when "Hide Details" is clicked', () => {
      render(<AgentPerformanceCard agent={mockAgent} rank={1} showMedal={false} />);

      const viewButton = screen.getByText('View Details');
      fireEvent.click(viewButton);

      const hideButton = screen.getByText('Hide Details');
      fireEvent.click(hideButton);

      expect(screen.queryByText('Best Performing Pairs')).not.toBeInTheDocument();
      expect(screen.getByText('View Details')).toBeInTheDocument();
    });
  });

  describe('Data Display', () => {
    it('renders without crashing with minimal data', () => {
      const minimalAgent: AgentPerformanceData = {
        agentId: 'test-agent',
        agentName: 'Test Agent',
        metrics: {
          winRate: 50,
          avgProfit: 100,
          avgLoss: -50,
          totalSignals: 10,
          totalTrades: 5,
          profitFactor: 2.0
        },
        bestPairs: [],
        recentActivity: {
          last7Days: 1,
          last30Days: 5
        }
      };

      render(<AgentPerformanceCard agent={minimalAgent} rank={5} showMedal={false} />);

      expect(screen.getByText('Test Agent')).toBeInTheDocument();
    });
  });
});
