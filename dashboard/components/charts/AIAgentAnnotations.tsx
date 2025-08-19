/**
 * AI Agent Annotations Component - AC4
 * Story 9.4: Chart annotations showing AI agent entry/exit points and decision rationale
 * 
 * FEATURES: Trade signals, decision rationale, confidence levels, risk assessment
 */

'use client'

import React, { useState, useCallback, useMemo, useEffect } from 'react'
import {
  AgentAnnotation,
  RiskAssessment,
  ChartTimeframe,
  OHLCV
} from '@/types/marketData'
import { useMarketData } from '@/hooks/useMarketData'

/**
 * Agent types with their characteristics
 */
const AGENT_TYPES = {
  market_analysis: {
    name: 'Market Analysis Agent',
    icon: '📊',
    color: '#3b82f6',
    description: 'Analyzes market trends and patterns'
  },
  risk_management: {
    name: 'Risk Management Agent',
    icon: '⚠️',
    color: '#f59e0b',
    description: 'Manages position sizing and risk'
  },
  execution_engine: {
    name: 'Execution Engine',
    icon: '⚡',
    color: '#10b981',
    description: 'Executes trades and manages orders'
  },
  circuit_breaker: {
    name: 'Circuit Breaker Agent',
    icon: '🛡️',
    color: '#ef4444',
    description: 'Emergency stops and safety measures'
  },
  human_behavior: {
    name: 'Human Behavior Agent',
    icon: '🧠',
    color: '#8b5cf6',
    description: 'Mimics human trading patterns'
  },
  wyckoff_analysis: {
    name: 'Wyckoff Analysis Agent',
    icon: '📈',
    color: '#06b6d4',
    description: 'Wyckoff methodology analysis'
  }
}

/**
 * Annotation tooltip component
 */
