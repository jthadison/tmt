/**
 * GET /api/validation/walk-forward-reports
 * Story 11.8 - Task 8: REST API Endpoints
 *
 * Returns list of walk-forward validation reports
 */

import { NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import type { ValidationJobsResponse, ValidationJob } from '@/types/validation';

const WALK_FORWARD_URL = process.env.NEXT_PUBLIC_WALK_FORWARD_URL || 'http://localhost:8010';

export async function GET(request: Request) {
  const correlation_id = uuidv4();
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get('limit') || '20', 10);

  try {
    // Fetch walk-forward jobs from walk-forward service
    const response = await fetch(`${WALK_FORWARD_URL}/api/walk-forward/jobs?limit=${limit}`, {
      headers: {
        'X-Correlation-ID': correlation_id,
      },
      next: { revalidate: 30 }, // Cache for 30 seconds
    });

    if (!response.ok) {
      throw new Error(`Walk-forward service returned ${response.status}`);
    }

    const jobsData = await response.json();

    // Transform to our expected format
    const jobs: ValidationJob[] = (jobsData.data?.jobs || []).map((j: any) => ({
      job_id: j.job_id || j.id,
      status: j.status,
      progress_pct: j.progress_pct || j.progress || 0,
      current_step: j.current_step || j.step || '',
      started_at: j.started_at || j.created_at,
      completed_at: j.completed_at || j.finished_at,
      error_message: j.error_message || j.error,
    }));

    const responseData: ValidationJobsResponse = {
      data: jobs,
      error: null,
      correlation_id,
    };

    return NextResponse.json(responseData, {
      headers: {
        'X-Correlation-ID': correlation_id,
      },
    });
  } catch (error) {
    console.error('[walk-forward-reports] Error fetching reports:', error);

    const errorResponse: ValidationJobsResponse = {
      data: [],
      error: error instanceof Error ? error.message : 'Failed to fetch walk-forward reports',
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
