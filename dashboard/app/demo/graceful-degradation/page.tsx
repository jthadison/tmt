'use client'

/**
 * Demo Page for Story 9.3: Graceful Degradation & Optimistic UI
 *
 * Demonstrates:
 * - Retry logic with exponential backoff
 * - Optimistic UI updates with rollback
 * - Agent fallback with last known data
 * - WebSocket with polling fallback
 */

import { useState } from 'react'
import { apiClient } from '@/lib/api/retryClient'
import { useOptimisticUpdate } from '@/hooks/useOptimisticUpdate'
import { useAgentWithFallback } from '@/hooks/useAgentWithFallback'

interface Position {
  id: string
  symbol: string
  stopLoss: number
  takeProfit: number
  status: string
}

export default function GracefulDegradationDemo() {
  const [retryAttempt, setRetryAttempt] = useState(0)
  const [retryResult, setRetryResult] = useState<string>('')

  // Demo 1: Retry Logic with Exponential Backoff
  const testRetryLogic = async () => {
    setRetryAttempt(0)
    setRetryResult('Testing...')

    try {
      await apiClient.get('/api/test-retry', {
        maxAttempts: 3,
        onRetry: (attempt, error) => {
          setRetryAttempt(attempt)
          console.log(`Retrying... Attempt ${attempt} of 3`, error)
        },
      })

      setRetryResult('✓ Success after retries')
    } catch (error) {
      setRetryResult(`✗ Failed after 3 attempts: ${(error as Error).message}`)
    } finally {
      setRetryAttempt(0)
    }
  }

  // Demo 2: Optimistic UI Update
  const initialPosition: Position = {
    id: '1',
    symbol: 'EUR_USD',
    stopLoss: 1.0950,
    takeProfit: 1.1050,
    status: 'open',
  }

  const { state, update, isUpdating, error } = useOptimisticUpdate(initialPosition, {
    onUpdate: async (updatedPosition) => {
      // Simulate API call
      const response = await fetch('/api/positions/' + updatedPosition.id, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedPosition),
      })

      if (!response.ok) {
        throw new Error('Failed to update position')
      }
    },
    onSuccess: (data) => {
      console.log('Position updated successfully:', data)
    },
    onError: (error) => {
      console.error('Failed to update position:', error)
    },
  })

  const handleStopLossChange = (newStopLoss: number) => {
    update({ ...state, stopLoss: newStopLoss })
  }

  // Demo 3: Agent with Fallback
  const fallbackPatterns = [
    { id: '1', type: 'Cached Pattern 1', timestamp: new Date(Date.now() - 300000) },
    { id: '2', type: 'Cached Pattern 2', timestamp: new Date(Date.now() - 300000) },
  ]

  const {
    data: patterns,
    status: agentStatus,
    isLoading: agentLoading,
  } = useAgentWithFallback('http://localhost:8008/patterns/EUR_USD', fallbackPatterns, {
    retryIntervalMs: 30000,
  })

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="bg-white rounded-lg shadow-sm p-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Story 9.3: Graceful Degradation Demo
          </h1>
          <p className="text-gray-600">
            Demonstrating retry logic, optimistic UI, and fallback mechanisms
          </p>
        </header>

        {/* Demo 1: Retry Logic */}
        <section className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            1. Automatic Retry with Exponential Backoff
          </h2>
          <p className="text-gray-600 mb-4">
            Tests automatic retry logic with 3 attempts (immediate, 2s, 4s delays)
          </p>

          <div className="space-y-4">
            <button
              onClick={testRetryLogic}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Test Retry Logic
            </button>

            {retryAttempt > 0 && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-blue-800 font-medium">
                  🔄 Retrying... Attempt {retryAttempt} of 3
                </p>
              </div>
            )}

            {retryResult && (
              <div
                className={`p-4 rounded-lg ${
                  retryResult.startsWith('✓')
                    ? 'bg-green-50 border border-green-200 text-green-800'
                    : retryResult.startsWith('✗')
                    ? 'bg-red-50 border border-red-200 text-red-800'
                    : 'bg-gray-50 border border-gray-200 text-gray-800'
                }`}
              >
                <p className="font-medium">{retryResult}</p>
              </div>
            )}
          </div>
        </section>

        {/* Demo 2: Optimistic UI Update */}
        <section className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            2. Optimistic UI Update with Rollback
          </h2>
          <p className="text-gray-600 mb-4">
            Immediately updates UI, then confirms with server or rolls back on error
          </p>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Stop Loss
                </label>
                <input
                  type="number"
                  value={state.stopLoss}
                  onChange={(e) => handleStopLossChange(parseFloat(e.target.value))}
                  disabled={isUpdating}
                  step="0.0001"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                <div className="px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg">
                  {state.status}
                </div>
              </div>
            </div>

            {isUpdating && (
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-yellow-800 font-medium">⏳ Updating position...</p>
              </div>
            )}

            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800 font-medium">✗ {error.message}</p>
                <button
                  onClick={() => update(state)}
                  className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                >
                  Retry
                </button>
              </div>
            )}

            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">
                <strong>Current Position:</strong> {state.symbol} | SL: {state.stopLoss} | TP:{' '}
                {state.takeProfit}
              </p>
            </div>
          </div>
        </section>

        {/* Demo 3: Agent with Fallback */}
        <section className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            3. Graceful Degradation - Agent with Fallback
          </h2>
          <p className="text-gray-600 mb-4">
            Shows last known data when agent is offline, retries every 30 seconds
          </p>

          {agentStatus.usingFallback && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-blue-800 font-medium">
                ℹ️ Pattern Detection temporarily unavailable. Using last known patterns.
              </p>
              {agentStatus.lastSeen && (
                <p className="text-sm text-blue-600 mt-1">
                  Last updated: {new Date(agentStatus.lastSeen).toLocaleTimeString()}
                </p>
              )}
            </div>
          )}

          {!agentStatus.online && !agentStatus.usingFallback && (
            <div className="mb-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-orange-800 font-medium">⚠️ Pattern Detection agent offline</p>
            </div>
          )}

          {agentStatus.online && (
            <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-green-800 font-medium">✓ Pattern Detection agent online</p>
            </div>
          )}

          <div className="space-y-2">
            {agentLoading ? (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-600">Loading patterns...</p>
              </div>
            ) : patterns && patterns.length > 0 ? (
              patterns.map((pattern: { id: string; type: string; timestamp?: Date }) => (
                <div key={pattern.id} className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                  <p className="font-medium text-gray-900">{pattern.type}</p>
                  {pattern.timestamp && (
                    <p className="text-sm text-gray-500">
                      {new Date(pattern.timestamp).toLocaleString()}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-600">No patterns available</p>
              </div>
            )}
          </div>
        </section>

        {/* Status Summary */}
        <section className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Status Summary</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-600 font-medium">Retry Logic</p>
              <p className="text-2xl font-bold text-blue-900">
                {retryAttempt > 0 ? `${retryAttempt}/3` : 'Ready'}
              </p>
            </div>
            <div className="p-4 bg-yellow-50 rounded-lg">
              <p className="text-sm text-yellow-600 font-medium">Optimistic Update</p>
              <p className="text-2xl font-bold text-yellow-900">
                {isUpdating ? 'Updating' : 'Ready'}
              </p>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <p className="text-sm text-green-600 font-medium">Agent Status</p>
              <p className="text-2xl font-bold text-green-900">
                {agentStatus.online ? 'Online' : 'Offline'}
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
