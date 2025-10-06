/**
 * Pattern Detection API service
 * Handles communication with Pattern Detection agent (port 8008)
 */

import { PatternData, EnhancedTradeRecord, PatternStats } from '@/types/intelligence';

const PATTERN_DETECTION_URL = process.env.NEXT_PUBLIC_PATTERN_DETECTION_URL || 'http://localhost:8008';

/**
 * Fetch patterns for a specific symbol
 */
export async function fetchPatterns(
  symbol: string,
  timeframe: string = '1h',
  limit: number = 10
): Promise<PatternData[]> {
  try {
    const response = await fetch(
      `${PATTERN_DETECTION_URL}/patterns/${symbol}?timeframe=${timeframe}&limit=${limit}`
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch patterns: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching patterns:', error);
    // Return empty array for graceful degradation
    return [];
  }
}

/**
 * Fetch pattern by ID
 */
export async function fetchPatternById(patternId: string): Promise<PatternData | null> {
  try {
    const response = await fetch(`${PATTERN_DETECTION_URL}/patterns/id/${patternId}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch pattern: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching pattern by ID:', error);
    return null;
  }
}

/**
 * Fetch trades with similar patterns
 */
export async function fetchTradesByPattern(
  patternType: string,
  symbol?: string,
  limit: number = 20
): Promise<{ trades: EnhancedTradeRecord[]; stats: PatternStats }> {
  try {
    const params = new URLSearchParams({
      pattern: patternType,
      limit: limit.toString()
    });

    if (symbol) {
      params.append('symbol', symbol);
    }

    const response = await fetch(`${PATTERN_DETECTION_URL}/trades/by-pattern?${params}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch trades by pattern: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching trades by pattern:', error);
    return {
      trades: [],
      stats: {
        winRate: 0,
        avgProfit: 0,
        avgLoss: 0,
        totalTrades: 0,
        profitFactor: 0
      }
    };
  }
}

/**
 * Mock patterns for development/testing when Pattern Detection agent is unavailable
 */
export function generateMockPatterns(symbol: string): PatternData[] {
  const now = Date.now();
  const hour = 60 * 60 * 1000;

  return [
    {
      id: 'pattern-mock-1',
      symbol,
      patternType: 'wyckoff-accumulation',
      phase: 'Phase E',
      confidence: 78,
      status: 'confirmed',
      detectedAt: now - 2 * hour,
      coordinates: {
        entryPoint: {
          price: 1.0850,
          timestamp: now - 2 * hour,
          label: 'Entry (SOS)'
        },
        targetLevels: [
          { price: 1.0920, timestamp: now - hour, label: 'Target 1' },
          { price: 1.0980, timestamp: now, label: 'Target 2' }
        ],
        stopLoss: {
          price: 1.0800,
          timestamp: now - 2 * hour,
          label: 'Stop Loss'
        },
        supportZones: [
          {
            priceHigh: 1.0820,
            priceLow: 1.0800,
            timestampStart: now - 4 * hour,
            timestampEnd: now - 2 * hour,
            label: 'Spring Zone'
          }
        ],
        resistanceZones: [
          {
            priceHigh: 1.0900,
            priceLow: 1.0880,
            timestampStart: now - 3 * hour,
            timestampEnd: now - hour,
            label: 'Resistance'
          }
        ],
        confirmationPoints: [
          { price: 1.0860, timestamp: now - 90 * 60 * 1000, label: 'Volume Confirmation' }
        ]
      },
      description: 'Wyckoff Accumulation Phase E detected with Sign of Strength (SOS) break above resistance',
      keyCharacteristics: [
        'Spring action completed',
        'Sign of Strength (SOS) confirmed with volume',
        'Price above Creek (support turned resistance)'
      ],
      riskRewardRatio: 3.5
    },
    {
      id: 'pattern-mock-2',
      symbol,
      patternType: 'spring',
      confidence: 85,
      status: 'confirmed',
      detectedAt: now - 5 * hour,
      coordinates: {
        entryPoint: {
          price: 1.0825,
          timestamp: now - 4 * hour,
          label: 'Spring Entry'
        },
        targetLevels: [
          { price: 1.0880, timestamp: now - 2 * hour, label: 'Target' }
        ],
        stopLoss: {
          price: 1.0790,
          timestamp: now - 4 * hour,
          label: 'SL'
        },
        supportZones: [
          {
            priceHigh: 1.0810,
            priceLow: 1.0790,
            timestampStart: now - 6 * hour,
            timestampEnd: now - 4 * hour,
            label: 'Support'
          }
        ]
      },
      description: 'Spring pattern detected - false breakdown followed by reversal',
      keyCharacteristics: [
        'False breakdown below support',
        'Quick reversal with volume',
        'Bullish divergence on RSI'
      ],
      riskRewardRatio: 2.8
    }
  ];
}
