'use client'

import { useState } from 'react'
import { EmergencyStopStatus, EmergencyStopRequest, EmergencyStopReason } from '@/types/systemControl'

/**
 * Props for EmergencyStop component
 */
interface EmergencyStopProps {
  /** Current emergency stop status */
  emergencyStopStatus: EmergencyStopStatus
  /** Callback when emergency stop is triggered */
  onEmergencyStop: (request: EmergencyStopRequest) => void
  /** Loading state indicator */
  loading?: boolean
}

/**
 * Emergency stop control with prominent button and multi-step confirmation
 * Critical safety component for immediate system shutdown
 */
export function EmergencyStop({
  emergencyStopStatus,
  onEmergencyStop,
  loading = false
}: EmergencyStopProps) {
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [selectedReason, setSelectedReason] = useState<EmergencyStopReason>('manual_intervention')
  const [customReason, setCustomReason] = useState('')
  const [confirmationCode, setConfirmationCode] = useState('')
  const [notifyContacts, setNotifyContacts] = useState(true)
  const [step, setStep] = useState(1) // 1: reason, 2: confirmation, 3: final

  const emergencyReasons: { value: EmergencyStopReason; label: string; description: string }[] = [
    {
      value: 'market_volatility',
      label: 'Extreme Market Volatility',
      description: 'Unusual market conditions requiring immediate halt'
    },
    {
      value: 'system_error',
      label: 'Critical System Error',
      description: 'Technical malfunction affecting trading operations'
    },
    {
      value: 'compliance_violation',
      label: 'Compliance Violation',
      description: 'Potential regulatory or rule violation detected'
    },
    {
      value: 'manual_intervention',
      label: 'Manual Intervention Required',
      description: 'Operator decision to halt trading'
    },
    {
      value: 'external_event',
      label: 'External Event',
      description: 'News or external factors requiring immediate stop'
    },
    {
      value: 'scheduled_maintenance',
      label: 'Emergency Maintenance',
      description: 'Urgent system maintenance required'
    }
  ]

  const generateConfirmationCode = (): string => {
    return Math.random().toString(36).substring(2, 8).toUpperCase()
  }

  const [requiredCode] = useState(generateConfirmationCode())

  const handleEmergencyClick = () => {
    if (emergencyStopStatus.isActive) {
      // Already active - could implement stop override here
      return
    }
    setShowConfirmation(true)
    setStep(1)
  }

  const handleReasonNext = () => {
    if (selectedReason || customReason.trim()) {
      setStep(2)
    }
  }

  const handleConfirmationNext = () => {
    if (confirmationCode.toUpperCase() === requiredCode) {
      setStep(3)
    }
  }

  const handleFinalConfirm = () => {
    const request: EmergencyStopRequest = {
      reason: selectedReason,
      customReason: customReason.trim() || undefined,
      confirmationCode: confirmationCode.toUpperCase(),
      notifyContacts
    }

    onEmergencyStop(request)
    handleCancel()
  }

  const handleCancel = () => {
    setShowConfirmation(false)
    setStep(1)
    setSelectedReason('manual_intervention')
    setCustomReason('')
    setConfirmationCode('')
    setNotifyContacts(true)
  }

  const formatTimeRemaining = (date: Date): string => {
    const diff = date.getTime() - Date.now()
    if (diff <= 0) return 'Complete'
    
    const minutes = Math.floor(diff / (60 * 1000))
    const seconds = Math.floor((diff % (60 * 1000)) / 1000)
    
    if (minutes > 0) return `${minutes}m ${seconds}s`
    return `${seconds}s`
  }

  if (loading) {
    return (
      <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-red-700/30 rounded w-48 mb-4"></div>
          <div className="h-12 bg-red-700/30 rounded w-32"></div>
        </div>
      </div>
    )
  }

  return (
    <>
      {/* Emergency Stop Panel */}
      <div className={`
        border rounded-lg p-6 transition-all duration-300
        ${emergencyStopStatus.isActive 
          ? 'bg-red-900/30 border-red-500' 
          : 'bg-red-900/10 border-red-500/30 hover:border-red-500/50'
        }
      `}>
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div className="flex-1">
            <h2 className="text-xl font-bold text-red-400 mb-2 flex items-center gap-2">
              🚨 Emergency Control
              {emergencyStopStatus.isActive && (
                <span className="text-sm bg-red-600 text-white px-2 py-1 rounded animate-pulse">
                  ACTIVE
                </span>
              )}
            </h2>
            
            {emergencyStopStatus.isActive ? (
              <div className="space-y-2">
                <p className="text-red-300">
                  Emergency stop is ACTIVE - All trading has been halted
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Triggered by:</span>
                    <span className="text-white ml-2">{emergencyStopStatus.triggeredBy}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Reason:</span>
                    <span className="text-white ml-2">
                      {emergencyStopStatus.customReason || emergencyStopStatus.reason}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">Time:</span>
                    <span className="text-white ml-2">
                      {emergencyStopStatus.triggeredAt?.toLocaleTimeString()}
                    </span>
                  </div>
                </div>
                
                {emergencyStopStatus.estimatedStopTime && (
                  <div className="mt-3 p-3 bg-red-800/30 rounded">
                    <div className="text-sm text-red-200">
                      <strong>Shutdown Progress:</strong>
                    </div>
                    <div className="text-sm text-gray-300 mt-1">
                      • {emergencyStopStatus.affectedAccounts} accounts affected
                    </div>
                    <div className="text-sm text-gray-300">
                      • {emergencyStopStatus.positionsClosing} positions closing
                    </div>
                    <div className="text-sm text-gray-300">
                      • ETA: {formatTimeRemaining(emergencyStopStatus.estimatedStopTime)}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-300">
                Immediately halt all trading operations across all accounts and agents
              </p>
            )}
          </div>
          
          <div className="flex items-center gap-4">
            {!emergencyStopStatus.isActive && (
              <button
                onClick={handleEmergencyClick}
                disabled={loading}
                className={`
                  relative px-8 py-4 rounded-lg font-bold text-lg transition-all duration-200
                  bg-red-600 hover:bg-red-700 text-white
                  border-2 border-red-500 hover:border-red-400
                  shadow-lg hover:shadow-red-500/25
                  disabled:opacity-50 disabled:cursor-not-allowed
                  transform hover:scale-105 active:scale-95
                `}
              >
                <span className="relative z-10">🛑 EMERGENCY STOP</span>
                <div className="absolute inset-0 bg-red-500 rounded-lg animate-pulse opacity-30"></div>
              </button>
            )}
            
            {emergencyStopStatus.contactsNotified.length > 0 && (
              <div className="text-sm text-gray-400">
                <div>Contacts Notified:</div>
                <div className="text-green-400">
                  {emergencyStopStatus.contactsNotified.join(', ')}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg max-w-md w-full border border-red-500">
            {/* Header */}
            <div className="p-6 border-b border-gray-700">
              <h3 className="text-xl font-bold text-red-400 flex items-center gap-2">
                🚨 Emergency Stop Confirmation
              </h3>
              <p className="text-gray-300 text-sm mt-2">
                This will immediately halt ALL trading operations
              </p>
            </div>

            {/* Step Content */}
            <div className="p-6">
              {step === 1 && (
                <div className="space-y-4">
                  <h4 className="font-medium text-white">Step 1: Select Reason</h4>
                  
                  <div className="space-y-3">
                    {emergencyReasons.map((reason) => (
                      <label key={reason.value} className="flex items-start gap-3 cursor-pointer">
                        <input
                          type="radio"
                          name="emergency-reason"
                          value={reason.value}
                          checked={selectedReason === reason.value}
                          onChange={(e) => setSelectedReason(e.target.value as EmergencyStopReason)}
                          className="mt-1"
                        />
                        <div>
                          <div className="text-white font-medium">{reason.label}</div>
                          <div className="text-gray-400 text-sm">{reason.description}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                  
                  <div>
                    <label className="block text-gray-300 text-sm mb-2">
                      Additional Details (Optional)
                    </label>
                    <textarea
                      value={customReason}
                      onChange={(e) => setCustomReason(e.target.value)}
                      placeholder="Provide additional context..."
                      rows={3}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                    />
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-4">
                  <h4 className="font-medium text-white">Step 2: Confirmation Required</h4>
                  
                  <div className="bg-red-900/20 border border-red-500/30 rounded p-4">
                    <div className="text-red-300 text-sm mb-2">
                      Type the following confirmation code to proceed:
                    </div>
                    <div className="text-red-400 font-mono text-xl font-bold">
                      {requiredCode}
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-gray-300 text-sm mb-2">
                      Confirmation Code
                    </label>
                    <input
                      type="text"
                      value={confirmationCode}
                      onChange={(e) => setConfirmationCode(e.target.value.toUpperCase())}
                      placeholder="Enter confirmation code"
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white font-mono"
                      maxLength={6}
                    />
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="notify-contacts"
                      checked={notifyContacts}
                      onChange={(e) => setNotifyContacts(e.target.checked)}
                      className="rounded border-gray-600 bg-gray-700 text-red-600"
                    />
                    <label htmlFor="notify-contacts" className="text-gray-300 text-sm">
                      Notify emergency contacts immediately
                    </label>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-4">
                  <h4 className="font-medium text-white">Step 3: Final Confirmation</h4>
                  
                  <div className="bg-red-900/30 border border-red-500 rounded p-4">
                    <div className="text-red-300 font-medium mb-2">
                      ⚠️ FINAL WARNING
                    </div>
                    <div className="text-red-200 text-sm space-y-1">
                      <div>• All trading will stop immediately</div>
                      <div>• Open positions will be closed</div>
                      <div>• All agents will be shut down</div>
                      <div>• Manual restart will be required</div>
                    </div>
                  </div>
                  
                  <div className="bg-gray-750 rounded p-3">
                    <div className="text-gray-300 text-sm">
                      <strong>Reason:</strong> {emergencyReasons.find(r => r.value === selectedReason)?.label}
                    </div>
                    {customReason && (
                      <div className="text-gray-300 text-sm mt-1">
                        <strong>Details:</strong> {customReason}
                      </div>
                    )}
                    <div className="text-gray-300 text-sm mt-1">
                      <strong>Notify Contacts:</strong> {notifyContacts ? 'Yes' : 'No'}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-gray-700 flex justify-between">
              <button
                onClick={handleCancel}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
              >
                Cancel
              </button>
              
              <div className="flex gap-3">
                {step > 1 && (
                  <button
                    onClick={() => setStep(step - 1)}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded transition-colors"
                  >
                    Back
                  </button>
                )}
                
                {step === 1 && (
                  <button
                    onClick={handleReasonNext}
                    disabled={!selectedReason}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                )}
                
                {step === 2 && (
                  <button
                    onClick={handleConfirmationNext}
                    disabled={confirmationCode.toUpperCase() !== requiredCode}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Confirm
                  </button>
                )}
                
                {step === 3 && (
                  <button
                    onClick={handleFinalConfirm}
                    className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-bold transition-colors"
                  >
                    🚨 EXECUTE EMERGENCY STOP
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}