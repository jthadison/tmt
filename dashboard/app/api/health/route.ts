/**
 * Health check endpoint for the TMT Trading System Dashboard
 */
import { NextResponse } from 'next/server'

export async function GET() {
  try {
    return NextResponse.json(
      {
        status: 'healthy',
        service: 'tmt-dashboard',
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || '1.0.0'
      },
      { status: 200 }
    )
  } catch (error) {
    return NextResponse.json(
      {
        status: 'unhealthy',
        service: 'tmt-dashboard',
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}