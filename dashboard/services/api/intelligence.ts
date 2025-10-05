/**
 * Intelligence API Service
 *
 * API client for agent intelligence features:
 * - Disagreement data fetching
 * - Agent signal retrieval
 * - Enhanced signal processing
 *
 * Story 7.1: API Integration
 */

import { DisagreementData, EnhancedTradingSignal } from '@/types/intelligence';

const DISAGREEMENT_ENGINE_URL = process.env.NEXT_PUBLIC_DISAGREEMENT_ENGINE_URL || 'http://localhost:8005';

/**
 * Fetch disagreement data for a symbol from Disagreement Engine
 *
 * @param symbol - Trading symbol (e.g., 'EUR_USD')
 * @returns Promise<DisagreementData>
 */
export async function fetchDisagreementData(symbol: string): Promise<DisagreementData> {
  try {
    const response = await fetch(`${DISAGREEMENT_ENGINE_URL}/disagreement/current/${symbol}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch disagreement data: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching disagreement data:', error);
    throw error;
  }
}

/**
 * Fetch enhanced signal from specific agent
 *
 * @param agentPort - Agent port number (8001-8008)
 * @param symbol - Trading symbol
 * @returns Promise<EnhancedTradingSignal>
 */
export async function fetchAgentSignal(
  agentPort: number,
  symbol: string
): Promise<EnhancedTradingSignal> {
  try {
    const response = await fetch(`http://localhost:${agentPort}/signal/${symbol}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch agent signal: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`Error fetching signal from agent ${agentPort}:`, error);
    throw error;
  }
}

/**
 * Fetch signals from all 8 agents
 *
 * @param symbol - Trading symbol
 * @returns Promise<EnhancedTradingSignal[]>
 */
export async function fetchAllAgentSignals(symbol: string): Promise<EnhancedTradingSignal[]> {
  const agentPorts = [8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008];

  const signalPromises = agentPorts.map(port =>
    fetchAgentSignal(port, symbol).catch(error => {
      console.error(`Failed to fetch from agent ${port}:`, error);
      return null;
    })
  );

  const signals = await Promise.all(signalPromises);
  return signals.filter((signal): signal is EnhancedTradingSignal => signal !== null);
}
