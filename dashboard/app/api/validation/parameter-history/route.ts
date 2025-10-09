/**
 * GET /api/validation/parameter-history
 * Story 11.8 - Task 8: REST API Endpoints
 *
 * Returns parameter version history with validation metrics
 */

import { NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import type { ParameterHistoryResponse, ParameterVersion } from '@/types/validation';

const CONFIG_MANAGER_URL = process.env.NEXT_PUBLIC_CONFIG_MANAGER_URL || 'http://localhost:8091';

export async function GET(request: Request) {
  const correlation_id = uuidv4();
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get('limit') || '10', 10);

  try {
    // Fetch configuration history from config-manager service
    const response = await fetch(`${CONFIG_MANAGER_URL}/api/config/history?limit=${limit}`, {
      headers: {
        'X-Correlation-ID': correlation_id,
      },
      next: { revalidate: 60 }, // Cache for 1 minute
    });

    if (!response.ok) {
      throw new Error(`Config manager returned ${response.status}`);
    }

    const configData = await response.json();

    // Transform to our expected format
    const versions: ParameterVersion[] = (configData.data?.versions || []).map((v: any) => ({
      version: v.version || v.tag || 'unknown',
      date: v.timestamp || v.created_at || new Date().toISOString(),
      author: v.author || v.committer || 'System',
      reason: v.message || v.description || 'Parameter update',
      metrics: {
        backtest_sharpe: v.validation_metrics?.backtest_sharpe || 0,
        out_of_sample_sharpe: v.validation_metrics?.out_of_sample_sharpe || 0,
        overfitting_score: v.validation_metrics?.overfitting_score || 0,
        max_drawdown: v.validation_metrics?.max_drawdown,
        win_rate: v.validation_metrics?.win_rate,
        profit_factor: v.validation_metrics?.profit_factor,
      },
    }));

    const responseData: ParameterHistoryResponse = {
      data: versions,
      error: null,
      correlation_id,
    };

    return NextResponse.json(responseData, {
      headers: {
        'X-Correlation-ID': correlation_id,
      },
    });
  } catch (error) {
    console.error('[parameter-history] Error fetching parameter history:', error);

    const errorResponse: ParameterHistoryResponse = {
      data: [],
      error: error instanceof Error ? error.message : 'Failed to fetch parameter history',
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
