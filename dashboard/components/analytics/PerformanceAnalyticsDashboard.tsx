/**
 * Main Performance Analytics Dashboard Component
 * Story 9.6: Trading Performance Analytics and Reporting
 * 
 * Unified dashboard integrating all performance analytics components
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  BarChart3,
  TrendingUp,
  Shield,
  Users,
  FileText,
  Settings,
  Calendar,
  Filter,
  Maximize2,
  Minimize2,
  Target
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import RealtimePnLTracker from './RealtimePnLTracker'
import HistoricalPerformanceDashboard from './HistoricalPerformanceDashboard'
import RiskAnalyticsDashboard from './RiskAnalyticsDashboard'
import AgentComparisonDashboard from './AgentComparisonDashboard'
import ComplianceReportGenerator from './ComplianceReportGenerator'
import PerformanceTrackingDashboard from './PerformanceTrackingDashboard'
import { TradeBreakdown, ComplianceReport } from '@/types/performanceAnalytics'

interface PerformanceAnalyticsDashboardProps {
  accountIds: string[]
  initialView?: 'overview' | 'realtime' | 'historical' | 'risk' | 'agents' | 'compliance' | 'tracking'
  onTradeSelect?: (trade: TradeBreakdown) => void
  onReportGenerated?: (report: ComplianceReport) => void
}

type ViewMode = 'overview' | 'realtime' | 'historical' | 'risk' | 'agents' | 'compliance' | 'tracking'

interface ViewConfig {
  id: ViewMode
  name: string
  icon: React.ElementType
  description: string
  component: React.ComponentType<any>
}

export default function PerformanceAnalyticsDashboard({
  accountIds,
  initialView = 'overview',
  onTradeSelect,
  onReportGenerated
}: PerformanceAnalyticsDashboardProps) {
  const [currentView, setCurrentView] = useState<ViewMode>(initialView)
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
    end: new Date()
  })
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>(accountIds)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [refreshInterval, setRefreshInterval] = useState(5000) // 5 seconds
  const [autoRefresh, setAutoRefresh] = useState(true)

  // View configurations
  const viewConfigs: ViewConfig[] = [
    {
      id: 'overview',
      name: 'Overview',
      icon: BarChart3,
      description: 'High-level performance summary across all accounts',
      component: () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RealtimePnLTracker
            accountId={selectedAccountIds[0]}
            showBreakdown={false}
            refreshInterval={refreshInterval}
            onTradeClick={onTradeSelect}
          />
          <RiskAnalyticsDashboard
            accountId={selectedAccountIds[0]}
            dateRange={dateRange}
          />
        </div>
      )
    },
    {
      id: 'realtime',
      name: 'Real-time P&L',
      icon: TrendingUp,
      description: 'Live profit/loss tracking with trade-by-trade breakdown',
      component: RealtimePnLTracker
    },
    {
      id: 'historical',
      name: 'Historical',
      icon: Calendar,
      description: 'Historical performance analysis with configurable periods',
      component: HistoricalPerformanceDashboard
    },
    {
      id: 'risk',
      name: 'Risk Analytics',
      icon: Shield,
      description: 'Comprehensive risk metrics and drawdown analysis',
      component: RiskAnalyticsDashboard
    },
    {
      id: 'agents',
      name: 'Agent Comparison',
      icon: Users,
      description: 'Multi-agent performance comparison and attribution',
      component: AgentComparisonDashboard
    },
    {
      id: 'compliance',
      name: 'Compliance',
      icon: FileText,
      description: 'Generate and export compliance reports',
      component: ComplianceReportGenerator
    },
    {
      id: 'tracking',
      name: 'Performance Tracking',
      icon: Target,
      description: 'Real-time tracking vs Monte Carlo projections with automated alerts',
      component: PerformanceTrackingDashboard
    }
  ]

  const currentViewConfig = viewConfigs.find(v => v.id === currentView)!

  // Handle fullscreen toggle
  const toggleFullscreen = useCallback(() => {
    if (!isFullscreen) {
      document.documentElement.requestFullscreen?.()
    } else {
      document.exitFullscreen?.()
    }
    setIsFullscreen(!isFullscreen)
  }, [isFullscreen])

  // Handle date range presets
  const setDateRangePreset = useCallback((preset: string) => {
    const now = new Date()
    let start: Date

    switch (preset) {
      case '7d':
        start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        break
      case '30d':
        start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
        break
      case '90d':
        start = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000)
        break
      case '1y':
        start = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000)
        break
      default:
        return
    }

    setDateRange({ start, end: now })
  }, [])

  // Component props for each view
  const getComponentProps = useCallback((viewId: ViewMode) => {
    const baseProps = {
      accountIds: selectedAccountIds,
      dateRange,
      onTradeSelect
    }

    switch (viewId) {
      case 'realtime':
        return {
          accountId: selectedAccountIds[0],
          showBreakdown: true,
          refreshInterval,
          onTradeClick: onTradeSelect
        }
      case 'historical':
        return {
          ...baseProps,
          initialDateRange: dateRange,
          onExport: (data: any) => console.log('Export historical data:', data)
        }
      case 'risk':
        return {
          accountId: selectedAccountIds[0],
          dateRange,
          onRiskAlert: (alert: any) => console.log('Risk alert:', alert)
        }
      case 'agents':
        return {
          ...baseProps,
          onAgentSelect: (agentId: string) => console.log('Agent selected:', agentId)
        }
      case 'compliance':
        return {
          accountIds: selectedAccountIds,
          onReportGenerated
        }
      case 'tracking':
        return {
          ...baseProps,
          refreshInterval,
          autoRefresh
        }
      default:
        return baseProps
    }
  }, [selectedAccountIds, dateRange, refreshInterval, onTradeSelect, onReportGenerated])

  return (
    <div className={`${isFullscreen ? 'fixed inset-0 z-50' : ''} bg-gray-900`}>
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-blue-400" />
            <div>
              <h1 className="text-2xl font-bold text-white">Performance Analytics</h1>
              <p className="text-gray-400 text-sm">
                Comprehensive trading performance analysis and reporting
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Auto-refresh toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1.5 rounded text-sm ${
                autoRefresh
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-800 text-gray-400'
              } hover:bg-opacity-80 transition-colors`}
            >
              Auto-refresh {autoRefresh ? 'ON' : 'OFF'}
            </button>

            {/* Fullscreen toggle */}
            <button
              onClick={toggleFullscreen}
              className="p-2 bg-gray-800 text-gray-400 rounded hover:bg-gray-700 hover:text-white transition-colors"
            >
              {isFullscreen ? (
                <Minimize2 className="w-4 h-4" />
              ) : (
                <Maximize2 className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex flex-wrap gap-2">
          {viewConfigs.map(({ id, name, icon: Icon, description }) => (
            <button
              key={id}
              onClick={() => setCurrentView(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                currentView === id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
              title={description}
            >
              <Icon className="w-4 h-4" />
              {name}
            </button>
          ))}
        </div>

        {/* Controls */}
        <div className="flex flex-wrap gap-4 mt-4 items-center">
          {/* Date Range Controls */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-400" />
            <div className="flex gap-1">
              {['7d', '30d', '90d', '1y'].map(preset => (
                <button
                  key={preset}
                  onClick={() => setDateRangePreset(preset)}
                  className="px-2 py-1 text-xs bg-gray-800 text-gray-400 rounded hover:bg-gray-700 hover:text-white transition-colors"
                >
                  {preset}
                </button>
              ))}
            </div>
            <input
              type="date"
              value={dateRange.start.toISOString().split('T')[0]}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: new Date(e.target.value) }))}
              className="px-2 py-1 bg-gray-800 text-white rounded text-sm"
            />
            <span className="text-gray-500">to</span>
            <input
              type="date"
              value={dateRange.end.toISOString().split('T')[0]}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: new Date(e.target.value) }))}
              className="px-2 py-1 bg-gray-800 text-white rounded text-sm"
            />
          </div>

          {/* Account Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              multiple
              value={selectedAccountIds}
              onChange={(e) => setSelectedAccountIds(Array.from(e.target.selectedOptions, option => option.value))}
              className="px-2 py-1 bg-gray-800 text-white rounded text-sm min-w-32"
              size={1}
            >
              {accountIds.map(id => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
            <span className="text-xs text-gray-500">
              {selectedAccountIds.length} of {accountIds.length} accounts
            </span>
          </div>

          {/* Refresh Interval */}
          {currentView === 'realtime' && (
            <div className="flex items-center gap-2">
              <Settings className="w-4 h-4 text-gray-400" />
              <select
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
                className="px-2 py-1 bg-gray-800 text-white rounded text-sm"
              >
                <option value={1000}>1s</option>
                <option value={5000}>5s</option>
                <option value={10000}>10s</option>
                <option value={30000}>30s</option>
                <option value={60000}>1m</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className={`${isFullscreen ? 'h-[calc(100vh-140px)]' : ''} overflow-auto`}>
        <AnimatePresence mode="wait">
          <motion.div
            key={currentView}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
            className="p-6"
          >
            {/* View Header */}
            <div className="mb-6">
              <div className="flex items-center gap-3 mb-2">
                <currentViewConfig.icon className="w-6 h-6 text-blue-400" />
                <h2 className="text-xl font-semibold text-white">
                  {currentViewConfig.name}
                </h2>
              </div>
              <p className="text-gray-400 text-sm">
                {currentViewConfig.description}
              </p>
            </div>

            {/* Dynamic Component */}
            {currentView === 'overview' ? (
              currentViewConfig.component()
            ) : (
              React.createElement(
                currentViewConfig.component,
                getComponentProps(currentView)
              )
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Footer */}
      <div className="bg-gray-900 border-t border-gray-800 px-6 py-3">
        <div className="flex justify-between items-center text-sm text-gray-500">
          <div>
            Last updated: {new Date().toLocaleString()}
          </div>
          <div className="flex items-center gap-4">
            <span>Accounts: {selectedAccountIds.length}</span>
            <span>Period: {Math.ceil((dateRange.end.getTime() - dateRange.start.getTime()) / (24 * 60 * 60 * 1000))} days</span>
            {autoRefresh && currentView === 'realtime' && (
              <span className="flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                Live
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}