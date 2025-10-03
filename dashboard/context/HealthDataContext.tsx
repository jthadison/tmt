/**
 * HealthDataContext
 * Provides shared health data across all components to avoid multiple polling instances
 */

'use client'

import React, { createContext, useContext, ReactNode } from 'react'
import { useDetailedHealth } from '@/hooks/useDetailedHealth'
import { DetailedHealthData } from '@/types/health'
import { ConnectionStatus } from '@/types/websocket'

interface HealthDataContextValue {
  healthData: DetailedHealthData | null
  loading: boolean
  error: string | null
  lastUpdate: Date | null
  refreshData: () => Promise<void>
  connectionStatus: ConnectionStatus
  latencyHistory: Map<string, number[]>
}

const HealthDataContext = createContext<HealthDataContextValue | undefined>(undefined)

interface HealthDataProviderProps {
  children: ReactNode
}

/**
 * Provider component that manages a single instance of health data polling
 */
export function HealthDataProvider({ children }: HealthDataProviderProps) {
  const healthDataValue = useDetailedHealth({
    enableWebSocket: false, // Use HTTP polling for reliability
    pollingInterval: 5000
  })

  return (
    <HealthDataContext.Provider value={healthDataValue}>
      {children}
    </HealthDataContext.Provider>
  )
}

/**
 * Hook to access shared health data
 * Must be used within HealthDataProvider
 */
export function useHealthData(): HealthDataContextValue {
  const context = useContext(HealthDataContext)

  if (context === undefined) {
    throw new Error('useHealthData must be used within HealthDataProvider')
  }

  return context
}
