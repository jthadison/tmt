/**
 * AgentPositionCard Component Tests
 *
 * Story 7.1: AC5 - Test agent position card display
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { AgentPositionCard } from '@/components/intelligence/AgentPositionCard';
import { AgentPosition } from '@/types/intelligence';

const mockPosition: AgentPosition = {
  agentId: 'market-analysis',
  agentName: 'Market Analysis',
  action: 'BUY',
  confidence: 85,
  reasoning: [
    'Strong bullish momentum detected',
    'Price broke above resistance at 1.0850'
  ],
  timestamp: Date.now()
};

describe('AgentPositionCard', () => {
  describe('Content Display', () => {
    it('displays agent name', () => {
      render(<AgentPositionCard position={mockPosition} />);

      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
    });

    it('displays action badge', () => {
      render(<AgentPositionCard position={mockPosition} />);

      expect(screen.getByText('BUY')).toBeInTheDocument();
    });

    it('displays confidence percentage', () => {
      render(<AgentPositionCard position={mockPosition} />);

      expect(screen.getByText('85% - High')).toBeInTheDocument();
    });

    it('displays all reasoning points', () => {
      render(<AgentPositionCard position={mockPosition} />);

      expect(screen.getByText('Strong bullish momentum detected')).toBeInTheDocument();
      expect(screen.getByText('Price broke above resistance at 1.0850')).toBeInTheDocument();
    });

    it('displays formatted timestamp', () => {
      const fixedTime = new Date('2024-01-01T12:30:45').getTime();
      const position = { ...mockPosition, timestamp: fixedTime };

      render(<AgentPositionCard position={position} />);

      expect(screen.getByText(/12:30:45/)).toBeInTheDocument();
    });
  });

  describe('Action Color Coding', () => {
    it('displays BUY action in green', () => {
      const buyPosition = { ...mockPosition, action: 'BUY' as const };
      render(<AgentPositionCard position={buyPosition} />);

      const actionText = screen.getByText('BUY');
      expect(actionText).toHaveClass('text-green-600');
    });

    it('displays SELL action in red', () => {
      const sellPosition = { ...mockPosition, action: 'SELL' as const };
      render(<AgentPositionCard position={sellPosition} />);

      const actionText = screen.getByText('SELL');
      expect(actionText).toHaveClass('text-red-600');
    });

    it('displays NEUTRAL action in gray', () => {
      const neutralPosition = { ...mockPosition, action: 'NEUTRAL' as const };
      render(<AgentPositionCard position={neutralPosition} />);

      const actionText = screen.getByText('NEUTRAL');
      expect(actionText).toHaveClass('text-gray-600');
    });
  });

  describe('Agent Icon', () => {
    it('renders agent icon', () => {
      render(<AgentPositionCard position={mockPosition} />);

      const icon = screen.getByTestId('agent-icon');
      expect(icon).toBeInTheDocument();
    });

    it('displays correct icon for agent', () => {
      render(<AgentPositionCard position={mockPosition} />);

      const icon = screen.getByTestId('agent-icon');
      expect(icon).toHaveTextContent('📊'); // Market Analysis icon
    });
  });

  describe('Confidence Meter Integration', () => {
    it('renders confidence meter component', () => {
      render(<AgentPositionCard position={mockPosition} />);

      const confidenceMeter = screen.getByTestId('confidence-meter');
      expect(confidenceMeter).toBeInTheDocument();
    });

    it('passes correct confidence value to meter', () => {
      render(<AgentPositionCard position={mockPosition} />);

      const confidenceBar = screen.getByTestId('confidence-bar');
      expect(confidenceBar).toHaveStyle({ width: '85%' });
    });
  });

  describe('Reasoning Display', () => {
    it('shows reasoning section header', () => {
      render(<AgentPositionCard position={mockPosition} />);

      expect(screen.getByText('Reasoning:')).toBeInTheDocument();
    });

    it('handles empty reasoning array', () => {
      const positionNoReasoning = { ...mockPosition, reasoning: [] };
      render(<AgentPositionCard position={positionNoReasoning} />);

      expect(screen.queryByText('Reasoning:')).not.toBeInTheDocument();
    });

    it('displays multiple reasoning points as bullets', () => {
      const positionMultiple = {
        ...mockPosition,
        reasoning: ['Point 1', 'Point 2', 'Point 3']
      };
      render(<AgentPositionCard position={positionMultiple} />);

      expect(screen.getByText('Point 1')).toBeInTheDocument();
      expect(screen.getByText('Point 2')).toBeInTheDocument();
      expect(screen.getByText('Point 3')).toBeInTheDocument();
    });

    it('limits reasoning to 3 points as per spec', () => {
      const position3Points = {
        ...mockPosition,
        reasoning: [
          'Strong bullish momentum',
          'Resistance break confirmed',
          'London session optimized'
        ]
      };
      render(<AgentPositionCard position={position3Points} />);

      const reasoningItems = screen.getAllByText(/Strong bullish|Resistance break|London session/);
      expect(reasoningItems).toHaveLength(3);
    });
  });

  describe('Accessibility', () => {
    it('includes data-testid for card', () => {
      render(<AgentPositionCard position={mockPosition} />);

      expect(screen.getByTestId('agent-position-card')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles different agents correctly', () => {
      const patternDetectionPosition = {
        ...mockPosition,
        agentId: 'pattern-detection',
        agentName: 'Pattern Detection'
      };
      render(<AgentPositionCard position={patternDetectionPosition} />);

      expect(screen.getByText('Pattern Detection')).toBeInTheDocument();
      const icon = screen.getByTestId('agent-icon');
      expect(icon).toHaveTextContent('🔍'); // Pattern Detection icon
    });

    it('handles very low confidence', () => {
      const lowConfidencePosition = { ...mockPosition, confidence: 15 };
      render(<AgentPositionCard position={lowConfidencePosition} />);

      expect(screen.getByText('15% - Very Low')).toBeInTheDocument();
    });

    it('handles very high confidence', () => {
      const highConfidencePosition = { ...mockPosition, confidence: 95 };
      render(<AgentPositionCard position={highConfidencePosition} />);

      expect(screen.getByText('95% - Very High')).toBeInTheDocument();
    });
  });
});
