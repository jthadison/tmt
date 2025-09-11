/**
 * Manual Trading Interface Component - AC3
 * Story 9.5: Manual trade execution interface for direct market intervention
 * 
 * SECURITY: Administrator access only - all trades require admin authentication and audit logging
 */

'use client'

import React, { useState, useMemo } from 'react'
import {
  ManualTradeRequest,
  ManualTradingAction,
  ManualTradeStatus,
  RiskAssessment,
  ComplianceCheck
} from '@/types/tradingControls'
import Card from '@/components/ui/Card'
import Modal from '@/components/ui/Modal'
import { getActiveInstruments } from '@/lib/instruments'

/**
 * Props for ManualTradingInterface component
 */
interface ManualTradingInterfaceProps {
  /** Array of trade requests */
  tradeRequests: ManualTradeRequest[]
  /** Loading state */
  loading?: boolean
  /** Error message */
  error?: string
  /** Callback to submit trade request */
  onSubmitTradeRequest?: (request: Omit<ManualTradeRequest, 'id' | 'userId' | 'status' | 'createdAt'>) => Promise<string | null>
  /** Callback to approve trade request */
  onApproveTradeRequest?: (requestId: string, justification: string) => Promise<boolean>
  /** Callback to refresh trade requests */
  onRefresh?: () => void
}

/**
 * Trade request form component
 */
