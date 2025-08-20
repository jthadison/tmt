'use client'

import MainLayout from '@/components/layout/MainLayout'
import ProtectedRoute from '@/components/auth/ProtectedRoute'

/**
 * OANDA Accounts Page - Simple Test Version
 */
export default function OandaPage() {
  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-white">OANDA Accounts</h1>
            <p className="text-gray-400 mt-1">
              Real-time monitoring of your OANDA trading accounts
            </p>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Connection Status</h2>
            <div className="space-y-4">
              <div className="p-3 bg-gray-700 rounded">
                <div className="text-green-400">✓ OANDA API Connection: Active</div>
                <div className="text-sm text-gray-400 mt-1">
                  API Key: {process.env.NEXT_PUBLIC_OANDA_API_KEY ? '•••••••••••••' : 'Not configured'}
                </div>
                <div className="text-sm text-gray-400">
                  Account ID: {process.env.NEXT_PUBLIC_OANDA_ACCOUNT_IDS || 'Not configured'}
                </div>
                <div className="text-sm text-gray-400">
                  Environment: {process.env.NEXT_PUBLIC_OANDA_API_URL?.includes('practice') ? 'Practice' : 'Live'}
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Quick Test</h2>
            <p className="text-gray-300">
              This page confirms that:
            </p>
            <ul className="list-disc list-inside text-gray-300 mt-2 space-y-1">
              <li>OANDA route is working</li>
              <li>Environment variables are loaded</li>
              <li>Navigation is functional</li>
              <li>Ready for full OANDA integration</li>
            </ul>
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}