'use client'

import React from 'react'

export default function TradingDashboard() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-blue-400 mb-2">
            TMT Trading System
          </h1>
          <p className="text-gray-300">
            Adaptive/Continuous Learning Autonomous Trading Platform
          </p>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-green-400 mb-2">Total Balance</h3>
            <p className="text-2xl font-bold">$125,450.00</p>
            <p className="text-sm text-gray-400">3 accounts</p>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-blue-400 mb-2">Daily P&L</h3>
            <p className="text-2xl font-bold text-green-400">+$2,340.50</p>
            <p className="text-sm text-gray-400">+1.87%</p>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-purple-400 mb-2">Active Positions</h3>
            <p className="text-2xl font-bold">12</p>
            <p className="text-sm text-gray-400">Across all accounts</p>
          </div>
          
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-yellow-400 mb-2">System Status</h3>
            <div className="flex items-center">
              <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
              <p className="text-lg font-semibold">All Systems Online</p>
            </div>
          </div>
        </div>

        {/* Account Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-xl font-semibold">FTMO Account #1</h4>
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                <span className="text-sm text-green-400">Healthy</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Balance:</span>
                <span className="font-semibold">$45,230.00</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Equity:</span>
                <span className="font-semibold">$46,100.50</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Daily P&L:</span>
                <span className="font-semibold text-green-400">+$870.50</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Drawdown:</span>
                <span className="font-semibold text-yellow-400">-2.3%</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-xl font-semibold">FTMO Account #2</h4>
              <div className="flex items-center">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                <span className="text-sm text-green-400">Healthy</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Balance:</span>
                <span className="font-semibold">$38,920.00</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Equity:</span>
                <span className="font-semibold">$39,450.25</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Daily P&L:</span>
                <span className="font-semibold text-green-400">+$530.25</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Drawdown:</span>
                <span className="font-semibold text-green-400">-1.4%</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-xl font-semibold">OANDA Live</h4>
              <div className="flex items-center">
                <div className="w-2 h-2 bg-yellow-500 rounded-full mr-2"></div>
                <span className="text-sm text-yellow-400">Monitoring</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Balance:</span>
                <span className="font-semibold">$41,300.00</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Equity:</span>
                <span className="font-semibold">$41,850.75</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Daily P&L:</span>
                <span className="font-semibold text-green-400">+$939.75</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Drawdown:</span>
                <span className="font-semibold text-green-400">-0.8%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors">
            Performance Analytics
          </button>
          <button className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors">
            Trading Controls
          </button>
          <button className="bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors">
            Market Data
          </button>
          <button className="bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors">
            Emergency Stop
          </button>
        </div>

        {/* System Information */}
        <div className="mt-8 bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h3 className="text-xl font-semibold mb-4">System Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-400">All Stories Complete:</span>
              <span className="ml-2 text-green-400">✅ 39/39 (100%)</span>
            </div>
            <div>
              <span className="text-gray-400">WebSocket:</span>
              <span className="ml-2 text-green-400">✅ Connected</span>
            </div>
            <div>
              <span className="text-gray-400">Database:</span>
              <span className="ml-2 text-green-400">✅ PostgreSQL Online</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
