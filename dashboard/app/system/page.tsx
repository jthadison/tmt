'use client'

import { useState, useEffect } from 'react'
import MainLayout from '@/components/layout/MainLayout'
import { CircuitBreakerPanel } from '@/components/control-panel/CircuitBreakerPanel'
import { EmergencyStop } from '@/components/control-panel/EmergencyStop'
import { CircuitBreakerInfo, EmergencyStopStatus } from '@/types/systemControl'

export default function SystemControlPage() {
  const [circuitBreakers, setCircuitBreakers] = useState<CircuitBreakerInfo[]>([])
  const [emergencyStopStatus, setEmergencyStopStatus] = useState<EmergencyStopStatus>({
    isActive: false,
    triggeredBy: '',
    reason: 'manual_intervention',
    triggeredAt: undefined,
    affectedAccounts: 0,
    positionsClosing: 0,
    contactsNotified: []
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Mock circuit breaker data - in production this would come from the orchestrator API
  const mockCircuitBreakers: CircuitBreakerInfo[] = [
    {
      id: 'system_health',
      name: 'System Health',
      category: 'System',
      status: 'open', // This should be 'open' based on our emergency stop test
      description: 'Overall system health monitoring',
      threshold: 5,
      failures: 5,
      successRate: 0,
      isManualOverride: false,
      lastTriggered: new Date()
    },
    {
      id: 'account_loss',
      name: 'Account Loss',
      category: 'Risk',
      status: 'closed',
      description: 'Daily loss threshold monitoring',
      threshold: 10,
      failures: 2,
      successRate: 95.5,
      isManualOverride: false
    },
    {
      id: 'position_size',
      name: 'Position Size',
      category: 'Risk',
      status: 'closed',
      description: 'Maximum position size enforcement',
      threshold: 15,
      failures: 0,
      successRate: 100,
      isManualOverride: false
    },
    {
      id: 'rate_limit',
      name: 'Rate Limiting',
      category: 'System',
      status: 'closed',
      description: 'API rate limiting protection',
      threshold: 20,
      failures: 1,
      successRate: 98.2,
      isManualOverride: false
    }
  ]

  useEffect(() => {
    // Fetch circuit breaker status from orchestrator
    fetchCircuitBreakerStatus()
  }, [])

  const fetchCircuitBreakerStatus = async () => {
    try {
      setLoading(true)
      
      // Try to fetch from orchestrator
      const orchestratorUrl = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8083'
      
      try {
        const response = await fetch(`${orchestratorUrl}/health`)
        
        if (response.ok) {
          const healthData = await response.json()
          
          // Update emergency stop status
          setEmergencyStopStatus({
            isActive: !healthData.trading_enabled,
            triggeredBy: 'System',
            reason: healthData.trading_enabled ? 'manual_intervention' : 'emergency_stop',
            triggeredAt: healthData.circuit_breaker_status.last_trigger ? new Date(healthData.circuit_breaker_status.last_trigger) : undefined,
            affectedAccounts: healthData.connected_agents || 0,
            positionsClosing: 0,
            contactsNotified: []
          })
          
          // Update circuit breaker status based on health data
          const updatedBreakers = mockCircuitBreakers.map(breaker => {
            if (breaker.id === 'system_health') {
              return {
                ...breaker,
                status: healthData.circuit_breaker_status.system_breakers.system_health as 'open' | 'closed' | 'half-open'
              }
            }
            return breaker
          })
          
          setCircuitBreakers(updatedBreakers)
        } else {
          throw new Error(`Orchestrator responded with status ${response.status}`)
        }
      } catch (fetchError) {
        console.warn('Failed to fetch from orchestrator, using mock data:', fetchError)
        setError('Unable to connect to orchestrator - showing mock data')
        setCircuitBreakers(mockCircuitBreakers)
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load system status')
      setCircuitBreakers(mockCircuitBreakers)
    } finally {
      setLoading(false)
    }
  }

  const handleCircuitBreakerAction = (request: any) => {
    console.log('Circuit breaker action requested:', request)
    // This would typically call the trading controls service
    alert(`Circuit breaker action: ${request.action} for ${request.breakerId}\nReason: ${request.reason}`)
  }

  const handleResetAllBreakers = async () => {
    try {
      const orchestratorUrl = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8083'
      
      // Try the new circuit-breakers/reset endpoint first
      let response = await fetch(`${orchestratorUrl}/circuit-breakers/reset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      // If that fails with 404, try the start endpoint as fallback
      if (response.status === 404) {
        console.log('Circuit breaker reset endpoint not available, trying /start endpoint...')
        
        response = await fetch(`${orchestratorUrl}/start`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      }
      
      if (response.ok) {
        const result = await response.json()
        alert(`✅ Success: ${result.status || 'Trading restarted successfully'}\n\nTrading has been re-enabled!`)
        
        // Refresh the status
        await fetchCircuitBreakerStatus()
      } else {
        const errorText = await response.text()
        
        // Check if it's the expected circuit breaker error
        if (errorText.includes('Circuit breakers prevent trading')) {
          alert(`⚠️ Circuit breakers are still blocking trading.\n\nThis means the orchestrator's circuit breakers need to be manually reset.\n\nThe new reset endpoint requires restarting the orchestrator service.`)
        } else {
          alert(`❌ Failed to reset circuit breakers: ${response.status}\n\n${errorText}`)
        }
      }
    } catch (error) {
      console.error('Reset failed:', error)
      alert(`❌ Failed to reset circuit breakers: ${error}`)
    }
  }

  const handleEmergencyStop = (request: any) => {
    console.log('Emergency stop requested:', request)
    // This would call the emergency stop service
    alert(`Emergency stop requested!\nReason: ${request.reason || request.customReason}`)
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">System Control Panel</h1>
            <p className="text-gray-400 mt-1">
              Emergency controls and circuit breaker management
            </p>
          </div>
          <div className="text-sm text-gray-400">
            Last updated: {new Date().toLocaleTimeString()}
          </div>
        </div>

        {error && (
          <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4">
            <div className="text-yellow-400 font-medium">⚠️ Connection Warning</div>
            <div className="text-yellow-200 text-sm mt-1">{error}</div>
          </div>
        )}

        {/* Emergency Stop Control */}
        <EmergencyStop
          emergencyStopStatus={emergencyStopStatus}
          onEmergencyStop={handleEmergencyStop}
          loading={loading}
        />

        {/* Circuit Breaker Panel */}
        <CircuitBreakerPanel
          circuitBreakers={circuitBreakers}
          onCircuitBreakerAction={handleCircuitBreakerAction}
          onResetAllBreakers={handleResetAllBreakers}
          loading={loading}
        />

        {/* System Status Summary */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">System Status Summary</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-750 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Trading Status</div>
              <div className={`font-medium text-lg ${emergencyStopStatus.isActive ? 'text-red-400' : 'text-green-400'}`}>
                {emergencyStopStatus.isActive ? '🛑 STOPPED' : '✅ ACTIVE'}
              </div>
            </div>
            <div className="bg-gray-750 rounded-lg p-4">
              <div className="text-gray-400 text-sm">Circuit Breakers</div>
              <div className="font-medium text-lg text-white">
                {circuitBreakers.filter(cb => cb.status === 'closed').length} / {circuitBreakers.length} Closed
              </div>
            </div>
            <div className="bg-gray-750 rounded-lg p-4">
              <div className="text-gray-400 text-sm">System Health</div>
              <div className="font-medium text-lg text-green-400">
                ✅ HEALTHY
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => fetchCircuitBreakerStatus()}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium transition-colors"
            >
              🔄 Refresh Status
            </button>
            <button
              onClick={() => window.open('http://localhost:8083/health', '_blank')}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded font-medium transition-colors"
            >
              🔍 View Orchestrator Health
            </button>
            <button
              onClick={() => window.open('http://localhost:8082/health', '_blank')}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded font-medium transition-colors"
            >
              🎯 View Execution Engine
            </button>
          </div>
        </div>
      </div>
    </MainLayout>
  )
}