/**
 * Authentication login endpoint for TMT Trading System Dashboard
 */
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email, password, twoFactorToken } = body

    // For staging/demo environment, accept demo credentials
    if (email === 'demo@trading.com' && password === 'demo123') {
      const mockUser = {
        id: 'user-001',
        name: 'Demo User',
        email: 'demo@tradingsystem.com',
        role: 'admin',
        two_factor_enabled: false,
        created_at: new Date().toISOString(),
        last_login: new Date().toISOString()
      }

      const response = {
        success: true,
        requires_2fa: false,
        user: mockUser,
        tokens: {
          access_token: 'staging-access-token-' + Date.now(),
          refresh_token: 'staging-refresh-token-' + Date.now(),
          expires_in: 3600
        }
      }

      return NextResponse.json(response)
    }

    // For other credentials, return error
    return NextResponse.json(
      {
        success: false,
        requires_2fa: false,
        error: 'Invalid credentials. Use demo@trading.com / demo123 for staging access.'
      },
      { status: 401 }
    )
  } catch (error) {
    console.error('Login error:', error)
    return NextResponse.json(
      {
        success: false,
        requires_2fa: false,
        error: 'Login failed'
      },
      { status: 500 }
    )
  }
}

export const dynamic = 'force-dynamic'