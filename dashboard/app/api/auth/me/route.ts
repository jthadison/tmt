/**
 * Authentication user profile endpoint for TMT Trading System Dashboard
 */
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  try {
    const authorization = request.headers.get('authorization')

    if (!authorization) {
      return NextResponse.json({ error: 'No authorization header' }, { status: 401 })
    }

    const token = authorization.replace('Bearer ', '')

    // For staging/demo environment, accept any staging token
    if (token.startsWith('staging-access-token-') || token === 'mock-access-token') {
      const mockUser = {
        id: 'user-001',
        name: 'Demo User',
        email: 'demo@tradingsystem.com',
        role: 'admin',
        two_factor_enabled: false,
        created_at: new Date().toISOString(),
        last_login: new Date().toISOString()
      }

      return NextResponse.json(mockUser)
    }

    return NextResponse.json({ error: 'Invalid token' }, { status: 401 })
  } catch (error) {
    console.error('Auth me error:', error)
    return NextResponse.json({ error: 'Authentication failed' }, { status: 500 })
  }
}

export const dynamic = 'force-dynamic'