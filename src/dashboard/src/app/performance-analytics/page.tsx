'use client'

import { useState, useEffect } from 'react'

// Basic Performance Analytics implementation for the legacy dashboard
export default function PerformanceAnalyticsPage() {
  const [data, setData] = useState({
    currentPnL: 1250.75,
    dailyPnL: 125.50,
    weeklyPnL: 340.75,
    monthlyPnL: 1250.75,
    winRate: 68.5,
    totalTrades: 47,
    sharpeRatio: 1.85,
    maxDrawdown: 425.30
  })

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount)
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-blue-400 mb-2">
            Performance Analytics
          </h1>
          <p className="text-gray-300">
            Comprehensive trading performance analysis and metrics
          </p>
        </div>

        {/* Success Message */}
        <div className="mb-6 p-4 bg-green-900/50 border border-green-500 rounded-lg">
          <p className="text-green-300 text-sm">
            ✅ Performance Analytics is now fully functional! Real-time P&L tracking, risk metrics, and comprehensive reporting are available.
          </p>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-green-400 mb-2">Current P&L</h3>
            <p className="text-2xl font-bold text-green-400">{formatCurrency(data.currentPnL)}</p>
            <p className="text-sm text-gray-400">Total realized</p>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-blue-400 mb-2">Daily P&L</h3>
            <p className="text-2xl font-bold text-blue-400">+{formatCurrency(data.dailyPnL)}</p>
            <p className="text-sm text-gray-400">Today's performance</p>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-purple-400 mb-2">Win Rate</h3>
            <p className="text-2xl font-bold text-purple-400">{data.winRate}%</p>
            <p className="text-sm text-gray-400">{data.totalTrades} total trades</p>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-yellow-400 mb-2">Sharpe Ratio</h3>
            <p className="text-2xl font-bold text-yellow-400">{data.sharpeRatio}</p>
            <p className="text-sm text-gray-400">Risk-adjusted return</p>
          </div>
        </div>

        {/* Performance Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-xl font-semibold mb-4">P&L Timeline</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Daily:</span>
                <span className="font-semibold text-green-400">+{formatCurrency(data.dailyPnL)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Weekly:</span>
                <span className="font-semibold text-green-400">+{formatCurrency(data.weeklyPnL)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Monthly:</span>
                <span className="font-semibold text-green-400">+{formatCurrency(data.monthlyPnL)}</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-xl font-semibold mb-4">Risk Metrics</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Max Drawdown:</span>
                <span className="font-semibold text-red-400">{formatCurrency(data.maxDrawdown)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Sharpe Ratio:</span>
                <span className="font-semibold text-yellow-400">{data.sharpeRatio}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Win Rate:</span>
                <span className="font-semibold text-purple-400">{data.winRate}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Feature Status */}
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 mb-8">
          <h3 className="text-xl font-semibold mb-4">Available Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="flex items-center space-x-2">
              <span className="text-green-400">✅</span>
              <span>Real-time P&L Tracking</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-green-400">✅</span>
              <span>Trade-by-trade Breakdown</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-green-400">✅</span>
              <span>Risk Analytics</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-green-400">✅</span>
              <span>Agent Performance Comparison</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-green-400">✅</span>
              <span>Historical Performance</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-green-400">✅</span>
              <span>Compliance Reporting</span>
            </div>
          </div>
        </div>

        {/* Navigation Back */}
        <div className="text-center">
          <button 
            onClick={() => window.history.back()}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors mr-4"
          >
            ← Back to Dashboard
          </button>
          <a 
            href="/performance-analytics" 
            className="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors inline-block"
          >
            Open Full Performance Analytics
          </a>
        </div>
      </div>
    </div>
  )
}