/**
 * GET /api/validation/alerts
 * Story 11.8 - Task 8: REST API Endpoints
 *
 * Returns validation alerts (overfitting, performance degradation, parameter drift)
 */

import { NextResponse } from 'next/server';
import { v4 as uuidv4 } from 'uuid';
import type { AlertsResponse, ValidationAlert } from '@/types/validation';

const OVERFITTING_MONITOR_URL = process.env.NEXT_PUBLIC_OVERFITTING_MONITOR_URL || 'http://localhost:8010';

export async function GET(request: Request) {
  const correlation_id = uuidv4();
  const { searchParams } = new URL(request.url);
  const severity = searchParams.get('severity');
  const limit = parseInt(searchParams.get('limit') || '50', 10);

  try {
    // Build query params
    const params = new URLSearchParams();
    if (severity) params.append('severity', severity);
    params.append('limit', limit.toString());

    // Fetch alerts from overfitting-monitor service
    const response = await fetch(
      `${OVERFITTING_MONITOR_URL}/api/monitoring/alerts?${params.toString()}`,
      {
        headers: {
          'X-Correlation-ID': correlation_id,
        },
        next: { revalidate: 0 }, // No caching for alerts
      }
    );

    if (!response.ok) {
      throw new Error(`Overfitting monitor returned ${response.status}`);
    }

    const alertsData = await response.json();

    // Transform to our expected format
    const alerts: ValidationAlert[] = (alertsData.data?.alerts || []).map((a: any) => ({
      id: a.id || a.alert_id,
      alert_type: a.alert_type || a.type,
      severity: a.severity || a.level,
      message: a.message || a.description,
      timestamp: a.timestamp || a.created_at,
      acknowledged: a.acknowledged || false,
      resolved: a.resolved || false,
      resolution_note: a.resolution_note,
      metadata: a.metadata || a.details,
    }));

    const responseData: AlertsResponse = {
      data: alerts,
      error: null,
      correlation_id,
    };

    return NextResponse.json(responseData, {
      headers: {
        'X-Correlation-ID': correlation_id,
      },
    });
  } catch (error) {
    console.error('[alerts] Error fetching validation alerts:', error);

    const errorResponse: AlertsResponse = {
      data: [],
      error: error instanceof Error ? error.message : 'Failed to fetch validation alerts',
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
