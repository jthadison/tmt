/**
 * Authentication token refresh endpoint for TMT Trading System Dashboard
 */
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { refresh_token } = body

    if (!refresh_token) {
      return NextResponse.json({ error: 'No refresh token provided' }, { status: 400 })
    }

    // For staging/demo environment, accept any staging refresh token
    if (refresh_token.startsWith('staging-refresh-token-') || refresh_token === 'mock-refresh-token') {
      const response = {
        success: true,
        tokens: {
          access_token: 'staging-access-token-' + Date.now(),
          refresh_token: 'staging-refresh-token-' + Date.now(),
          expires_in: 3600
        }
      }

      return NextResponse.json(response)
    }

    return NextResponse.json({ error: 'Invalid refresh token' }, { status: 401 })
  } catch (error) {
    console.error('Token refresh error:', error)
    return NextResponse.json({ error: 'Token refresh failed' }, { status: 500 })
  }
}

export const dynamic = 'force-dynamic'