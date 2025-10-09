/**
 * GET /api/validation/report/[report_id]
 * Story 11.8 - Task 8: REST API Endpoints
 *
 * Returns detailed walk-forward validation report
 */

import { NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import type { WalkForwardReportResponse, WalkForwardReport } from '@/types/validation';

const WALK_FORWARD_URL = process.env.NEXT_PUBLIC_WALK_FORWARD_URL || 'http://localhost:8010';

export async function GET(
  request: Request,
  { params }: { params: { report_id: string } }
) {
  const correlation_id = uuidv4();
  const { report_id } = params;

  try {
    // Fetch detailed report from walk-forward service
    const response = await fetch(`${WALK_FORWARD_URL}/api/walk-forward/results/${report_id}`, {
      headers: {
        'X-Correlation-ID': correlation_id,
      },
      next: { revalidate: 300 }, // Cache for 5 minutes
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          {
            data: null,
            error: `Report ${report_id} not found`,
            correlation_id,
          },
          { status: 404 }
        );
      }
      throw new Error(`Walk-forward service returned ${response.status}`);
    }

    const reportData = await response.json();

    // Transform to our expected format
    const report: WalkForwardReport = {
      job_id: reportData.data?.job_id || report_id,
      config_file: reportData.data?.config_file || 'unknown',
      timestamp: reportData.data?.timestamp || new Date().toISOString(),
      status: reportData.data?.status || 'COMPLETED',

      windows: reportData.data?.windows || [],
      session_performance: reportData.data?.session_performance || [],
      parameter_stability: reportData.data?.parameter_stability || [],

      avg_in_sample_sharpe: reportData.data?.avg_in_sample_sharpe || 0,
      avg_out_of_sample_sharpe: reportData.data?.avg_out_of_sample_sharpe || 0,
      overfitting_score: reportData.data?.overfitting_score || 0,
      degradation_factor: reportData.data?.degradation_factor || 1,

      equity_curve_in_sample: reportData.data?.equity_curve_in_sample || [],
      equity_curve_out_of_sample: reportData.data?.equity_curve_out_of_sample || [],
      trade_distribution: reportData.data?.trade_distribution || [],
    };

    const responseData: WalkForwardReportResponse = {
      data: report,
      error: null,
      correlation_id,
    };

    return NextResponse.json(responseData, {
      headers: {
        'X-Correlation-ID': correlation_id,
      },
    });
  } catch (error) {
    console.error(`[report/${report_id}] Error fetching report:`, error);

    const errorResponse: WalkForwardReportResponse = {
      data: null as any,
      error: error instanceof Error ? error.message : 'Failed to fetch validation report',
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
