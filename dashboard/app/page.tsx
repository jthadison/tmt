'use client'

import { useEffect } from 'react'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/ui/Card'
import Grid from '@/components/ui/Grid'
import ConnectionStatus from '@/components/ui/ConnectionStatus'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import { useWebSocket } from '@/hooks/useWebSocket'

export default function Home() {
  const { connectionStatus, connect } = useWebSocket({
    url: 'ws://localhost:8080', // Development WebSocket URL
    reconnectAttempts: 3,
    reconnectInterval: 3000
  })

  useEffect(() => {
    // Auto-connect on component mount
    connect()
  }, [connect])

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Dashboard Overview</h2>
            <p className="text-gray-600 dark:text-gray-400">Monitor your trading accounts and performance</p>
          </div>
          
          <Grid cols={{ default: 1, md: 2, xl: 4 }}>
            <Card title="Total Balance">
              <p className="text-2xl font-bold text-green-400">$125,430.50</p>
              <p className="text-sm text-gray-500 mt-1">+5.2% today</p>
            </Card>
            
            <Card title="Active Positions">
              <p className="text-2xl font-bold text-blue-400">8</p>
              <p className="text-sm text-gray-500 mt-1">3 winning, 5 pending</p>
            </Card>
            
            <Card title="Daily P&L">
              <p className="text-2xl font-bold text-green-400">+$2,340.00</p>
              <p className="text-sm text-gray-500 mt-1">Best day this week</p>
            </Card>
            
            <Card title="Win Rate">
              <p className="text-2xl font-bold text-yellow-400">68.5%</p>
              <p className="text-sm text-gray-500 mt-1">Last 30 days</p>
            </Card>
          </Grid>
          
          <Grid cols={{ default: 1, lg: 2 }}>
            <Card title="Recent Activity" className="h-64">
              <div className="space-y-2">
                <div className="flex justify-between py-2 border-b border-gray-200 dark:border-gray-800">
                  <span>EUR/USD Buy</span>
                  <span className="text-green-400">+$142.50</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-200 dark:border-gray-800">
                  <span>GBP/JPY Sell</span>
                  <span className="text-red-400">-$87.30</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-200 dark:border-gray-800">
                  <span>XAU/USD Buy</span>
                  <span className="text-green-400">+$523.80</span>
                </div>
              </div>
            </Card>
            
            <Card title="System Status" className="h-64">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span>Market Analysis Agent</span>
                  <span className="text-green-400">● Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Risk Management</span>
                  <span className="text-green-400">● Active</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Circuit Breaker</span>
                  <span className="text-yellow-400">● Monitoring</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>WebSocket Connection</span>
                  <ConnectionStatus status={connectionStatus} />
                </div>
              </div>
            </Card>
          </Grid>
        </div>
      </MainLayout>
    </ProtectedRoute>
  )
}
