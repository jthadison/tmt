/**
 * Chart Pattern Overlay Component
 * Adds pattern detection annotations to price charts
 * Story 7.2: AC4
 */

import { useEffect } from 'react';
import { PatternData, ChartCoordinate } from '@/types/intelligence';

export interface ChartPatternOverlayProps {
  symbol: string;
  chartRef: React.RefObject<unknown>;
  enabled: boolean;
  patterns: PatternData[];
}

/**
 * Overlay pattern annotations on a chart
 * This is a logic component - no UI rendered
 */
export function ChartPatternOverlay({ symbol, chartRef, enabled, patterns }: ChartPatternOverlayProps) {
  useEffect(() => {
    const chart = chartRef.current;

    if (!enabled || !chart || patterns.length === 0) {
      // Clean up annotations when disabled
      if (chart) {
        removePatternAnnotations(chart);
      }
      return;
    }

    // Add annotations to chart
    patterns.forEach(pattern => {
      addPatternAnnotations(chart, pattern);
    });

    return () => {
      // Clean up annotations on unmount
      if (chart) {
        removePatternAnnotations(chart);
      }
    };
  }, [patterns, enabled, chartRef, symbol]);

  return null; // This is a logic component, no UI
}

/**
 * Add pattern annotations to chart
 */
export function addPatternAnnotations(chart: unknown, pattern: PatternData) {
  if (!chart) return;

  const { coordinates } = pattern;

  // Entry point - green filled circle
  if (coordinates.entryPoint) {
    addMarker(chart, coordinates.entryPoint, {
      color: '#22c55e',
      shape: 'circle',
      position: 'inBar',
      text: coordinates.entryPoint.label || 'Entry'
    });
  }

  // Target levels - green hollow circles
  coordinates.targetLevels?.forEach((target, index) => {
    addMarker(chart, target, {
      color: '#22c55e',
      shape: 'circle',
      position: 'aboveBar',
      text: target.label || `T${index + 1}`
    });
  });

  // Stop loss - red filled circle
  if (coordinates.stopLoss) {
    addMarker(chart, coordinates.stopLoss, {
      color: '#ef4444',
      shape: 'circle',
      position: 'belowBar',
      text: coordinates.stopLoss.label || 'SL'
    });
  }

  // Support zones - green shaded rectangles
  coordinates.supportZones?.forEach(zone => {
    addPriceLine(chart, zone.priceHigh, {
      color: 'rgba(34, 197, 94, 0.2)',
      lineWidth: 2,
      lineStyle: 2, // dashed
      title: zone.label || 'Support'
    });
  });

  // Resistance zones - red shaded rectangles
  coordinates.resistanceZones?.forEach(zone => {
    addPriceLine(chart, zone.priceLow, {
      color: 'rgba(239, 68, 68, 0.2)',
      lineWidth: 2,
      lineStyle: 2, // dashed
      title: zone.label || 'Resistance'
    });
  });

  // Confirmation points - blue checkmarks
  coordinates.confirmationPoints?.forEach(point => {
    addMarker(chart, point, {
      color: '#3b82f6',
      shape: 'arrowUp',
      position: 'inBar',
      text: '✓'
    });
  });

  // Warning areas - yellow triangles
  coordinates.warningAreas?.forEach(area => {
    addMarker(chart, { price: area.priceHigh, timestamp: area.timestampStart }, {
      color: '#eab308',
      shape: 'arrowDown',
      position: 'aboveBar',
      text: '⚠'
    });
  });
}

/**
 * Remove pattern annotations from chart
 */
export function removePatternAnnotations(chart: unknown) {
  if (!chart) return;

  // Check which chart library is being used and call appropriate cleanup
  if (typeof chart.clearMarkers === 'function') {
    chart.clearMarkers();
  }

  if (typeof chart.clearPriceLines === 'function') {
    chart.clearPriceLines();
  }

  // For Chart.js
  if (chart.config?.type && chart.options?.plugins?.annotation) {
    chart.options.plugins.annotation.annotations = {};
    chart.update();
  }
}

/**
 * Add a marker to the chart (abstracted for different chart libraries)
 */
function addMarker(
  chart: unknown,
  coordinate: ChartCoordinate,
  options: {
    color: string;
    shape: string;
    position: string;
    text: string;
  }
) {
  if (!chart) return;

  // Lightweight Charts API
  if (typeof chart.addMarker === 'function') {
    chart.addMarker({
      time: coordinate.timestamp / 1000, // Convert to seconds
      position: options.position,
      color: options.color,
      shape: options.shape,
      text: options.text
    });
  }

  // Chart.js annotation plugin
  if (chart.config?.type && chart.options?.plugins?.annotation) {
    const annotationId = `marker-${Date.now()}-${Math.random()}`;

    if (!chart.options.plugins.annotation.annotations) {
      chart.options.plugins.annotation.annotations = {};
    }

    chart.options.plugins.annotation.annotations[annotationId] = {
      type: 'point',
      xValue: coordinate.timestamp,
      yValue: coordinate.price,
      backgroundColor: options.color,
      borderColor: options.color,
      borderWidth: 2,
      radius: 6,
      label: {
        content: options.text,
        enabled: true,
        position: 'top'
      }
    };

    chart.update();
  }
}

/**
 * Add a price line to the chart (abstracted for different chart libraries)
 */
function addPriceLine(
  chart: unknown,
  price: number,
  options: {
    color: string;
    lineWidth: number;
    lineStyle: number;
    title: string;
  }
) {
  if (!chart) return;

  // Lightweight Charts API
  if (typeof chart.addPriceLine === 'function') {
    chart.addPriceLine({
      price,
      color: options.color,
      lineWidth: options.lineWidth,
      lineStyle: options.lineStyle,
      axisLabelVisible: true,
      title: options.title
    });
  }

  // Chart.js annotation plugin
  if (chart.config?.type && chart.options?.plugins?.annotation) {
    const annotationId = `line-${Date.now()}-${Math.random()}`;

    if (!chart.options.plugins.annotation.annotations) {
      chart.options.plugins.annotation.annotations = {};
    }

    chart.options.plugins.annotation.annotations[annotationId] = {
      type: 'line',
      yMin: price,
      yMax: price,
      borderColor: options.color,
      borderWidth: options.lineWidth,
      borderDash: options.lineStyle === 2 ? [5, 5] : [],
      label: {
        content: options.title,
        enabled: true,
        position: 'end'
      }
    };

    chart.update();
  }
}
