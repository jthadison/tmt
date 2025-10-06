/**
 * ActivityEventCard Component Tests
 * Story 7.3: AC6 - Activity Event Card with Animation
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ActivityEventCard } from '@/components/intelligence/ActivityEventCard';
import { AgentActivityEvent } from '@/types/intelligence';

const mockEvent: AgentActivityEvent = {
  eventId: 'evt-12345',
  eventType: 'signal_generated',
  timestamp: Date.now() - 120000, // 2 minutes ago
  agentId: 'market-analysis',
  agentName: 'Market Analysis',
  symbol: 'EUR/USD',
  action: 'BUY',
  confidence: 85,
  reasoning: ['Strong bullish momentum detected', 'Resistance break confirmed']
};

describe('ActivityEventCard', () => {
  describe('Display', () => {
    it('displays agent name', () => {
      render(<ActivityEventCard event={mockEvent} />);

      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
    });

    it('displays symbol in monospace font', () => {
      render(<ActivityEventCard event={mockEvent} />);

      const symbol = screen.getByText('EUR/USD');
      expect(symbol).toHaveClass('font-mono');
    });

    it('displays confidence percentage', () => {
      render(<ActivityEventCard event={mockEvent} />);

      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('displays relative timestamp', () => {
      render(<ActivityEventCard event={mockEvent} />);

      expect(screen.getByText('2m ago')).toBeInTheDocument();
    });

    it('displays action badge', () => {
      render(<ActivityEventCard event={mockEvent} />);

      expect(screen.getByTestId('action-badge')).toHaveTextContent('BUY');
    });
  });

  describe('Event Type Icons', () => {
    it('shows correct icon for signal_generated', () => {
      const event = { ...mockEvent, eventType: 'signal_generated' as const };
      const { container } = render(<ActivityEventCard event={event} />);

      // Check for blue color class
      const icon = container.querySelector('.text-blue-600');
      expect(icon).toBeInTheDocument();
    });

    it('shows correct icon for trade_executed', () => {
      const event = { ...mockEvent, eventType: 'trade_executed' as const };
      const { container } = render(<ActivityEventCard event={event} />);

      // Check for green color class
      const icon = container.querySelector('.text-green-600');
      expect(icon).toBeInTheDocument();
    });

    it('shows correct icon for pattern_detected', () => {
      const event = { ...mockEvent, eventType: 'pattern_detected' as const };
      const { container } = render(<ActivityEventCard event={event} />);

      // Check for purple color class
      const icon = container.querySelector('.text-purple-600');
      expect(icon).toBeInTheDocument();
    });

    it('shows correct icon for disagreement_resolved', () => {
      const event = { ...mockEvent, eventType: 'disagreement_resolved' as const };
      const { container } = render(<ActivityEventCard event={event} />);

      // Check for yellow color class
      const icon = container.querySelector('.text-yellow-600');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Reasoning Display', () => {
    it('displays first reasoning point by default', () => {
      render(<ActivityEventCard event={mockEvent} />);

      expect(screen.getByText('Strong bullish momentum detected')).toBeInTheDocument();
    });

    it('shows expand button when multiple reasoning points exist', () => {
      render(<ActivityEventCard event={mockEvent} />);

      expect(screen.getByText('+1 more')).toBeInTheDocument();
    });

    it('expands to show all reasoning when clicked', () => {
      render(<ActivityEventCard event={mockEvent} />);

      const expandButton = screen.getByText('+1 more');
      fireEvent.click(expandButton);

      expect(screen.getByText('Strong bullish momentum detected')).toBeInTheDocument();
      expect(screen.getByText('Resistance break confirmed')).toBeInTheDocument();
    });

    it('changes to "Show less" when expanded', () => {
      render(<ActivityEventCard event={mockEvent} />);

      const expandButton = screen.getByText('+1 more');
      fireEvent.click(expandButton);

      expect(screen.getByText('Show less')).toBeInTheDocument();
    });

    it('collapses when "Show less" is clicked', () => {
      render(<ActivityEventCard event={mockEvent} />);

      const expandButton = screen.getByText('+1 more');
      fireEvent.click(expandButton);

      const collapseButton = screen.getByText('Show less');
      fireEvent.click(collapseButton);

      expect(screen.getByText('+1 more')).toBeInTheDocument();
    });

    it('does not show expand button for single reasoning point', () => {
      const singleReasonEvent = { ...mockEvent, reasoning: ['Single reason'] };
      render(<ActivityEventCard event={singleReasonEvent} />);

      expect(screen.queryByText(/more/)).not.toBeInTheDocument();
    });
  });

  describe('Metadata Display', () => {
    it('displays consensus percentage when present', () => {
      const eventWithConsensus = {
        ...mockEvent,
        metadata: { consensusPercentage: 75 }
      };
      render(<ActivityEventCard event={eventWithConsensus} />);

      expect(screen.getByText('Consensus: 75%')).toBeInTheDocument();
    });

    it('displays pattern type when present', () => {
      const eventWithPattern = {
        ...mockEvent,
        metadata: { patternType: 'wyckoff-accumulation' }
      };
      render(<ActivityEventCard event={eventWithPattern} />);

      // Pattern type is transformed: hyphens to spaces, capitalized
      expect(screen.getByText(/wyckoff accumulation/i)).toBeInTheDocument();
    });

    it('displays session context when present', () => {
      const eventWithSession = {
        ...mockEvent,
        metadata: { sessionContext: 'London' }
      };
      render(<ActivityEventCard event={eventWithSession} />);

      expect(screen.getByText('London')).toBeInTheDocument();
    });

    it('displays P/L when present', () => {
      const eventWithPnL = {
        ...mockEvent,
        metadata: { pnl: 125.50 }
      };
      render(<ActivityEventCard event={eventWithPnL} />);

      expect(screen.getByText('P/L: $125.50')).toBeInTheDocument();
    });

    it('displays negative P/L in red', () => {
      const eventWithLoss = {
        ...mockEvent,
        metadata: { pnl: -50.25 }
      };
      const { container } = render(<ActivityEventCard event={eventWithLoss} />);

      const pnlElement = screen.getByText('P/L: $-50.25');
      expect(pnlElement).toHaveClass('text-red-600');
    });

    it('displays positive P/L in green', () => {
      const eventWithProfit = {
        ...mockEvent,
        metadata: { pnl: 100.00 }
      };
      const { container } = render(<ActivityEventCard event={eventWithProfit} />);

      const pnlElement = screen.getByText('P/L: $100.00');
      expect(pnlElement).toHaveClass('text-green-600');
    });
  });

  describe('Relative Time Formatting', () => {
    it('shows "Just now" for very recent events', () => {
      const recentEvent = { ...mockEvent, timestamp: Date.now() - 5000 }; // 5 seconds ago
      render(<ActivityEventCard event={recentEvent} />);

      expect(screen.getByText('Just now')).toBeInTheDocument();
    });

    it('shows minutes ago for events < 1 hour', () => {
      const minutesAgo = { ...mockEvent, timestamp: Date.now() - 1800000 }; // 30 minutes ago
      render(<ActivityEventCard event={minutesAgo} />);

      expect(screen.getByText('30m ago')).toBeInTheDocument();
    });

    it('shows hours ago for events < 1 day', () => {
      const hoursAgo = { ...mockEvent, timestamp: Date.now() - 7200000 }; // 2 hours ago
      render(<ActivityEventCard event={hoursAgo} />);

      expect(screen.getByText('2h ago')).toBeInTheDocument();
    });

    it('shows days ago for events >= 1 day', () => {
      const daysAgo = { ...mockEvent, timestamp: Date.now() - 172800000 }; // 2 days ago
      render(<ActivityEventCard event={daysAgo} />);

      expect(screen.getByText('2d ago')).toBeInTheDocument();
    });
  });
});