function TradeRequestForm({
  onSubmit
}: {
  onSubmit?: (request: Omit<ManualTradeRequest, 'id' | 'userId' | 'status' | 'createdAt'>) => Promise<string | null>
}) {
  const [formData, setFormData] = useState({
    action: 'market_buy' as ManualTradingAction,
    instrument: 'EUR_USD',
    quantity: '',
    price: '',
    orderType: 'market' as 'market' | 'limit' | 'stop' | 'stop_limit',
    timeInForce: 'GTC' as 'GTC' | 'IOC' | 'FOK' | 'DAY',
    accountId: 'account_001',
    justification: ''
  })
  
  const [submitting, setSubmitting] = useState(false)
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(null)

  const tradingActions: { value: ManualTradingAction; label: string }[] = [
    { value: 'market_buy', label: 'Market Buy' },
    { value: 'market_sell', label: 'Market Sell' },
    { value: 'limit_buy', label: 'Limit Buy' },
    { value: 'limit_sell', label: 'Limit Sell' },
    { value: 'close_position', label: 'Close Position' },
    { value: 'close_all_positions', label: 'Close All Positions' },
    { value: 'cancel_order', label: 'Cancel Order' },
    { value: 'modify_order', label: 'Modify Order' }
  ]

  const instruments = getActiveInstruments()

  const accounts = [
    { id: 'account_001', name: 'Primary Trading Account', balance: 100000 },
    { id: 'account_002', name: 'Secondary Account', balance: 50000 },
    { id: 'account_003', name: 'Risk Management Account', balance: 25000 }
  ]

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const generateRiskAssessment = (): RiskAssessment => {
    const quantity = parseFloat(formData.quantity) || 0
    const price = parseFloat(formData.price) || 1.0
    
    // Mock risk assessment calculation
    const positionValue = quantity * price
    const accountBalance = accounts.find(a => a.id === formData.accountId)?.balance || 100000
    const positionImpact = (positionValue / accountBalance) * 100
    
    let overall: 'low' | 'medium' | 'high' | 'critical' = 'low'
    const factors: any[] = []
    const warnings: string[] = []
    
    if (positionImpact > 50) {
      overall = 'critical'
      factors.push({
        name: 'Position Size',
        level: 'high',
        description: 'Position exceeds 50% of account balance',
        impact: 90
      })
      warnings.push('Position size is extremely large relative to account balance')
    } else if (positionImpact > 25) {
      overall = 'high'
      factors.push({
        name: 'Position Size',
        level: 'high',
        description: 'Position exceeds 25% of account balance',
        impact: 70
      })
      warnings.push('Large position size increases risk exposure')
    } else if (positionImpact > 10) {
      overall = 'medium'
      factors.push({
        name: 'Position Size',
        level: 'medium',
        description: 'Moderate position size',
        impact: 40
      })
    }

    // Market conditions factor (mock)
    factors.push({
      name: 'Market Volatility',
      level: 'medium',
      description: 'Current market conditions show moderate volatility',
      impact: 30
    })

    return {
      overall,
      factors,
      maxDrawdown: positionImpact * 0.1, // Mock calculation
      positionImpact,
      correlationRisk: 25, // Mock
      leverageImpact: 15, // Mock
      recommendations: [
        'Consider reducing position size if possible',
        'Monitor position closely after execution',
        'Set appropriate stop-loss levels'
      ],
      warnings,
      approved: overall !== 'critical',
      assessedBy: 'risk_engine',
      assessedAt: new Date()
    }
  }

  const validateForm = (): boolean => {
    if (!formData.instrument || !formData.quantity || !formData.accountId || !formData.justification.trim()) {
      return false
    }
    
    if ((formData.orderType === 'limit' || formData.orderType === 'stop' || formData.orderType === 'stop_limit') && !formData.price) {
      return false
    }
    
    return true
  }

  const handleSubmit = () => {
    if (!validateForm()) return
    
    const assessment = generateRiskAssessment()
    setRiskAssessment(assessment)
    setShowConfirmation(true)
  }

  const confirmSubmit = async () => {
    if (!onSubmit || !riskAssessment) return

    setSubmitting(true)
    try {
      const mockComplianceCheck: ComplianceCheck = {
        passed: true,
        violations: [],
        warnings: [],
        overrides: [],
        checkedAt: new Date(),
        checkedBy: 'compliance_engine'
      }

      const request: Omit<ManualTradeRequest, 'id' | 'userId' | 'status' | 'createdAt'> = {
        action: formData.action,
        instrument: formData.instrument,
        quantity: parseFloat(formData.quantity),
        price: formData.price ? parseFloat(formData.price) : undefined,
        orderType: formData.orderType,
        timeInForce: formData.timeInForce,
        accountId: formData.accountId,
        justification: formData.justification,
        riskAssessment,
        complianceCheck: mockComplianceCheck
      }

      const requestId = await onSubmit(request)
      if (requestId) {
        // Reset form
        setFormData({
          action: 'market_buy',
          instrument: 'EUR_USD',
          quantity: '',
          price: '',
          orderType: 'market',
          timeInForce: 'GTC',
          accountId: 'account_001',
          justification: ''
        })
        setShowConfirmation(false)
        setRiskAssessment(null)
      }
    } finally {
      setSubmitting(false)
    }
  }

  const getRiskLevelColor = (level: string): string => {
    switch (level) {
      case 'low': return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'medium': return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'high': return 'text-orange-400 bg-orange-900/20 border-orange-500/30'
      case 'critical': return 'text-red-400 bg-red-900/20 border-red-500/30'
      default: return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  return (
    <>
      <Card>
        <h3 className="text-lg font-semibold text-white mb-4">Submit Manual Trade Request</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Trading Action */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Trading Action</label>
            <select
              value={formData.action}
              onChange={(e) => handleInputChange('action', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              {tradingActions.map(action => (
                <option key={action.value} value={action.value}>
                  {action.label}
                </option>
              ))}
            </select>
          </div>

          {/* Instrument */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Instrument</label>
            <select
              value={formData.instrument}
              onChange={(e) => handleInputChange('instrument', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              {instruments.map(instrument => (
                <option key={instrument} value={instrument}>
                  {instrument}
                </option>
              ))}
            </select>
          </div>

          {/* Quantity */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Quantity (Units)</label>
            <input
              type="number"
              value={formData.quantity}
              onChange={(e) => handleInputChange('quantity', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
              placeholder="Enter quantity"
              min="0"
              step="1000"
            />
          </div>

          {/* Price (conditional) */}
          {(formData.orderType === 'limit' || formData.orderType === 'stop' || formData.orderType === 'stop_limit') && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Price</label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => handleInputChange('price', e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                placeholder="Enter price"
                min="0"
                step="0.00001"
              />
            </div>
          )}

          {/* Order Type */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Order Type</label>
            <select
              value={formData.orderType}
              onChange={(e) => handleInputChange('orderType', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="market">Market</option>
              <option value="limit">Limit</option>
              <option value="stop">Stop</option>
              <option value="stop_limit">Stop Limit</option>
            </select>
          </div>

          {/* Time in Force */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Time in Force</label>
            <select
              value={formData.timeInForce}
              onChange={(e) => handleInputChange('timeInForce', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              <option value="GTC">Good Till Cancelled (GTC)</option>
              <option value="IOC">Immediate or Cancel (IOC)</option>
              <option value="FOK">Fill or Kill (FOK)</option>
              <option value="DAY">Day Order</option>
            </select>
          </div>

          {/* Account */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-300 mb-2">Trading Account</label>
            <select
              value={formData.accountId}
              onChange={(e) => handleInputChange('accountId', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
            >
              {accounts.map(account => (
                <option key={account.id} value={account.id}>
                  {account.name} (Balance: ${account.balance.toLocaleString()})
                </option>
              ))}
            </select>
          </div>

          {/* Justification */}
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Trade Justification (Required)
            </label>
            <textarea
              value={formData.justification}
              onChange={(e) => handleInputChange('justification', e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white resize-none"
              rows={3}
              placeholder="Explain the reason for this manual trade intervention..."
              required
            />
          </div>
        </div>

        <div className="flex justify-end mt-6">
          <button
            onClick={handleSubmit}
            disabled={!validateForm() || submitting}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:opacity-50 text-white px-6 py-2 rounded font-medium"
          >
            Submit Trade Request
          </button>
        </div>
      </Card>

      {/* Trade Confirmation Modal */}
      <Modal isOpen={showConfirmation} onClose={() => setShowConfirmation(false)} size="lg">
        <div className="bg-gray-900 p-6">
          <h2 className="text-xl font-bold text-white mb-6">Confirm Manual Trade Request</h2>
          
          {/* Trade Summary */}
          <div className="mb-6 p-4 bg-gray-800 rounded-lg">
            <h3 className="text-white font-medium mb-3">Trade Summary</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Action:</span>
                <span className="ml-2 text-white font-medium">{formData.action.replace('_', ' ').toUpperCase()}</span>
              </div>
              <div>
                <span className="text-gray-400">Instrument:</span>
                <span className="ml-2 text-white">{formData.instrument}</span>
              </div>
              <div>
                <span className="text-gray-400">Quantity:</span>
                <span className="ml-2 text-white">{parseFloat(formData.quantity).toLocaleString()} units</span>
              </div>
              {formData.price && (
                <div>
                  <span className="text-gray-400">Price:</span>
                  <span className="ml-2 text-white">{formData.price}</span>
                </div>
              )}
            </div>
          </div>

          {/* Risk Assessment */}
          {riskAssessment && (
            <div className="mb-6">
              <h3 className="text-white font-medium mb-3">Risk Assessment</h3>
              <div className={`p-4 rounded-lg border ${getRiskLevelColor(riskAssessment.overall)}`}>
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium">Overall Risk Level</span>
                  <span className="font-bold">{riskAssessment.overall.toUpperCase()}</span>
                </div>
                
                {riskAssessment.warnings.length > 0 && (
                  <div className="mb-3">
                    <div className="text-sm font-medium mb-1">Warnings:</div>
                    {riskAssessment.warnings.map((warning, index) => (
                      <div key={index} className="text-sm">• {warning}</div>
                    ))}
                  </div>
                )}
                
                <div className="text-sm space-y-1">
                  <div>Position Impact: {riskAssessment.positionImpact.toFixed(1)}% of account</div>
                  <div>Max Drawdown: {riskAssessment.maxDrawdown.toFixed(1)}%</div>
                </div>
              </div>
            </div>
          )}

          {riskAssessment && !riskAssessment.approved && (
            <div className="mb-6 p-4 bg-red-900/20 border border-red-500/50 rounded">
              <div className="text-red-300 font-medium">⚠ HIGH RISK TRADE</div>
              <div className="text-red-200 text-sm mt-1">
                This trade has been flagged as high risk and may require additional approval.
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-3">
            <button
              onClick={() => setShowConfirmation(false)}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              onClick={confirmSubmit}
              disabled={submitting}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2 rounded font-medium"
            >
              {submitting ? 'Submitting...' : 'Confirm Trade Request'}
            </button>
          </div>
        </div>
      </Modal>
    </>
  )
}

/**
 * Trade request list component
 */
function TradeRequestList({
  tradeRequests,
  onApprove,
  loading = false
}: {
  tradeRequests: ManualTradeRequest[]
  onApprove?: (requestId: string, justification: string) => Promise<boolean>
  loading?: boolean
}) {
  const [approveModal, setApproveModal] = useState<{
    request: ManualTradeRequest | null
    show: boolean
  }>({ request: null, show: false })
  const [justification, setJustification] = useState('')
  const [approving, setApproving] = useState(false)

  const getStatusColor = (status: ManualTradeStatus): string => {
    switch (status) {
      case 'pending_approval': return 'text-yellow-400 bg-yellow-900/20 border-yellow-500/30'
      case 'approved': return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'rejected': return 'text-red-400 bg-red-900/20 border-red-500/30'
      case 'executing': return 'text-blue-400 bg-blue-900/20 border-blue-500/30'
      case 'executed': return 'text-green-400 bg-green-900/20 border-green-500/30'
      case 'failed': return 'text-red-400 bg-red-900/20 border-red-500/30'
      case 'cancelled': return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
      default: return 'text-gray-400 bg-gray-900/20 border-gray-500/30'
    }
  }

  const handleApprove = async () => {
    if (!onApprove || !approveModal.request || !justification.trim()) return

    setApproving(true)
    try {
      const success = await onApprove(approveModal.request.id, justification.trim())
      if (success) {
        setApproveModal({ request: null, show: false })
        setJustification('')
      }
    } finally {
      setApproving(false)
    }
  }

  if (loading && tradeRequests.length === 0) {
    return (
      <div className="animate-pulse space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-20 bg-gray-700 rounded"></div>
        ))}
      </div>
    )
  }

  return (
    <>
      <div className="space-y-4">
        {tradeRequests.length === 0 ? (
          <Card>
            <div className="text-center py-8">
              <div className="text-gray-400 text-lg mb-2">No Trade Requests</div>
              <p className="text-gray-500">No manual trade requests have been submitted</p>
            </div>
          </Card>
        ) : (
          tradeRequests.map(request => (
            <Card key={request.id}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-medium text-white">
                      {request.action.replace('_', ' ').toUpperCase()} - {request.instrument}
                    </h3>
                    <div className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(request.status)}`}>
                      {request.status.replace('_', ' ').toUpperCase()}
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                    <div>
                      <span className="text-gray-400">Quantity:</span>
                      <span className="ml-1 text-white">{request.quantity.toLocaleString()}</span>
                    </div>
                    {request.price && (
                      <div>
                        <span className="text-gray-400">Price:</span>
                        <span className="ml-1 text-white">{request.price}</span>
                      </div>
                    )}
                    <div>
                      <span className="text-gray-400">Account:</span>
                      <span className="ml-1 text-white">{request.accountId}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Submitted:</span>
                      <span className="ml-1 text-white">{request.createdAt.toLocaleString()}</span>
                    </div>
                  </div>
                  
                  <div className="text-sm">
                    <span className="text-gray-400">Justification:</span>
                    <span className="ml-2 text-white">{request.justification}</span>
                  </div>
                  
                  {request.riskAssessment && (
                    <div className="mt-2 text-sm">
                      <span className="text-gray-400">Risk Level:</span>
                      <span className={`ml-2 font-medium ${
                        request.riskAssessment.overall === 'critical' ? 'text-red-400' :
                        request.riskAssessment.overall === 'high' ? 'text-orange-400' :
                        request.riskAssessment.overall === 'medium' ? 'text-yellow-400' : 'text-green-400'
                      }`}>
                        {request.riskAssessment.overall.toUpperCase()}
                      </span>
                    </div>
                  )}
                </div>
                
                {request.status === 'pending_approval' && onApprove && (
                  <button
                    onClick={() => setApproveModal({ request, show: true })}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm font-medium"
                  >
                    Approve
                  </button>
                )}
              </div>
            </Card>
          ))
        )}
      </div>

      {/* Approval Modal */}
      <Modal 
        isOpen={approveModal.show} 
        onClose={() => setApproveModal({ request: null, show: false })} 
        size="md"
      >
        <div className="bg-gray-900 p-6">
          <h2 className="text-xl font-bold text-white mb-4">Approve Trade Request</h2>
          
          {approveModal.request && (
            <>
              <div className="mb-4 p-3 bg-gray-800 rounded">
                <div className="text-white font-medium">
                  {approveModal.request.action.replace('_', ' ').toUpperCase()} - {approveModal.request.instrument}
                </div>
                <div className="text-gray-400 text-sm">
                  Quantity: {approveModal.request.quantity.toLocaleString()} | Account: {approveModal.request.accountId}
                </div>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Approval Justification (Required)
                </label>
                <textarea
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white resize-none"
                  rows={3}
                  placeholder="Explain why you are approving this trade request..."
                  required
                />
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setApproveModal({ request: null, show: false })}
                  className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded"
                  disabled={approving}
                >
                  Cancel
                </button>
                <button
                  onClick={handleApprove}
                  disabled={!justification.trim() || approving}
                  className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-4 py-2 rounded font-medium"
                >
                  {approving ? 'Approving...' : 'Approve Trade'}
                </button>
              </div>
            </>
          )}
        </div>
      </Modal>
    </>
  )
}

/**
 * Main ManualTradingInterface component
 */
export function ManualTradingInterface({
  tradeRequests,
  loading = false,
  error,
  onSubmitTradeRequest,
  onApproveTradeRequest,
  onRefresh
}: ManualTradingInterfaceProps) {
  const [activeTab, setActiveTab] = useState<'submit' | 'requests'>('submit')

  const pendingRequests = useMemo(() => 
    tradeRequests.filter(req => req.status === 'pending_approval'), [tradeRequests])

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="text-red-400 text-lg mb-2">Error Loading Manual Trading Interface</div>
          <p className="text-gray-400 mb-4">{error}</p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
            >
              Retry
            </button>
          )}
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Manual Trading Interface</h2>
          <p className="text-sm text-gray-400">Direct market intervention - Administrator access only</p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex bg-gray-700 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('submit')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'submit'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Submit Trade
            </button>
            <button
              onClick={() => setActiveTab('requests')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'requests'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Trade Requests {pendingRequests.length > 0 && (
                <span className="ml-1 bg-yellow-500 text-black text-xs px-1.5 py-0.5 rounded-full">
                  {pendingRequests.length}
                </span>
              )}
            </button>
          </div>
          
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded text-sm font-medium"
            >
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {activeTab === 'submit' && (
        <TradeRequestForm onSubmit={onSubmitTradeRequest} />
      )}

      {activeTab === 'requests' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-white">Trade Requests</h3>
            <div className="text-sm text-gray-400">
              {tradeRequests.length} total, {pendingRequests.length} pending approval
            </div>
          </div>
          
          <TradeRequestList 
            tradeRequests={tradeRequests}
            onApprove={onApproveTradeRequest}
            loading={loading}
          />
        </div>
      )}
    </div>
  )
}

export default ManualTradingInterface