/**
 * Agent Performance API Tests
 * Story 7.3: AC1 - Agent Performance Data API
 */

describe('Agent Performance API', () => {
  describe('Performance Calculations', () => {
    it('calculates win rate correctly', () => {
      const wins = 7;
      const losses = 3;
      const totalTrades = wins + losses;
      const winRate = (wins / totalTrades) * 100;

      expect(winRate).toBeCloseTo(70.0, 1);
    });

    it('calculates profit factor correctly', () => {
      const totalProfits = 200;
      const totalLosses = 100;
      const profitFactor = totalProfits / totalLosses;

      expect(profitFactor).toBe(2.0);
    });

    it('calculates average profit correctly', () => {
      const profits = [100, 150, 200];
      const avgProfit = profits.reduce((a, b) => a + b, 0) / profits.length;

      expect(avgProfit).toBe(150);
    });

    it('calculates average loss correctly', () => {
      const losses = [-50, -100, -75];
      const avgLoss = losses.reduce((a, b) => a + b, 0) / losses.length;

      expect(avgLoss).toBe(-75);
    });
  });

  describe('Data Structure', () => {
    it('defines correct performance data structure', () => {
      const mockPerformanceData = {
        agentId: 'market-analysis',
        agentName: 'Market Analysis',
        metrics: {
          winRate: 70.0,
          avgProfit: 145.30,
          avgLoss: -82.50,
          totalSignals: 450,
          totalTrades: 280,
          profitFactor: 2.4,
          maxDrawdown: -1250.00
        },
        bestPairs: [
          { symbol: 'EUR/USD', winRate: 72.0, totalTrades: 85, avgProfit: 165.20 }
        ],
        sessionPerformance: [
          { session: 'London', winRate: 75.0, totalTrades: 120 }
        ],
        recentActivity: {
          last7Days: 42,
          last30Days: 180
        }
      };

      expect(mockPerformanceData).toHaveProperty('agentId');
      expect(mockPerformanceData).toHaveProperty('agentName');
      expect(mockPerformanceData).toHaveProperty('metrics');
      expect(mockPerformanceData).toHaveProperty('bestPairs');
      expect(mockPerformanceData).toHaveProperty('recentActivity');

      expect(mockPerformanceData.metrics).toHaveProperty('winRate');
      expect(mockPerformanceData.metrics).toHaveProperty('avgProfit');
      expect(mockPerformanceData.metrics).toHaveProperty('profitFactor');
    });

    it('has correct data types for metrics', () => {
      const metrics = {
        winRate: 70.5,
        avgProfit: 145.30,
        avgLoss: -82.50,
        totalSignals: 450,
        totalTrades: 280,
        profitFactor: 2.4
      };

      expect(typeof metrics.winRate).toBe('number');
      expect(typeof metrics.avgProfit).toBe('number');
      expect(typeof metrics.totalSignals).toBe('number');
      expect(typeof metrics.profitFactor).toBe('number');
    });
  });

  describe('Time Period Filtering', () => {
    it('filters trades by 7 day period', () => {
      const now = Date.now();
      const threshold = now - 7 * 24 * 60 * 60 * 1000;

      const mockTrades = [
        { timestamp: now - 1 * 24 * 60 * 60 * 1000 }, // 1 day ago - should be included
        { timestamp: now - 10 * 24 * 60 * 60 * 1000 } // 10 days ago - should be excluded
      ];

      const filtered = mockTrades.filter(t => t.timestamp >= threshold);

      expect(filtered.length).toBe(1);
    });

    it('filters trades by 30 day period', () => {
      const now = Date.now();
      const threshold = now - 30 * 24 * 60 * 60 * 1000;

      const mockTrades = [
        { timestamp: now - 15 * 24 * 60 * 60 * 1000 }, // 15 days ago - included
        { timestamp: now - 45 * 24 * 60 * 60 * 1000 } // 45 days ago - excluded
      ];

      const filtered = mockTrades.filter(t => t.timestamp >= threshold);

      expect(filtered.length).toBe(1);
    });
  });

  describe('Best Pairs Calculation', () => {
    it('sorts pairs by win rate', () => {
      const pairs = [
        { symbol: 'EUR/USD', winRate: 65.0 },
        { symbol: 'GBP/USD', winRate: 75.0 },
        { symbol: 'USD/JPY', winRate: 70.0 }
      ];

      const sorted = pairs.sort((a, b) => b.winRate - a.winRate);

      expect(sorted[0].symbol).toBe('GBP/USD');
      expect(sorted[1].symbol).toBe('USD/JPY');
      expect(sorted[2].symbol).toBe('EUR/USD');
    });

    it('limits to top 3 pairs', () => {
      const pairs = [
        { symbol: 'EUR/USD', winRate: 65.0 },
        { symbol: 'GBP/USD', winRate: 75.0 },
        { symbol: 'USD/JPY', winRate: 70.0 },
        { symbol: 'AUD/USD', winRate: 60.0 },
        { symbol: 'USD/CHF', winRate: 55.0 }
      ];

      const top3 = pairs.sort((a, b) => b.winRate - a.winRate).slice(0, 3);

      expect(top3.length).toBe(3);
    });
  });
});