function AnnotationTooltip({
  annotation,
  position,
  onClose,
  onViewDetails
}: {
  annotation: AgentAnnotation
  position: { x: number; y: number }
  onClose: () => void
  onViewDetails: () => void
}) {
  const agentType = AGENT_TYPES[annotation.agentId as keyof typeof AGENT_TYPES] || {
    name: annotation.agentName,
    icon: '🤖',
    color: '#6b7280',
    description: 'AI Trading Agent'
  }

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'low': return 'text-green-400 bg-green-900/20'
      case 'medium': return 'text-yellow-400 bg-yellow-900/20'
      case 'high': return 'text-orange-400 bg-orange-900/20'
      case 'critical': return 'text-red-400 bg-red-900/20'
      default: return 'text-gray-400 bg-gray-900/20'
    }
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'buy': return 'text-green-400'
      case 'sell': return 'text-red-400'
      case 'hold': return 'text-yellow-400'
      case 'close': return 'text-gray-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div
      className="fixed z-50 bg-gray-900 border border-gray-600 rounded-lg p-4 shadow-lg max-w-sm"
      style={{
        left: Math.min(position.x, window.innerWidth - 320),
        top: Math.max(position.y - 100, 10)
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-lg">{agentType.icon}</span>
          <div>
            <div className="font-medium text-white text-sm">{agentType.name}</div>
            <div className="text-xs text-gray-400">{annotation.type.toUpperCase()}</div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white text-lg"
        >
          ×
        </button>
      </div>

      {/* Action and Price */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className={`font-semibold uppercase text-sm ${getActionColor(annotation.action)}`}>
            {annotation.action}
          </span>
          <span className="text-gray-400">@</span>
          <span className="font-mono text-white font-semibold">
            {annotation.price.toFixed(4)}
          </span>
        </div>
        <div className="text-sm text-gray-400">
          Size: {annotation.size.toLocaleString()}
        </div>
      </div>

      {/* Confidence and Risk */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Confidence</div>
          <div className={`text-sm font-semibold ${
            annotation.confidence > 0.8 ? 'text-green-400' :
            annotation.confidence > 0.6 ? 'text-yellow-400' : 'text-red-400'
          }`}>
            {(annotation.confidence * 100).toFixed(0)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Risk Level</div>
          <div className={`text-xs px-2 py-1 rounded ${getRiskLevelColor(annotation.riskAssessment.level)}`}>
            {annotation.riskAssessment.level.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Risk Assessment */}
      <div className="mb-3 p-2 bg-gray-800 rounded">
        <div className="text-xs text-gray-400 mb-2">Risk Assessment</div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-gray-400">R:R Ratio: </span>
            <span className="text-white font-mono">
              {annotation.riskAssessment.riskRewardRatio.toFixed(1)}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Max Loss: </span>
            <span className="text-red-400 font-mono">
              ${annotation.riskAssessment.maxLoss}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Stop Loss: </span>
            <span className="text-orange-400 font-mono">
              {annotation.riskAssessment.stopLossDistance} pips
            </span>
          </div>
          <div>
            <span className="text-gray-400">Take Profit: </span>
            <span className="text-green-400 font-mono">
              {annotation.riskAssessment.takeProfitDistance} pips
            </span>
          </div>
        </div>
      </div>

      {/* Rationale */}
      <div className="mb-3">
        <div className="text-xs text-gray-400 mb-1">Decision Rationale</div>
        <div className="text-sm text-gray-200 leading-relaxed">
          {annotation.rationale}
        </div>
      </div>

      {/* Supporting Data */}
      {Object.keys(annotation.supportingData).length > 0 && (
        <div className="mb-3 p-2 bg-gray-800 rounded">
          <div className="text-xs text-gray-400 mb-2">Supporting Data</div>
          <div className="space-y-1">
            {Object.entries(annotation.supportingData).slice(0, 3).map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs">
                <span className="text-gray-400 capitalize">
                  {key.replace(/_/g, ' ')}:
                </span>
                <span className="text-white font-mono">
                  {typeof value === 'number' ? value.toFixed(2) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timestamp */}
      <div className="text-xs text-gray-400 mb-3">
        {new Date(annotation.timestamp).toLocaleString()}
      </div>

      {/* Actions */}
      <div className="flex space-x-2">
        <button
          onClick={onViewDetails}
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs py-2 px-3 rounded"
        >
          View Details
        </button>
      </div>
    </div>
  )
}

/**
 * Annotation marker component
 */
function AnnotationMarker({
  annotation,
  position,
  onHover,
  onLeave,
  onClick,
  isHovered = false
}: {
  annotation: AgentAnnotation
  position: { x: number; y: number }
  onHover: (annotation: AgentAnnotation, event: React.MouseEvent) => void
  onLeave: () => void
  onClick: (annotation: AgentAnnotation) => void
  isHovered?: boolean
}) {
  const agentType = AGENT_TYPES[annotation.agentId as keyof typeof AGENT_TYPES] || {
    name: annotation.agentName,
    icon: '🤖',
    color: '#6b7280',
    description: 'AI Trading Agent'
  }

  const getMarkerStyle = () => {
    const baseStyle = {
      position: 'absolute' as const,
      left: position.x - 8,
      top: position.y - 8,
      width: 16,
      height: 16,
      borderRadius: '50%',
      border: '2px solid',
      borderColor: agentType.color,
      backgroundColor: annotation.action === 'buy' ? '#22c55e' : 
                       annotation.action === 'sell' ? '#ef4444' : 
                       '#6b7280',
      cursor: 'pointer',
      transform: isHovered ? 'scale(1.2)' : 'scale(1)',
      transition: 'transform 0.2s ease',
      zIndex: isHovered ? 30 : 20
    }

    return baseStyle
  }

  return (
    <div
      style={getMarkerStyle()}
      onMouseEnter={(e) => onHover(annotation, e)}
      onMouseLeave={onLeave}
      onClick={() => onClick(annotation)}
      title={`${agentType.name} - ${annotation.action.toUpperCase()}`}
    >
      {/* Confidence ring */}
      <div
        className="absolute inset-0 rounded-full border-2"
        style={{
          borderColor: agentType.color,
          opacity: annotation.confidence,
          animation: isHovered ? 'pulse 1s infinite' : 'none'
        }}
      />
      
      {/* Agent icon (very small) */}
      <div className="absolute inset-0 flex items-center justify-center text-xs">
        {annotation.action === 'buy' ? '↗' : 
         annotation.action === 'sell' ? '↘' : 
         '•'}
      </div>
    </div>
  )
}

/**
 * Annotations legend
 */
function AnnotationsLegend({
  annotations,
  onToggleAgent,
  onToggleType,
  enabledAgents,
  enabledTypes,
  compact = false
}: {
  annotations: AgentAnnotation[]
  onToggleAgent: (agentId: string) => void
  onToggleType: (type: string) => void
  enabledAgents: Set<string>
  enabledTypes: Set<string>
  compact?: boolean
}) {
  const agentCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    annotations.forEach(annotation => {
      counts[annotation.agentId] = (counts[annotation.agentId] || 0) + 1
    })
    return counts
  }, [annotations])

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    annotations.forEach(annotation => {
      counts[annotation.type] = (counts[annotation.type] || 0) + 1
    })
    return counts
  }, [annotations])

  if (compact) {
    return (
      <div className="p-2 bg-gray-800 rounded border border-gray-700">
        <div className="text-xs text-gray-400 mb-2">AI Annotations ({annotations.length})</div>
        <div className="flex flex-wrap gap-1">
          {Object.entries(agentCounts).slice(0, 4).map(([agentId, count]) => {
            const agentType = AGENT_TYPES[agentId as keyof typeof AGENT_TYPES] || {
              name: agentId,
              icon: '🤖',
              color: '#6b7280'
            }
            
            return (
              <button
                key={agentId}
                onClick={() => onToggleAgent(agentId)}
                className={`px-2 py-1 text-xs rounded flex items-center space-x-1 ${
                  enabledAgents.has(agentId)
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300'
                }`}
              >
                <span>{agentType.icon}</span>
                <span>{count}</span>
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h4 className="font-medium text-white mb-2">AI Agents</h4>
        <div className="space-y-2">
          {Object.entries(agentCounts).map(([agentId, count]) => {
            const agentType = AGENT_TYPES[agentId as keyof typeof AGENT_TYPES] || {
              name: agentId,
              icon: '🤖',
              color: '#6b7280',
              description: 'AI Trading Agent'
            }
            
            return (
              <div key={agentId} className="flex items-center justify-between">
                <button
                  onClick={() => onToggleAgent(agentId)}
                  className="flex items-center space-x-3 flex-1 text-left"
                >
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={enabledAgents.has(agentId)}
                      onChange={() => onToggleAgent(agentId)}
                      className="text-blue-600"
                    />
                    <span className="text-lg">{agentType.icon}</span>
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: agentType.color }}
                    />
                  </div>
                  <div>
                    <div className="text-sm text-white">{agentType.name}</div>
                    <div className="text-xs text-gray-400">{agentType.description}</div>
                  </div>
                </button>
                <span className="text-sm text-gray-400">
                  {count} annotations
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <div>
        <h4 className="font-medium text-white mb-2">Annotation Types</h4>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(typeCounts).map(([type, count]) => (
            <button
              key={type}
              onClick={() => onToggleType(type)}
              className={`p-2 rounded text-left ${
                enabledTypes.has(type)
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              <div className="text-sm font-medium capitalize">
                {type.replace('_', ' ')}
              </div>
              <div className="text-xs opacity-75">
                {count} annotations
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

/**
 * Annotation details modal
 */
function AnnotationDetailsModal({
  annotation,
  onClose
}: {
  annotation: AgentAnnotation | null
  onClose: () => void
}) {
  if (!annotation) return null

  const agentType = AGENT_TYPES[annotation.agentId as keyof typeof AGENT_TYPES] || {
    name: annotation.agentName,
    icon: '🤖',
    color: '#6b7280',
    description: 'AI Trading Agent'
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg border border-gray-600 p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{agentType.icon}</span>
            <div>
              <h2 className="text-xl font-semibold text-white">{agentType.name}</h2>
              <p className="text-gray-400">{agentType.description}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        {/* Decision Summary */}
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center">
              <div className="text-sm text-gray-400">Action</div>
              <div className={`text-lg font-semibold uppercase ${
                annotation.action === 'buy' ? 'text-green-400' :
                annotation.action === 'sell' ? 'text-red-400' : 'text-gray-400'
              }`}>
                {annotation.action}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-400">Price</div>
              <div className="text-lg font-mono font-semibold text-white">
                {annotation.price.toFixed(4)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-400">Size</div>
              <div className="text-lg font-semibold text-white">
                {annotation.size.toLocaleString()}
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-400">Confidence</div>
              <div className={`text-lg font-semibold ${
                annotation.confidence > 0.8 ? 'text-green-400' :
                annotation.confidence > 0.6 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {(annotation.confidence * 100).toFixed(0)}%
              </div>
            </div>
          </div>
          
          <div className="text-sm text-gray-400 mb-2">Decision Time</div>
          <div className="text-white">
            {new Date(annotation.timestamp).toLocaleString()}
          </div>
        </div>

        {/* Risk Assessment */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">Risk Assessment</h3>
          <div className="p-4 bg-gray-800 rounded-lg">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-sm text-gray-400">Risk Level</div>
                <div className={`inline-block px-3 py-1 rounded text-sm font-semibold ${
                  annotation.riskAssessment.level === 'low' ? 'bg-green-900 text-green-200' :
                  annotation.riskAssessment.level === 'medium' ? 'bg-yellow-900 text-yellow-200' :
                  annotation.riskAssessment.level === 'high' ? 'bg-orange-900 text-orange-200' :
                  'bg-red-900 text-red-200'
                }`}>
                  {annotation.riskAssessment.level.toUpperCase()}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-400">Risk:Reward</div>
                <div className="text-lg font-mono font-semibold text-white">
                  1:{annotation.riskAssessment.riskRewardRatio.toFixed(1)}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-400">Max Loss</div>
                <div className="text-lg font-semibold text-red-400">
                  ${annotation.riskAssessment.maxLoss}
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-400">Stop Loss</div>
                <div className="text-sm font-mono text-orange-400">
                  {annotation.riskAssessment.stopLossDistance} pips
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-400">Take Profit</div>
                <div className="text-sm font-mono text-green-400">
                  {annotation.riskAssessment.takeProfitDistance} pips
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-400">Expected Profit</div>
                <div className="text-sm font-semibold text-green-400">
                  ${annotation.riskAssessment.expectedProfit}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Decision Rationale */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">Decision Rationale</h3>
          <div className="p-4 bg-gray-800 rounded-lg">
            <p className="text-gray-200 leading-relaxed">
              {annotation.rationale}
            </p>
          </div>
        </div>

        {/* Supporting Data */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-white mb-3">Supporting Data</h3>
          <div className="p-4 bg-gray-800 rounded-lg">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(annotation.supportingData).map(([key, value]) => (
                <div key={key} className="flex justify-between items-center">
                  <span className="text-gray-400 capitalize">
                    {key.replace(/_/g, ' ')}:
                  </span>
                  <span className="font-mono text-white font-semibold">
                    {typeof value === 'number' ? 
                      value.toFixed(key.includes('price') || key.includes('level') ? 4 : 2) : 
                      String(value)
                    }
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * Props for AIAgentAnnotations component
 */
interface AIAgentAnnotationsProps {
  /** Instrument symbol */
  instrument: string
  /** Chart timeframe */
  timeframe: ChartTimeframe
  /** Chart container dimensions */
  chartDimensions: { width: number; height: number }
  /** Price data for coordinate calculation */
  priceData: OHLCV[]
  /** Visible price range */
  visibleRange: { from: number; to: number }
  /** Enable annotations */
  enabled?: boolean
  /** Callback when annotation is clicked */
  onAnnotationClick?: (annotation: AgentAnnotation) => void
  /** Compact display mode */
  compact?: boolean
}

/**
 * Main AIAgentAnnotations component
 */
export function AIAgentAnnotations({
  instrument,
  timeframe,
  chartDimensions,
  priceData,
  visibleRange,
  enabled = true,
  onAnnotationClick,
  compact = false
}: AIAgentAnnotationsProps) {
  const [annotations, setAnnotations] = useState<AgentAnnotation[]>([])
  const [enabledAgents, setEnabledAgents] = useState<Set<string>>(new Set())
  const [enabledTypes, setEnabledTypes] = useState<Set<string>>(new Set(['entry', 'exit']))
  const [hoveredAnnotation, setHoveredAnnotation] = useState<{
    annotation: AgentAnnotation
    position: { x: number; y: number }
  } | null>(null)
  const [selectedAnnotation, setSelectedAnnotation] = useState<AgentAnnotation | null>(null)

  const { actions, state } = useMarketData()

  /**
   * Load annotations from service
   */
  const loadAnnotations = useCallback(async () => {
    if (!enabled || priceData.length === 0) return

    try {
      const from = new Date(priceData[0].timestamp)
      const to = new Date(priceData[priceData.length - 1].timestamp)
      
      await actions.loadAIAnnotations(instrument, from, to)
    } catch (error) {
      console.error('Failed to load AI annotations:', error)
    }
  }, [enabled, priceData, actions, instrument])

  /**
   * Filter visible annotations
   */
  const visibleAnnotations = useMemo(() => {
    const instrumentAnnotations = state.aiAnnotations.get(instrument) || []
    
    return instrumentAnnotations.filter(annotation => {
      // Filter by enabled agents
      if (!enabledAgents.has(annotation.agentId) && enabledAgents.size > 0) {
        return false
      }
      
      // Filter by enabled types
      if (!enabledTypes.has(annotation.type) && enabledTypes.size > 0) {
        return false
      }
      
      // Filter by visible time range
      return annotation.timestamp >= visibleRange.from && 
             annotation.timestamp <= visibleRange.to
    })
  }, [state.aiAnnotations, instrument, enabledAgents, enabledTypes, visibleRange])

  /**
   * Calculate annotation screen positions
   */
  const annotationPositions = useMemo(() => {
    if (!priceData.length || !chartDimensions.width || !chartDimensions.height) {
      return []
    }

    const timeRange = visibleRange.to - visibleRange.from
    const priceRange = Math.max(...priceData.map(d => d.high)) - Math.min(...priceData.map(d => d.low))

    return visibleAnnotations.map(annotation => {
      // Calculate X position (time-based)
      const timePercent = (annotation.timestamp - visibleRange.from) / timeRange
      const x = timePercent * chartDimensions.width

      // Calculate Y position (price-based)
      const minPrice = Math.min(...priceData.map(d => d.low))
      const pricePercent = (annotation.price - minPrice) / priceRange
      const y = chartDimensions.height - (pricePercent * chartDimensions.height)

      return {
        annotation,
        position: { x, y }
      }
    }).filter(item => 
      item.position.x >= 0 && 
      item.position.x <= chartDimensions.width &&
      item.position.y >= 0 && 
      item.position.y <= chartDimensions.height
    )
  }, [visibleAnnotations, priceData, chartDimensions, visibleRange])

  /**
   * Handle annotation hover
   */
  const handleAnnotationHover = useCallback((annotation: AgentAnnotation, event: React.MouseEvent) => {
    setHoveredAnnotation({
      annotation,
      position: { x: event.clientX, y: event.clientY }
    })
  }, [])

  /**
   * Handle annotation leave
   */
  const handleAnnotationLeave = useCallback(() => {
    setHoveredAnnotation(null)
  }, [])

  /**
   * Handle annotation click
   */
  const handleAnnotationClick = useCallback((annotation: AgentAnnotation) => {
    setSelectedAnnotation(annotation)
    onAnnotationClick?.(annotation)
  }, [onAnnotationClick])

  /**
   * Toggle agent visibility
   */
  const handleToggleAgent = useCallback((agentId: string) => {
    setEnabledAgents(prev => {
      const newSet = new Set(prev)
      if (newSet.has(agentId)) {
        newSet.delete(agentId)
      } else {
        newSet.add(agentId)
      }
      return newSet
    })
  }, [])

  /**
   * Toggle type visibility
   */
  const handleToggleType = useCallback((type: string) => {
    setEnabledTypes(prev => {
      const newSet = new Set(prev)
      if (newSet.has(type)) {
        newSet.delete(type)
      } else {
        newSet.add(type)
      }
      return newSet
    })
  }, [])

  /**
   * Initialize with all agents enabled
   */
  useEffect(() => {
    const allAnnotations = state.aiAnnotations.get(instrument) || []
    const agentIds = new Set(allAnnotations.map(a => a.agentId))
    setEnabledAgents(agentIds)
  }, [state.aiAnnotations, instrument])

  /**
   * Load annotations when component mounts or dependencies change
   */
  useEffect(() => {
    loadAnnotations()
  }, [loadAnnotations])

  if (!enabled) {
    return (
      <div className="text-center p-4 text-gray-400">
        <div className="text-sm">AI Agent annotations disabled</div>
      </div>
    )
  }

  const allAnnotations = state.aiAnnotations.get(instrument) || []

  return (
    <div className="space-y-4">
      {/* Annotations Legend */}
      <AnnotationsLegend
        annotations={allAnnotations}
        onToggleAgent={handleToggleAgent}
        onToggleType={handleToggleType}
        enabledAgents={enabledAgents}
        enabledTypes={enabledTypes}
        compact={compact}
      />

      {/* Chart Overlay - Annotation Markers */}
      <div className="relative">
        {annotationPositions.map(({ annotation, position }, index) => (
          <AnnotationMarker
            key={`${annotation.id}_${index}`}
            annotation={annotation}
            position={position}
            onHover={handleAnnotationHover}
            onLeave={handleAnnotationLeave}
            onClick={handleAnnotationClick}
            isHovered={hoveredAnnotation?.annotation.id === annotation.id}
          />
        ))}
      </div>

      {/* Hover Tooltip */}
      {hoveredAnnotation && (
        <AnnotationTooltip
          annotation={hoveredAnnotation.annotation}
          position={hoveredAnnotation.position}
          onClose={handleAnnotationLeave}
          onViewDetails={() => setSelectedAnnotation(hoveredAnnotation.annotation)}
        />
      )}

      {/* Details Modal */}
      <AnnotationDetailsModal
        annotation={selectedAnnotation}
        onClose={() => setSelectedAnnotation(null)}
      />

      {/* Loading State */}
      {state.loading.annotations && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto mb-2"></div>
          <div className="text-sm text-gray-400">Loading AI annotations...</div>
        </div>
      )}

      {/* Error State */}
      {state.errors.annotations && (
        <div className="p-3 bg-red-900/20 border border-red-500/30 rounded text-red-200 text-sm">
          Error loading annotations: {state.errors.annotations}
        </div>
      )}
    </div>
  )
}

export default AIAgentAnnotations