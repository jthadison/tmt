/**
 * AgentDisagreementPanel Component Tests
 *
 * Story 7.1: AC3 - Test agent disagreement panel integration
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { AgentDisagreementPanel } from '@/components/intelligence/AgentDisagreementPanel';
import * as intelligenceApi from '@/services/api/intelligence';
import { DisagreementData } from '@/types/intelligence';

// Mock the intelligence API
jest.mock('@/services/api/intelligence');

const mockDisagreementData: DisagreementData = {
  symbol: 'EUR_USD',
  timestamp: Date.now(),
  consensusPercentage: 75,
  finalDecision: 'BUY',
  thresholdMet: true,
  requiredThreshold: 70,
  agentPositions: [
    {
      agentId: 'market-analysis',
      agentName: 'Market Analysis',
      action: 'BUY',
      confidence: 85,
      reasoning: ['Strong bullish momentum', 'Resistance break confirmed'],
      timestamp: Date.now()
    },
    {
      agentId: 'pattern-detection',
      agentName: 'Pattern Detection',
      action: 'BUY',
      confidence: 78,
      reasoning: ['Wyckoff accumulation detected'],
      timestamp: Date.now()
    },
    {
      agentId: 'strategy-analysis',
      agentName: 'Strategy Analysis',
      action: 'NEUTRAL',
      confidence: 45,
      reasoning: ['Recent win rate below target'],
      timestamp: Date.now()
    },
    {
      agentId: 'parameter-optimization',
      agentName: 'Parameter Optimization',
      action: 'BUY',
      confidence: 72,
      reasoning: ['Risk parameters optimized'],
      timestamp: Date.now()
    },
    {
      agentId: 'learning-safety',
      agentName: 'Learning Safety',
      action: 'BUY',
      confidence: 80,
      reasoning: ['No anomalies detected'],
      timestamp: Date.now()
    },
    {
      agentId: 'disagreement-engine',
      agentName: 'Disagreement Engine',
      action: 'BUY',
      confidence: 75,
      reasoning: ['Consensus threshold met'],
      timestamp: Date.now()
    },
    {
      agentId: 'data-collection',
      agentName: 'Data Collection',
      action: 'BUY',
      confidence: 70,
      reasoning: ['Data quality verified'],
      timestamp: Date.now()
    },
    {
      agentId: 'continuous-improvement',
      agentName: 'Continuous Improvement',
      action: 'SELL',
      confidence: 55,
      reasoning: ['Recent performance decline'],
      timestamp: Date.now()
    }
  ]
};

describe('AgentDisagreementPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Visibility Control', () => {
    it('renders nothing when isExpanded is false', () => {
      const { container } = render(
        <AgentDisagreementPanel symbol="EUR_USD" isExpanded={false} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('renders panel when isExpanded is true', async () => {
      (intelligenceApi.fetchDisagreementData as jest.Mock).mockResolvedValue(
        mockDisagreementData
      );

      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={true} />);

      await waitFor(() => {
        expect(screen.getByText('Agent Consensus')).toBeInTheDocument();
      });
    });
  });

  describe('Loading State', () => {
    it('displays loading indicator while fetching data', () => {
      (intelligenceApi.fetchDisagreementData as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      );

      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={true} />);

      expect(screen.getByText(/Loading agent disagreement data/i)).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('displays error message when fetch fails', async () => {
      (intelligenceApi.fetchDisagreementData as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );

      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={true} />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load disagreement data/i)).toBeInTheDocument();
        expect(screen.getByText(/Network error/i)).toBeInTheDocument();
      });
    });
  });

  describe('Consensus Display', () => {
    beforeEach(async () => {
      (intelligenceApi.fetchDisagreementData as jest.Mock).mockResolvedValue(
        mockDisagreementData
      );

      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={true} />);

      await waitFor(() => {
        expect(screen.getByText('Agent Consensus')).toBeInTheDocument();
      });
    });

    it('displays consensus percentage', () => {
      const percentages = screen.getAllByText('75%');
      expect(percentages.length).toBeGreaterThan(0);
    });

    it('displays agent agreement count', () => {
      expect(screen.getByText('6 of 8 agents agree')).toBeInTheDocument();
    });

    it('renders consensus meter component', () => {
      expect(screen.getByTestId('consensus-meter')).toBeInTheDocument();
    });

    it('displays last updated timestamp', () => {
      expect(screen.getByText(/Last updated:/i)).toBeInTheDocument();
    });
  });

  describe('Final Decision Display', () => {
    beforeEach(async () => {
      (intelligenceApi.fetchDisagreementData as jest.Mock).mockResolvedValue(
        mockDisagreementData
      );

      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={true} />);

      await waitFor(() => {
        expect(screen.getByText('Final Decision')).toBeInTheDocument();
      });
    });

    it('displays final decision section', () => {
      expect(screen.getByText('Final Decision')).toBeInTheDocument();
    });

    it('renders decision badge component', () => {
      expect(screen.getByTestId('decision-badge')).toBeInTheDocument();
    });

    it('displays decision value', () => {
      const buyTexts = screen.getAllByText('BUY');
      expect(buyTexts.length).toBeGreaterThan(0);
    });
  });

  describe('Agent Positions Display', () => {
    beforeEach(async () => {
      (intelligenceApi.fetchDisagreementData as jest.Mock).mockResolvedValue(
        mockDisagreementData
      );

      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={true} />);

      await waitFor(() => {
        expect(screen.getByText('Individual Agent Positions')).toBeInTheDocument();
      });
    });

    it('displays all 8 agent position cards', () => {
      const cards = screen.getAllByTestId('agent-position-card');
      expect(cards).toHaveLength(8);
    });

    it('displays agent names', () => {
      expect(screen.getByText('Market Analysis')).toBeInTheDocument();
      expect(screen.getByText('Pattern Detection')).toBeInTheDocument();
      expect(screen.getByText('Strategy Analysis')).toBeInTheDocument();
    });

    it('displays agent actions', () => {
      const buyActions = screen.getAllByText('BUY');
      expect(buyActions.length).toBeGreaterThan(0);
    });

    it('displays agent reasoning', () => {
      expect(screen.getByText('Strong bullish momentum')).toBeInTheDocument();
      expect(screen.getByText('Wyckoff accumulation detected')).toBeInTheDocument();
    });
  });

  describe('Data Fetching', () => {
    it('fetches disagreement data on mount when expanded', async () => {
      (intelligenceApi.fetchDisagreementData as jest.Mock).mockResolvedValue(
        mockDisagreementData
      );

      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={true} />);

      await waitFor(() => {
        expect(intelligenceApi.fetchDisagreementData).toHaveBeenCalledWith('EUR_USD');
        expect(intelligenceApi.fetchDisagreementData).toHaveBeenCalledTimes(1);
      });
    });

    it('does not fetch data when not expanded', () => {
      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={false} />);

      expect(intelligenceApi.fetchDisagreementData).not.toHaveBeenCalled();
    });

    it('refetches data at refresh interval when expanded', async () => {
      jest.useFakeTimers();

      (intelligenceApi.fetchDisagreementData as jest.Mock).mockResolvedValue(
        mockDisagreementData
      );

      render(
        <AgentDisagreementPanel
          symbol="EUR_USD"
          isExpanded={true}
          refreshInterval={5000}
        />
      );

      await waitFor(() => {
        expect(intelligenceApi.fetchDisagreementData).toHaveBeenCalledTimes(1);
      });

      // Fast-forward 5 seconds
      await act(async () => {
        jest.advanceTimersByTime(5000);
      });

      await waitFor(() => {
        expect(intelligenceApi.fetchDisagreementData).toHaveBeenCalledTimes(2);
      });

      jest.useRealTimers();
    });
  });

  describe('Grid Layout', () => {
    beforeEach(async () => {
      (intelligenceApi.fetchDisagreementData as jest.Mock).mockResolvedValue(
        mockDisagreementData
      );

      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={true} />);

      await waitFor(() => {
        expect(screen.getByText('Individual Agent Positions')).toBeInTheDocument();
      });
    });

    it('uses grid layout for agent cards', () => {
      const grid = screen.getByText('Individual Agent Positions').nextElementSibling;
      expect(grid).toHaveClass('grid');
    });
  });

  describe('No Data State', () => {
    it('displays message when no data available', async () => {
      (intelligenceApi.fetchDisagreementData as jest.Mock).mockResolvedValue(null);

      render(<AgentDisagreementPanel symbol="EUR_USD" isExpanded={true} />);

      await waitFor(() => {
        expect(
          screen.getByText(/No disagreement data available for EUR_USD/i)
        ).toBeInTheDocument();
      });
    });
  });
});
