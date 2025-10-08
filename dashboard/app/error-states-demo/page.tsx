'use client'

import { useState } from 'react'
import ErrorBoundary from '@/components/ui/ErrorBoundary'
import { ComponentErrorState } from '@/components/errors/ComponentErrorState'
import { CriticalErrorState } from '@/components/errors/CriticalErrorState'
import { EmptyState } from '@/components/empty/EmptyState'
import { useToastContext } from '@/context/ToastContext'
import { FormProvider, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { FormField } from '@/components/forms/FormField'

// Component that throws an error for testing ErrorBoundary
function BrokenComponent() {
  throw new Error('This component is intentionally broken for testing')
}

// Form validation schema
const positionSchema = z.object({
  stopLoss: z.coerce
    .number()
    .positive('Stop loss must be a positive value')
    .max(100, 'Stop loss cannot exceed 100 USD')
    .refine(val => val >= 0.01, {
      message: 'Stop loss must be at least 0.01 USD',
    }),
  takeProfit: z.coerce
    .number()
    .positive('Take profit must be a positive value')
    .max(500, 'Take profit cannot exceed 500 USD'),
})

type PositionFormData = z.infer<typeof positionSchema>

export default function ErrorStatesDemoPage() {
  const [showCriticalError, setShowCriticalError] = useState(false)
  const [showComponentError, setShowComponentError] = useState(false)
  const [showErrorBoundary, setShowErrorBoundary] = useState(false)
  const [hasData, setHasData] = useState(false)
  const [hasFilteredResults, setHasFilteredResults] = useState(false)
  const { showToast } = useToastContext()

  const methods = useForm<PositionFormData>({
    resolver: zodResolver(positionSchema),
  })

  const onSubmit = (data: PositionFormData) => {
    showToast({
      type: 'success',
      title: 'Form Submitted',
      message: `Form submitted successfully with stopLoss: ${data.stopLoss}, takeProfit: ${data.takeProfit}`,
      priority: 'low',
      category: 'system',
      timestamp: new Date().toISOString(),
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
          Error States & Empty States Demo
        </h1>

        <div className="space-y-8">
          {/* Toast Notifications */}
          <section className="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Toast Notifications
            </h2>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() =>
                  showToast({
                    type: 'error',
                    title: 'Error Toast',
                    message: 'This is an error toast notification',
                    priority: 'high',
                    category: 'system',
                    timestamp: new Date().toISOString(),
                  })
                }
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
              >
                Show Error Toast
              </button>
              <button
                onClick={() =>
                  showToast({
                    type: 'warning',
                    title: 'Warning Toast',
                    message: 'This is a warning toast notification',
                    priority: 'medium',
                    category: 'system',
                    timestamp: new Date().toISOString(),
                  })
                }
                className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg"
              >
                Show Warning Toast
              </button>
              <button
                onClick={() =>
                  showToast({
                    type: 'info',
                    title: 'Info Toast',
                    message: 'This is an info toast notification',
                    priority: 'low',
                    category: 'system',
                    timestamp: new Date().toISOString(),
                  })
                }
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
              >
                Show Info Toast
              </button>
              <button
                onClick={() =>
                  showToast({
                    type: 'success',
                    title: 'Success Toast',
                    message: 'This is a success toast notification',
                    priority: 'low',
                    category: 'system',
                    timestamp: new Date().toISOString(),
                  })
                }
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
              >
                Show Success Toast
              </button>
            </div>
          </section>

          {/* Component Error State */}
          <section className="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Component Error State (Inline)
            </h2>
            <button
              onClick={() => setShowComponentError(!showComponentError)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg mb-4"
            >
              {showComponentError ? 'Hide' : 'Show'} Component Error
            </button>
            {showComponentError && (
              <ComponentErrorState
                error={new Error('Failed to load EUR_USD position data')}
                onRetry={() => setShowComponentError(false)}
                title="Unable to load EUR_USD position data"
                description="The trading server is temporarily unavailable. Other positions are still visible."
                impact="This specific position cannot be displayed right now."
              />
            )}
          </section>

          {/* Critical Error State */}
          <section className="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Critical Error State (Full Page)
            </h2>
            <button
              onClick={() => setShowCriticalError(!showCriticalError)}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
            >
              {showCriticalError ? 'Hide' : 'Show'} Critical Error
            </button>
          </section>

          {showCriticalError && (
            <CriticalErrorState
              title="Connection Lost"
              description="Unable to connect to the trading system. Live signals and position updates are currently unavailable."
              impact="You cannot open new positions or modify existing ones until the connection is restored."
              onRetry={() => setShowCriticalError(false)}
              autoRetrySeconds={15}
            />
          )}

          {/* Error Boundary */}
          <section className="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Error Boundary (React Error Catching)
            </h2>
            <button
              onClick={() => setShowErrorBoundary(!showErrorBoundary)}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg mb-4"
            >
              {showErrorBoundary ? 'Hide' : 'Show'} Error Boundary Test
            </button>
            <ErrorBoundary>
              {showErrorBoundary && <BrokenComponent />}
            </ErrorBoundary>
          </section>

          {/* Form Validation Errors */}
          <section className="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Form Validation Errors with Suggestions
            </h2>
            <FormProvider {...methods}>
              <form onSubmit={methods.handleSubmit(onSubmit)} className="max-w-md">
                <FormField
                  name="stopLoss"
                  label="Stop Loss (USD)"
                  type="number"
                  placeholder="20.00"
                  suggestion="Try 20.00 for a 2% stop loss on this position"
                  exampleValue="20.00"
                />
                <FormField
                  name="takeProfit"
                  label="Take Profit (USD)"
                  type="number"
                  placeholder="60.00"
                  suggestion="Try 60.00 for a 6% take profit (3:1 risk-reward ratio)"
                  exampleValue="60.00"
                />
                <button
                  type="submit"
                  className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                >
                  Submit Form
                </button>
              </form>
            </FormProvider>
          </section>

          {/* Empty State - No Data */}
          <section className="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Empty State - No Data
            </h2>
            <button
              onClick={() => setHasData(!hasData)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg mb-4"
            >
              {hasData ? 'Show' : 'Hide'} Empty State
            </button>
            {!hasData && (
              <EmptyState
                type="no-data"
                title="No Open Positions"
                description="You haven't opened any positions yet. When you do, they'll appear here with real-time updates on profit/loss and risk levels."
                action={{
                  label: 'View Available Signals',
                  onClick: () =>
                    showToast({
                      type: 'info',
                      title: 'Navigation',
                      message: 'Would navigate to signals page',
                      priority: 'low',
                      category: 'system',
                      timestamp: new Date().toISOString(),
                    }),
                }}
                secondaryAction={{
                  label: 'Learn About Trading',
                  onClick: () =>
                    showToast({
                      type: 'info',
                      title: 'Navigation',
                      message: 'Would navigate to learning resources',
                      priority: 'low',
                      category: 'system',
                      timestamp: new Date().toISOString(),
                    }),
                }}
              />
            )}
          </section>

          {/* Empty State - No Results (Filtered) */}
          <section className="bg-white dark:bg-gray-900 rounded-lg shadow p-6">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Empty State - No Results (Filtered)
            </h2>
            <button
              onClick={() => setHasFilteredResults(!hasFilteredResults)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg mb-4"
            >
              {hasFilteredResults ? 'Show' : 'Hide'} No Results State
            </button>
            {!hasFilteredResults && (
              <EmptyState
                type="no-results"
                title="No Positions Match Your Filters"
                description="No positions found for: Symbol: GBP_USD, Status: Profitable, Session: London"
                action={{
                  label: 'Clear All Filters',
                  onClick: () =>
                    showToast({
                      type: 'success',
                      title: 'Filters Cleared',
                      message: 'All filters have been cleared',
                      priority: 'low',
                      category: 'system',
                      timestamp: new Date().toISOString(),
                    }),
                }}
                secondaryAction={{
                  label: 'Modify Filters',
                  onClick: () =>
                    showToast({
                      type: 'info',
                      title: 'Filter Panel',
                      message: 'Would open filter modification panel',
                      priority: 'low',
                      category: 'system',
                      timestamp: new Date().toISOString(),
                    }),
                }}
              />
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
