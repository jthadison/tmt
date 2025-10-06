/**
 * Unit tests for ChartPatternOverlay component
 * Story 7.2: AC4
 */

import React, { createRef } from 'react';
import { render } from '@testing-library/react';
import { ChartPatternOverlay, addPatternAnnotations, removePatternAnnotations } from '@/components/intelligence/ChartPatternOverlay';
import { PatternData } from '@/types/intelligence';

describe('ChartPatternOverlay', () => {
  const mockPattern: PatternData = {
    id: 'pattern-123',
    symbol: 'EUR_USD',
    patternType: 'wyckoff-accumulation',
    phase: 'Phase E',
    confidence: 78,
    status: 'confirmed',
    detectedAt: Date.now(),
    coordinates: {
      entryPoint: { price: 1.0850, timestamp: Date.now(), label: 'Entry (SOS)' },
      targetLevels: [
        { price: 1.0920, timestamp: Date.now() + 3600000, label: 'Target 1' }
      ],
      stopLoss: { price: 1.0800, timestamp: Date.now(), label: 'Stop Loss' },
      supportZones: [
        {
          priceHigh: 1.0820,
          priceLow: 1.0800,
          timestampStart: Date.now() - 7200000,
          timestampEnd: Date.now(),
          label: 'Spring Zone'
        }
      ],
      resistanceZones: [
        {
          priceHigh: 1.0900,
          priceLow: 1.0880,
          timestampStart: Date.now() - 3600000,
          timestampEnd: Date.now() + 3600000,
          label: 'Resistance'
        }
      ],
      confirmationPoints: [
        { price: 1.0860, timestamp: Date.now() - 1800000, label: 'Volume Confirmation' }
      ],
      warningAreas: [
        {
          priceHigh: 1.0950,
          priceLow: 1.0930,
          timestampStart: Date.now() + 3600000,
          timestampEnd: Date.now() + 7200000,
          label: 'Overextension Risk'
        }
      ]
    },
    description: 'Wyckoff Accumulation Phase E detected',
    keyCharacteristics: ['Spring action completed'],
    riskRewardRatio: 3.5
  };

  function createMockChart() {
    return {
      addMarker: jest.fn(),
      addPriceLine: jest.fn(),
      clearMarkers: jest.fn(),
      clearPriceLines: jest.fn()
    };
  }

  test('renders without crashing', () => {
    const mockChart = createMockChart();
    const chartRef = createRef() as any;
    chartRef.current = mockChart;

    render(
      <ChartPatternOverlay
        symbol="EUR_USD"
        chartRef={chartRef}
        enabled={true}
        patterns={[mockPattern]}
      />
    );

    // Component renders (returns null but executes effects)
    expect(chartRef.current).toBeDefined();
  });

  test('does not add annotations when disabled', () => {
    const mockChart = createMockChart();
    const chartRef = createRef() as any;
    chartRef.current = mockChart;

    render(
      <ChartPatternOverlay
        symbol="EUR_USD"
        chartRef={chartRef}
        enabled={false}
        patterns={[mockPattern]}
      />
    );

    expect(mockChart.addMarker).not.toHaveBeenCalled();
    expect(mockChart.addPriceLine).not.toHaveBeenCalled();
  });

  test('does not add annotations when no patterns', () => {
    const mockChart = createMockChart();
    const chartRef = createRef() as any;
    chartRef.current = mockChart;

    render(
      <ChartPatternOverlay
        symbol="EUR_USD"
        chartRef={chartRef}
        enabled={true}
        patterns={[]}
      />
    );

    expect(mockChart.addMarker).not.toHaveBeenCalled();
    expect(mockChart.addPriceLine).not.toHaveBeenCalled();
  });

  test('addPatternAnnotations adds entry point marker', () => {
    const mockChart = createMockChart();

    addPatternAnnotations(mockChart, mockPattern);

    expect(mockChart.addMarker).toHaveBeenCalledWith(
      expect.objectContaining({
        position: 'inBar',
        color: '#22c55e',
        shape: 'circle',
        text: 'Entry (SOS)'
      })
    );
  });

  test('addPatternAnnotations adds target level markers', () => {
    const mockChart = createMockChart();

    addPatternAnnotations(mockChart, mockPattern);

    expect(mockChart.addMarker).toHaveBeenCalledWith(
      expect.objectContaining({
        position: 'aboveBar',
        color: '#22c55e',
        text: 'Target 1'
      })
    );
  });

  test('addPatternAnnotations adds stop loss marker', () => {
    const mockChart = createMockChart();

    addPatternAnnotations(mockChart, mockPattern);

    expect(mockChart.addMarker).toHaveBeenCalledWith(
      expect.objectContaining({
        position: 'belowBar',
        color: '#ef4444',
        text: 'Stop Loss'
      })
    );
  });

  test('addPatternAnnotations adds support zone price lines', () => {
    const mockChart = createMockChart();

    addPatternAnnotations(mockChart, mockPattern);

    expect(mockChart.addPriceLine).toHaveBeenCalledWith(
      expect.objectContaining({
        color: 'rgba(34, 197, 94, 0.2)',
        title: 'Spring Zone'
      })
    );
  });

  test('addPatternAnnotations adds resistance zone price lines', () => {
    const mockChart = createMockChart();

    addPatternAnnotations(mockChart, mockPattern);

    expect(mockChart.addPriceLine).toHaveBeenCalledWith(
      expect.objectContaining({
        color: 'rgba(239, 68, 68, 0.2)',
        title: 'Resistance'
      })
    );
  });

  test('addPatternAnnotations adds confirmation points', () => {
    const mockChart = createMockChart();

    addPatternAnnotations(mockChart, mockPattern);

    expect(mockChart.addMarker).toHaveBeenCalledWith(
      expect.objectContaining({
        color: '#3b82f6',
        text: '✓'
      })
    );
  });

  test('addPatternAnnotations adds warning areas', () => {
    const mockChart = createMockChart();

    addPatternAnnotations(mockChart, mockPattern);

    expect(mockChart.addMarker).toHaveBeenCalledWith(
      expect.objectContaining({
        color: '#eab308',
        text: '⚠'
      })
    );
  });

  test('removePatternAnnotations clears markers and lines', () => {
    const mockChart = createMockChart();

    removePatternAnnotations(mockChart);

    expect(mockChart.clearMarkers).toHaveBeenCalled();
    expect(mockChart.clearPriceLines).toHaveBeenCalled();
  });

  test('handles null chart reference gracefully', () => {
    expect(() => {
      addPatternAnnotations(null, mockPattern);
    }).not.toThrow();

    expect(() => {
      removePatternAnnotations(null);
    }).not.toThrow();
  });

  test('handles pattern with minimal coordinates', () => {
    const minimalPattern: PatternData = {
      id: 'pattern-minimal',
      symbol: 'EUR_USD',
      patternType: 'spring',
      confidence: 70,
      status: 'forming',
      detectedAt: Date.now(),
      coordinates: {},
      description: 'Minimal pattern',
      keyCharacteristics: ['Test']
    };

    const mockChart = createMockChart();

    expect(() => {
      addPatternAnnotations(mockChart, minimalPattern);
    }).not.toThrow();
  });
});
