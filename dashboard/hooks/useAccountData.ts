'use client'

import { useState, useEffect, useCallback } from 'react'
import { AccountOverview, AccountStatus } from '@/types/account'
import { ConnectionStatus } from '@/types/websocket'

/**
 * Custom hook for managing account data with mock implementation
 * In production, this would integrate with React Query and real API
 */
export function useAccountData() {
  const [accounts, setAccounts] = useState<AccountOverview[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Generate mock account data
  const generateMockAccount = (id: string, index: number): AccountOverview => {
    const propFirms = ['FTMO', 'MyForexFunds', 'FundedNext', 'The5ers', 'TrueForexFunds']
    const statuses: AccountStatus[] = ['healthy', 'warning', 'danger']
    
    // Create varied data for testing
    const baseBalance = 10000 + (index * 15000)
    const dailyPnL = (Math.random() - 0.5) * 2000 // -1000 to +1000
    const weeklyPnL = dailyPnL * 5 + (Math.random() - 0.5) * 3000
    const totalPnL = weeklyPnL * 4 + (Math.random() - 0.5) * 5000
    const equity = baseBalance + totalPnL
    
    const drawdownCurrent = Math.max(0, Math.random() * 4000)
    const drawdownMax = 5000
    const drawdownPercentage = (drawdownCurrent / drawdownMax) * 100
    
    const activePositions = Math.floor(Math.random() * 15)
    const longPositions = Math.floor(activePositions * Math.random())
    const shortPositions = activePositions - longPositions
    
    const exposureTotal = baseBalance * (0.1 + Math.random() * 0.4) // 10-50% of balance
    const exposureLimit = baseBalance * 0.5 // 50% max exposure
    const exposureUtilization = (exposureTotal / exposureLimit) * 100

    // Determine status based on drawdown and P&L
    let status: AccountStatus = 'healthy'
    if (drawdownPercentage > 80 || dailyPnL < -1500) {
      status = 'danger'
    } else if (drawdownPercentage > 50 || dailyPnL < -800) {
      status = 'warning'
    }

    return {
      id,
      accountName: `Account ${String.fromCharCode(65 + index)}${index + 1}`,
      propFirm: propFirms[index % propFirms.length],
      balance: baseBalance,
      equity,
      pnl: {
        daily: dailyPnL,
        weekly: weeklyPnL,
        total: totalPnL,
        percentage: (totalPnL / baseBalance) * 100
      },
      drawdown: {
        current: drawdownCurrent,
        maximum: drawdownMax,
        percentage: drawdownPercentage
      },
      positions: {
        active: activePositions,
        long: longPositions,
        short: shortPositions
      },
      exposure: {
        total: exposureTotal,
        limit: exposureLimit,
        utilization: exposureUtilization
      },
      status,
      lastUpdate: new Date(Date.now() - Math.random() * 3600000) // Random time within last hour
    }
  }

  // Initialize mock data
  const initializeData = useCallback(() => {
    setLoading(true)
    setError(null)
    
    // Simulate API delay
    setTimeout(() => {
      try {
        const mockAccounts = Array.from({ length: 12 }, (_, i) => 
          generateMockAccount(`account-${i + 1}`, i)
        )
        setAccounts(mockAccounts)
        setLoading(false)
      } catch (err) {
        setError('Failed to load account data')
        setLoading(false)
      }
    }, 1000)
  }, [])

  // Refresh data
  const refreshData = useCallback(() => {
    if (accounts.length === 0) {
      initializeData()
      return
    }

    setLoading(true)
    setTimeout(() => {
      // Update existing accounts with new data
      setAccounts(prevAccounts => 
        prevAccounts.map((account, index) => ({
          ...generateMockAccount(account.id, index),
          accountName: account.accountName, // Keep original name
          propFirm: account.propFirm // Keep original prop firm
        }))
      )
      setLoading(false)
    }, 500)
  }, [accounts.length, initializeData])

  // Simulate real-time updates
  const simulateRealTimeUpdate = useCallback((accountId: string) => {
    setAccounts(prevAccounts => 
      prevAccounts.map(account => {
        if (account.id !== accountId) return account
        
        // Small random changes for real-time simulation
        const pnlChange = (Math.random() - 0.5) * 100 // Small P&L change
        const newDailyPnL = account.pnl.daily + pnlChange
        const newTotalPnL = account.pnl.total + pnlChange
        const newEquity = account.balance + newTotalPnL
        
        return {
          ...account,
          equity: newEquity,
          pnl: {
            ...account.pnl,
            daily: newDailyPnL,
            total: newTotalPnL,
            percentage: (newTotalPnL / account.balance) * 100
          },
          lastUpdate: new Date()
        }
      })
    )
  }, [])

  // Initialize data on mount
  useEffect(() => {
    initializeData()
  }, [initializeData])

  // Simulate periodic real-time updates
  useEffect(() => {
    if (accounts.length === 0) return

    const interval = setInterval(() => {
      // Randomly update one account
      const randomAccount = accounts[Math.floor(Math.random() * accounts.length)]
      simulateRealTimeUpdate(randomAccount.id)
    }, 5000) // Update every 5 seconds

    return () => clearInterval(interval)
  }, [accounts, simulateRealTimeUpdate])

  return {
    accounts,
    loading,
    error,
    refreshData,
    simulateRealTimeUpdate
  }
}

/**
 * Hook for subscribing to WebSocket account updates
 * This would integrate with the actual WebSocket in production
 */
export function useAccountWebSocket(accounts: AccountOverview[]) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED)
  
  useEffect(() => {
    // Simulate WebSocket connection
    setConnectionStatus(ConnectionStatus.CONNECTED)
    
    // In production, this would set up actual WebSocket listeners:
    // - accounts:overview:update
    // - accounts:pnl:update  
    // - accounts:positions:change
    
    return () => {
      setConnectionStatus(ConnectionStatus.DISCONNECTED)
    }
  }, [])

  return {
    connectionStatus
  }
}