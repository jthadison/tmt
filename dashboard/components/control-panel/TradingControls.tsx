'use client'

import { useState } from 'react'
import { TradingSession, TradingSessionControlRequest } from '@/types/systemControl'

/**
 * Props for TradingControls component
 */
interface TradingControlsProps {
  /** Array of trading session information */
  tradingSessions: TradingSession[]
  /** Callback when trading action is requested */
  onTradingAction: (request: TradingSessionControlRequest) => void
  /** Loading state indicator */
  loading?: boolean
}

/**
 * Trading pause/resume system for per-account and global control
 * Provides granular control over trading operations across accounts
 */
export function TradingControls({
  tradingSessions,
  onTradingAction,
  loading = false
}: TradingControlsProps) {
  const [showActionDialog, setShowActionDialog] = useState(false)
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [selectedAction, setSelectedAction] = useState<'pause' | 'resume' | 'stop'>('pause')
  const [actionReason, setActionReason] = useState('')
  const [scheduledResume, setScheduledResume] = useState('')
  const [showGlobalControls, setShowGlobalControls] = useState(false)

  const getStatusColor = (status: TradingSession['status']): string => {
    switch (status) {
      case 'active':
        return 'text-green-400'
      case 'paused':
        return 'text-yellow-400'
      case 'stopped':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = (status: TradingSession['status']): string => {
    switch (status) {
      case 'active':
        return '▶'
      case 'paused':
        return '⏸'
      case 'stopped':
        return '⏹'
      default:
        return '○'
    }
  }

  const getStatusBadge = (status: TradingSession['status']): string => {
    switch (status) {
      case 'active':
        return 'bg-green-900/30 text-green-400 border-green-500/30'
      case 'paused':
        return 'bg-yellow-900/30 text-yellow-400 border-yellow-500/30'
      case 'stopped':
        return 'bg-red-900/30 text-red-400 border-red-500/30'
      default:
        return 'bg-gray-900/30 text-gray-400 border-gray-500/30'
    }
  }

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: amount !== 0 ? 'always' : 'never'
    }).format(amount)
  }

  const formatTimeAgo = (date: Date): string => {
    const diff = Date.now() - date.getTime()
    const minutes = Math.floor(diff / (60 * 1000))
    const hours = Math.floor(diff / (60 * 60 * 1000))
    
    if (hours > 0) return `${hours}h ${minutes % 60}m ago`
    return `${minutes}m ago`
  }

  const formatScheduledTime = (date: Date): string => {
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()
    
    if (isToday) {
      return `Today at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
    }
    
    return date.toLocaleDateString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const handleAccountAction = (accountId: string, action: 'pause' | 'resume' | 'stop') => {
    setSelectedAccount(accountId)
    setSelectedAction(action)
    setShowActionDialog(true)
  }

  const handleGlobalAction = (action: 'pause' | 'resume' | 'stop') => {
    setSelectedAccount('global')
    setSelectedAction(action)
    setShowActionDialog(true)
  }

  const handleConfirmAction = () => {
    if (!actionReason.trim()) return

    const request: TradingSessionControlRequest = {
      accountId: selectedAccount,
      action: selectedAction,
      reason: actionReason.trim(),
      scheduledResume: scheduledResume ? new Date(scheduledResume) : undefined
    }

    onTradingAction(request)
    setShowActionDialog(false)
    setSelectedAccount('')
    setActionReason('')
    setScheduledResume('')
  }

  const getActionDescription = (action: 'pause' | 'resume' | 'stop'): string => {
    switch (action) {
      case 'pause':
        return 'Temporarily halt trading (can be resumed)'
      case 'resume':
        return 'Resume trading operations'
      case 'stop':
        return 'Stop trading completely (requires manual restart)'
      default:
        return ''
    }
  }

  // const canPerformAction = (session: TradingSession, action: 'pause' | 'resume' | 'stop'): boolean => {
  //   switch (action) {
  //     case 'pause':
  //       return session.status === 'active'
  //     case 'resume':
  //       return session.status === 'paused'
  //     case 'stop':
  //       return session.status !== 'stopped'
  //     default:
  //       return false
  //   }
  // }

  const getActiveSessionsCount = (): number => {
    return tradingSessions.filter(session => session.status === 'active').length
  }

  const getPausedSessionsCount = (): number => {
    return tradingSessions.filter(session => session.status === 'paused').length
  }

  const getTotalPnL = (): number => {
    return tradingSessions.reduce((sum, session) => sum + session.currentPnL, 0)
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-700 rounded w-40"></div>
          <div className="grid grid-cols-1 gap-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-24 bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-gray-800 rounded-lg p-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold text-white">Trading Controls</h3>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-400">
              {getActiveSessionsCount()} active • {getPausedSessionsCount()} paused
            </div>
            <button
              onClick={() => setShowGlobalControls(!showGlobalControls)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition-colors"
            >
              Global Controls
            </button>
          </div>
        </div>

        {/* Global Controls */}
        {showGlobalControls && (
          <div className="mb-6 p-4 bg-gray-750 rounded-lg border border-gray-600">
            <h4 className="text-white font-medium mb-3">Global Trading Controls</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <button
                onClick={() => handleGlobalAction('pause')}
                disabled={getActiveSessionsCount() === 0}
                className="bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-4 py-2 rounded text-sm transition-colors"
              >
                ⏸ Pause All Trading
              </button>
              <button
                onClick={() => handleGlobalAction('resume')}
                disabled={getPausedSessionsCount() === 0}
                className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-4 py-2 rounded text-sm transition-colors"
              >
                ▶ Resume All Trading
              </button>
              <button
                onClick={() => handleGlobalAction('stop')}
                disabled={getActiveSessionsCount() === 0 && getPausedSessionsCount() === 0}
                className="bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white px-4 py-2 rounded text-sm transition-colors"
              >
                ⏹ Stop All Trading
              </button>
            </div>
            <div className="mt-3 text-sm text-gray-400">
              Global actions affect all trading accounts simultaneously
            </div>
          </div>
        )}

        {/* Trading Sessions Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {tradingSessions.map((session) => (
            <div
              key={session.accountId}
              className={`
                rounded-lg p-4 border transition-colors
                ${session.status === 'stopped'
                  ? 'bg-red-900/10 border-red-500/30'
                  : session.status === 'paused'
                  ? 'bg-yellow-900/10 border-yellow-500/30'
                  : 'bg-gray-750 border-gray-700 hover:border-gray-600'
                }
              `}
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`text-lg ${getStatusColor(session.status)}`}>
                      {getStatusIcon(session.status)}
                    </span>
                    <h4 className="font-medium text-white">{session.accountName}</h4>
                    <span className={`px-2 py-1 rounded text-xs border ${getStatusBadge(session.status)}`}>
                      {session.status.toUpperCase()}
                    </span>
                  </div>
                  
                  {session.status === 'paused' && session.pausedBy && (
                    <div className="text-sm text-gray-400 mb-1">
                      Paused by {session.pausedBy}
                      {session.pausedAt && ` • ${formatTimeAgo(session.pausedAt)}`}
                    </div>
                  )}
                  
                  {session.pauseReason && (
                    <div className="text-sm text-yellow-300 mb-2">
                      Reason: {session.pauseReason}
                    </div>
                  )}
                </div>
              </div>

              {/* Session Metrics */}
              <div className="grid grid-cols-3 gap-4 mb-3">
                <div>
                  <div className="text-xs text-gray-400">P&L</div>
                  <div className={`font-medium ${session.currentPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatCurrency(session.currentPnL)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Positions</div>
                  <div className="font-medium text-white">{session.activePositions}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Daily Trades</div>
                  <div className="font-medium text-white">{session.dailyTrades}</div>
                </div>
              </div>

              {/* Last Trade Info */}
              {session.lastTradeTime && (
                <div className="text-xs text-gray-500 mb-3">
                  Last trade: {formatTimeAgo(session.lastTradeTime)}
                </div>
              )}

              {/* Scheduled Resume */}
              {session.scheduledResume && session.status === 'paused' && (
                <div className="mb-3 p-2 bg-yellow-900/20 rounded border border-yellow-500/30">
                  <div className="text-yellow-400 text-xs font-medium">Scheduled Resume</div>
                  <div className="text-yellow-200 text-sm">
                    {formatScheduledTime(session.scheduledResume)}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-2">
                {session.status === 'active' && (
                  <button
                    onClick={() => handleAccountAction(session.accountId, 'pause')}
                    className="flex-1 bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-2 rounded text-sm transition-colors"
                  >
                    ⏸ Pause
                  </button>
                )}
                
                {session.status === 'paused' && (
                  <button
                    onClick={() => handleAccountAction(session.accountId, 'resume')}
                    className="flex-1 bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded text-sm transition-colors"
                  >
                    ▶ Resume
                  </button>
                )}
                
                {session.status !== 'stopped' && (
                  <button
                    onClick={() => handleAccountAction(session.accountId, 'stop')}
                    className="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded text-sm transition-colors"
                  >
                    ⏹ Stop
                  </button>
                )}

                {session.status === 'stopped' && (
                  <div className="flex-1 text-center py-2 text-gray-400 text-sm">
                    Requires manual restart
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Summary Statistics */}
        <div className="mt-6 pt-6 border-t border-gray-700">
          <h4 className="text-white font-medium mb-3">Trading Summary</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-gray-400">Total P&L</div>
              <div className={`text-lg font-bold ${getTotalPnL() >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatCurrency(getTotalPnL())}
              </div>
            </div>
            <div>
              <div className="text-gray-400">Active Positions</div>
              <div className="text-lg font-bold text-white">
                {tradingSessions.reduce((sum, session) => sum + session.activePositions, 0)}
              </div>
            </div>
            <div>
              <div className="text-gray-400">Daily Trades</div>
              <div className="text-lg font-bold text-white">
                {tradingSessions.reduce((sum, session) => sum + session.dailyTrades, 0)}
              </div>
            </div>
            <div>
              <div className="text-gray-400">Account Status</div>
              <div className="text-sm">
                <div className="text-green-400">{getActiveSessionsCount()} Active</div>
                <div className="text-yellow-400">{getPausedSessionsCount()} Paused</div>
                <div className="text-red-400">
                  {tradingSessions.filter(s => s.status === 'stopped').length} Stopped
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Trading Action Dialog */}
      {showActionDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg max-w-md w-full border border-gray-700">
            <div className="p-6 border-b border-gray-700">
              <h3 className="text-xl font-bold text-white">Trading Control Action</h3>
              <p className="text-gray-400 text-sm mt-1">
                {selectedAccount === 'global' 
                  ? 'All Trading Accounts' 
                  : tradingSessions.find(s => s.accountId === selectedAccount)?.accountName
                }
              </p>
            </div>

            <div className="p-6 space-y-4">
              <div className="bg-gray-750 rounded p-3">
                <div className="text-white font-medium">
                  Action: {selectedAction.charAt(0).toUpperCase() + selectedAction.slice(1)} Trading
                </div>
                <div className="text-gray-400 text-sm mt-1">
                  {getActionDescription(selectedAction)}
                </div>
              </div>

              {selectedAction === 'pause' && (
                <div>
                  <label className="block text-gray-300 text-sm mb-2">
                    Scheduled Resume (Optional)
                  </label>
                  <input
                    type="datetime-local"
                    value={scheduledResume}
                    onChange={(e) => setScheduledResume(e.target.value)}
                    min={new Date().toISOString().slice(0, 16)}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                  <p className="text-gray-500 text-xs mt-1">
                    Leave empty for manual resume
                  </p>
                </div>
              )}

              <div>
                <label className="block text-gray-300 text-sm mb-2">Reason *</label>
                <textarea
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  placeholder="Explain why this action is necessary..."
                  rows={3}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  required
                />
              </div>

              {selectedAction === 'stop' && (
                <div className="bg-red-900/20 border border-red-500/30 rounded p-3">
                  <div className="text-red-400 text-sm font-medium">🛑 Warning</div>
                  <div className="text-red-200 text-sm mt-1">
                    This will completely stop trading. Open positions may need manual closure. 
                    Manual restart will be required.
                  </div>
                </div>
              )}

              {selectedAccount === 'global' && (
                <div className="bg-yellow-900/20 border border-yellow-500/30 rounded p-3">
                  <div className="text-yellow-400 text-sm font-medium">⚠️ Global Action</div>
                  <div className="text-yellow-200 text-sm mt-1">
                    This action will affect ALL trading accounts simultaneously.
                  </div>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowActionDialog(false)
                  setSelectedAccount('')
                  setActionReason('')
                  setScheduledResume('')
                }}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAction}
                disabled={!actionReason.trim()}
                className={`
                  px-4 py-2 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                  ${selectedAction === 'stop' 
                    ? 'bg-red-600 hover:bg-red-700' 
                    : selectedAction === 'pause'
                    ? 'bg-yellow-600 hover:bg-yellow-700'
                    : 'bg-green-600 hover:bg-green-700'
                  }
                `}
              >
                {selectedAction === 'pause' ? '⏸ ' : selectedAction === 'resume' ? '▶ ' : '⏹ '}
                {selectedAction.charAt(0).toUpperCase() + selectedAction.slice(1)} Trading
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}