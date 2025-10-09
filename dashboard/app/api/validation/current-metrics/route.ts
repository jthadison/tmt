/**
 * GET /api/validation/current-metrics
 * Story 11.8 - Task 8: REST API Endpoints
 *
 * Returns current validation metrics including overfitting score, Sharpe ratios, and parameter drift
 */

import { NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import type { CurrentMetricsResponse, ValidationMetrics } from '@/types/validation';

const OVERFITTING_MONITOR_URL = process.env.NEXT_PUBLIC_OVERFITTING_MONITOR_URL || 'http://localhost:8010';

export async function GET(request: Request) {
  const correlation_id = uuidv4();

  try {
    // Fetch current overfitting score from overfitting-monitor service
    const response = await fetch(`${OVERFITTING_MONITOR_URL}/api/monitoring/overfitting/current`, {
      headers: {
        'X-Correlation-ID': correlation_id,
      },
      next: { revalidate: 0 }, // Disable caching for real-time data
    });

    if (!response.ok) {
      throw new Error(`Overfitting monitor returned ${response.status}`);
    }

    const monitorData = await response.json();

    // Transform to our expected format
    const metrics: ValidationMetrics = {
      overfitting_score: monitorData.data?.current_score || 0,
      live_sharpe: monitorData.data?.live_performance?.sharpe_ratio || 0,
      backtest_sharpe: monitorData.data?.backtest_performance?.sharpe_ratio || 0,
      sharpe_ratio: monitorData.data?.performance_ratio || 0,
      parameter_drift_7d: monitorData.data?.drift_7d || 0,
      parameter_drift_30d: monitorData.data?.drift_30d || 0,
      last_updated: monitorData.data?.timestamp || new Date().toISOString(),
    };

    const responseData: CurrentMetricsResponse = {
      data: metrics,
      error: null,
      correlation_id,
    };

    return NextResponse.json(responseData, {
      headers: {
        'X-Correlation-ID': correlation_id,
      },
    });
  } catch (error) {
    console.error('[current-metrics] Error fetching validation metrics:', error);

    const errorResponse: CurrentMetricsResponse = {
      data: {
        overfitting_score: 0,
        live_sharpe: 0,
        backtest_sharpe: 0,
        sharpe_ratio: 0,
        parameter_drift_7d: 0,
        parameter_drift_30d: 0,
        last_updated: new Date().toISOString(),
      },
      error: error instanceof Error ? error.message : 'Failed to fetch validation metrics',
      correlation_id,
    };

    return NextResponse.json(errorResponse, {
      status: 500,
      headers: {
        'X-Correlation-ID': correlation_id,
      },
    });
  }
}
