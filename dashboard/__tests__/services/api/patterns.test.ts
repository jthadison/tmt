/**
 * Integration tests for Pattern Detection API
 * Story 7.2: AC3
 */

import { fetchPatterns, fetchPatternById, fetchTradesByPattern, generateMockPatterns } from '@/services/api/patterns';

// Mock fetch globally
global.fetch = jest.fn();

describe('Pattern Detection API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchPatterns', () => {
    test('fetches patterns successfully', async () => {
      const mockPatterns = [
        {
          id: 'pattern-1',
          symbol: 'EUR_USD',
          patternType: 'wyckoff-accumulation',
          confidence: 78,
          status: 'confirmed',
          detectedAt: Date.now(),
          coordinates: {},
          description: 'Test pattern',
          keyCharacteristics: ['Test']
        }
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPatterns
      });

      const result = await fetchPatterns('EUR_USD', '1h', 10);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/patterns/EUR_USD?timeframe=1h&limit=10')
      );
      expect(result).toEqual(mockPatterns);
    });

    test('returns empty array on fetch error', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const result = await fetchPatterns('EUR_USD');

      expect(result).toEqual([]);
    });

    test('returns empty array on non-ok response', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found'
      });

      const result = await fetchPatterns('EUR_USD');

      expect(result).toEqual([]);
    });

    test('uses default parameters when not provided', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => []
      });

      await fetchPatterns('EUR_USD');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('timeframe=1h&limit=10')
      );
    });
  });

  describe('fetchPatternById', () => {
    test('fetches pattern by ID successfully', async () => {
      const mockPattern = {
        id: 'pattern-123',
        symbol: 'EUR_USD',
        patternType: 'spring',
        confidence: 85,
        status: 'confirmed',
        detectedAt: Date.now(),
        coordinates: {},
        description: 'Test pattern',
        keyCharacteristics: ['Test']
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPattern
      });

      const result = await fetchPatternById('pattern-123');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/patterns/id/pattern-123')
      );
      expect(result).toEqual(mockPattern);
    });

    test('returns null on fetch error', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const result = await fetchPatternById('pattern-123');

      expect(result).toBeNull();
    });
  });

  describe('fetchTradesByPattern', () => {
    test('fetches trades with pattern statistics', async () => {
      const mockData = {
        trades: [
          {
            id: 'trade-1',
            symbol: 'EUR_USD',
            action: 'BUY' as const,
            price: 1.0850,
            quantity: 10000,
            timestamp: Date.now()
          }
        ],
        stats: {
          winRate: 68.5,
          avgProfit: 125.50,
          avgLoss: -45.20,
          totalTrades: 100,
          profitFactor: 2.8
        }
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData
      });

      const result = await fetchTradesByPattern('wyckoff-accumulation', 'EUR_USD', 20);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/trades/by-pattern?')
      );
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('pattern=wyckoff-accumulation')
      );
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('symbol=EUR_USD')
      );
      expect(result).toEqual(mockData);
    });

    test('returns empty data on fetch error', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const result = await fetchTradesByPattern('wyckoff-accumulation');

      expect(result.trades).toEqual([]);
      expect(result.stats).toEqual({
        winRate: 0,
        avgProfit: 0,
        avgLoss: 0,
        totalTrades: 0,
        profitFactor: 0
      });
    });

    test('omits symbol parameter when not provided', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ trades: [], stats: {} })
      });

      await fetchTradesByPattern('spring', undefined, 10);

      const fetchCall = (global.fetch as jest.Mock).mock.calls[0][0];
      expect(fetchCall).not.toContain('symbol=');
    });
  });

  describe('generateMockPatterns', () => {
    test('generates mock patterns for development', () => {
      const patterns = generateMockPatterns('EUR_USD');

      expect(Array.isArray(patterns)).toBe(true);
      expect(patterns.length).toBeGreaterThan(0);
      expect(patterns[0]).toHaveProperty('symbol', 'EUR_USD');
      expect(patterns[0]).toHaveProperty('patternType');
      expect(patterns[0]).toHaveProperty('confidence');
      expect(patterns[0]).toHaveProperty('coordinates');
    });

    test('includes all required coordinate types', () => {
      const patterns = generateMockPatterns('EUR_USD');
      const pattern = patterns[0];

      expect(pattern.coordinates).toHaveProperty('entryPoint');
      expect(pattern.coordinates).toHaveProperty('targetLevels');
      expect(pattern.coordinates).toHaveProperty('stopLoss');
      expect(pattern.coordinates).toHaveProperty('supportZones');
    });

    test('generates patterns with realistic data', () => {
      const patterns = generateMockPatterns('EUR_USD');
      const pattern = patterns[0];

      expect(pattern.confidence).toBeGreaterThanOrEqual(0);
      expect(pattern.confidence).toBeLessThanOrEqual(100);
      expect(pattern.riskRewardRatio).toBeGreaterThan(0);
      expect(pattern.keyCharacteristics.length).toBeGreaterThan(0);
    });
  });
});
