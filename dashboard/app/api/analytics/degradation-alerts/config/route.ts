import { NextRequest, NextResponse } from 'next/server'
import { DegradationThresholds, DEFAULT_THRESHOLDS } from '@/types/analytics'

// TODO: Replace in-memory storage with database (PostgreSQL/TimescaleDB)
let storedThresholds: DegradationThresholds = { ...DEFAULT_THRESHOLDS }

/**
 * GET /api/analytics/degradation-alerts/config
 * Get current alert thresholds
 */
export async function GET(_request: NextRequest) {
  try {
    return NextResponse.json(storedThresholds)
  } catch (error) {
    console.error('Error fetching alert config:', error)
    return NextResponse.json(
      { error: 'Failed to fetch config' },
      { status: 500 }
    )
  }
}

/**
 * PUT /api/analytics/degradation-alerts/config
 * Update alert thresholds
 */
export async function PUT(request: NextRequest) {
  try {
    const newThresholds = (await request.json()) as DegradationThresholds

    // Validate thresholds
    if (
      newThresholds.profitFactorDecline < 0 ||
      newThresholds.sharpeThreshold < 0 ||
      newThresholds.sharpeDaysBelow < 1 ||
      newThresholds.overfittingThreshold < 0 ||
      newThresholds.overfittingThreshold > 1 ||
      newThresholds.walkForwardThreshold < 0 ||
      newThresholds.sharpeDropPercent < 0 ||
      newThresholds.winRateDecline < 0
    ) {
      return NextResponse.json(
        { error: 'Invalid threshold values' },
        { status: 400 }
      )
    }

    // Update stored thresholds
    storedThresholds = { ...newThresholds }

    return NextResponse.json({
      success: true,
      thresholds: storedThresholds
    })
  } catch (error) {
    console.error('Error updating alert config:', error)
    return NextResponse.json(
      { error: 'Failed to update config' },
      { status: 500 }
    )
  }
}
