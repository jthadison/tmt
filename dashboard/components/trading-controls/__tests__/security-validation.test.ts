/**
 * Security Validation Tests for Trading Controls
 * Story 9.5: Comprehensive security testing for administrator-only trading controls
 * 
 * These tests validate:
 * - Authentication and authorization
 * - Audit logging
 * - Input validation
 * - Access control enforcement
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals'
import { TradingControlsService, AuthenticationService, AuditService } from '@/services/tradingControlsService'
import { UserRole, SystemUser, SecurityError, AgentControlAction } from '@/types/tradingControls'

describe('Trading Controls Security Validation', () => {
  let tradingControlsService: TradingControlsService
  let authService: AuthenticationService
  let auditService: AuditService
  let mockUser: SystemUser

  beforeEach(() => {
    authService = new AuthenticationService()
    auditService = new AuditService()
    tradingControlsService = new TradingControlsService()

    mockUser = {
      id: 'admin_001',
      email: 'admin@proptrading.com',
      role: 'administrator' as UserRole,
      permissions: ['agent_control', 'emergency_stop', 'manual_trading', 'parameter_modification', 'audit_access'],
      isActive: true,
      createdAt: new Date(),
      lastLogin: new Date(),
      sessionId: 'session_123',
      mfaEnabled: true
    }

    // Mock authentication
    jest.spyOn(authService, 'getCurrentUser').mockReturnValue(mockUser)
    jest.spyOn(authService, 'isAuthenticated').mockReturnValue(true)
    jest.spyOn(authService, 'isAdministrator').mockReturnValue(true)
  })

  describe('Authentication and Authorization', () => {
    it('should require administrator access for all operations', async () => {
      // Mock non-admin user
      const regularUser = { ...mockUser, role: 'viewer' as UserRole }
      jest.spyOn(authService, 'getCurrentUser').mockReturnValue(regularUser)
      jest.spyOn(authService, 'isAdministrator').mockReturnValue(false)

      expect(() => {
        tradingControlsService.getSystemStatus()
      }).toThrow(SecurityError)
    })

    it('should validate user permissions for specific actions', () => {
      const userWithoutPermissions = { 
        ...mockUser, 
        permissions: ['audit_access'] // Only has audit access
      }
      jest.spyOn(authService, 'getCurrentUser').mockReturnValue(userWithoutPermissions)

      expect(() => {
        tradingControlsService.controlAgent('agent_001', 'pause', 'Test pause')
      }).toThrow('Insufficient permissions for agent control')
    })

    it('should enforce session validation', () => {
      const userWithExpiredSession = { ...mockUser, sessionId: null }
      jest.spyOn(authService, 'getCurrentUser').mockReturnValue(userWithExpiredSession)
      jest.spyOn(authService, 'isAuthenticated').mockReturnValue(false)

      expect(() => {
        tradingControlsService.getSystemStatus()
      }).toThrow('Authentication required')
    })

    it('should require MFA for high-risk operations', () => {
      const userWithoutMFA = { ...mockUser, mfaEnabled: false }
      jest.spyOn(authService, 'getCurrentUser').mockReturnValue(userWithoutMFA)

      expect(() => {
        tradingControlsService.emergencyStopAll('Emergency situation')
      }).toThrow('Multi-factor authentication required for emergency operations')
    })
  })

  describe('Audit Logging', () => {
    it('should log all administrator actions', async () => {
      const logSpy = jest.spyOn(auditService, 'logAction')

      await tradingControlsService.controlAgent('agent_001', 'pause', 'Routine maintenance')

      expect(logSpy).toHaveBeenCalledWith({
        userId: mockUser.id,
        userEmail: mockUser.email,
        action: 'agent_control',
        resource: 'agent',
        resourceId: 'agent_001',
        justification: 'Routine maintenance',
        ipAddress: expect.any(String),
        sessionId: mockUser.sessionId,
        timestamp: expect.any(Date),
        details: expect.objectContaining({
          agentId: 'agent_001',
          action: 'pause'
        })
      })
    })

    it('should log failed operations', async () => {
      const logSpy = jest.spyOn(auditService, 'logAction')
      
      // Mock a failure
      jest.spyOn(tradingControlsService, 'controlAgent').mockRejectedValue(new Error('Agent not found'))

      try {
        await tradingControlsService.controlAgent('nonexistent_agent', 'pause', 'Test')
      } catch (error) {
        // Expected to fail
      }

      expect(logSpy).toHaveBeenCalledWith(expect.objectContaining({
        result: 'failure',
        errorMessage: 'Agent not found'
      }))
    })

    it('should include risk assessment in audit logs', async () => {
      const logSpy = jest.spyOn(auditService, 'logAction')

      await tradingControlsService.emergencyStopAll('Critical system error detected')

      expect(logSpy).toHaveBeenCalledWith(expect.objectContaining({
        riskLevel: 'critical',
        complianceCheck: expect.objectContaining({
          passed: expect.any(Boolean),
          violations: expect.any(Array),
          warnings: expect.any(Array)
        })
      }))
    })
  })

  describe('Input Validation', () => {
    it('should validate justification requirements', () => {
      expect(() => {
        tradingControlsService.controlAgent('agent_001', 'pause', '')
      }).toThrow('Justification is required for all administrator actions')

      expect(() => {
        tradingControlsService.controlAgent('agent_001', 'pause', 'a'.repeat(10))
      }).toThrow('Justification must be at least 20 characters')
    })

    it('should validate agent IDs', () => {
      expect(() => {
        tradingControlsService.controlAgent('', 'pause', 'Valid justification for pause action')
      }).toThrow('Invalid agent ID')

      expect(() => {
        tradingControlsService.controlAgent('invalid-id-format', 'pause', 'Valid justification')
      }).toThrow('Invalid agent ID format')
    })

    it('should validate trade request parameters', async () => {
      const invalidTradeRequest = {
        action: 'market_buy' as any,
        instrument: '', // Invalid empty instrument
        quantity: -1000, // Invalid negative quantity
        accountId: 'account_001',
        justification: 'Test trade'
      }

      expect(() => {
        tradingControlsService.submitTradeRequest(invalidTradeRequest)
      }).toThrow('Invalid trade request parameters')
    })

    it('should validate risk parameter updates', () => {
      expect(() => {
        tradingControlsService.updateRiskParameter('param_001', NaN, 'Update parameter')
      }).toThrow('Invalid parameter value')

      expect(() => {
        tradingControlsService.updateRiskParameter('param_001', 9999999, 'Set very high value')
      }).toThrow('Parameter value exceeds maximum allowed range')
    })
  })

  describe('Access Control Enforcement', () => {
    it('should prevent concurrent emergency stops', async () => {
      // Mock an active emergency stop
      jest.spyOn(tradingControlsService, 'getEmergencyStops').mockResolvedValue([
        {
          id: 'stop_001',
          type: 'immediate_halt',
          isActive: true,
          triggeredAt: new Date(),
          triggeredBy: 'admin@proptrading.com',
          reason: 'Previous emergency',
          affectedAgents: ['agent_001']
        }
      ])

      expect(() => {
        tradingControlsService.emergencyStopAll('New emergency')
      }).toThrow('Emergency stop already active')
    })

    it('should enforce agent status constraints', () => {
      // Mock agent in emergency stop state
      const emergencyStoppedAgent = {
        id: 'agent_001',
        status: 'emergency_stop' as any,
        // ... other agent properties
      }

      expect(() => {
        tradingControlsService.controlAgent('agent_001', 'pause', 'Try to pause emergency stopped agent')
      }).toThrow('Cannot pause agent in emergency_stop state')
    })

    it('should validate risk parameter compliance', async () => {
      // Mock parameter requiring compliance approval
      const complianceRequiredParam = {
        id: 'param_001',
        complianceRequired: true,
        currentValue: 100,
        minValue: 0,
        maxValue: 1000
      }

      const result = await tradingControlsService.updateRiskParameter('param_001', 500, 'Update for new strategy')

      // Should require additional approval workflow
      expect(result).toEqual(expect.objectContaining({
        requiresApproval: true,
        approvalWorkflowId: expect.any(String)
      }))
    })
  })

  describe('Rate Limiting and Throttling', () => {
    it('should enforce rate limits on high-frequency actions', async () => {
      // Simulate rapid-fire agent control actions
      const promises = Array.from({ length: 10 }, (_, i) =>
        tradingControlsService.controlAgent(`agent_${i}`, 'pause', `Rapid action ${i}`)
      )

      // Should throttle after a certain threshold
      await expect(Promise.all(promises)).rejects.toThrow('Rate limit exceeded')
    })

    it('should implement cooling-off periods for emergency actions', async () => {
      await tradingControlsService.emergencyStopAll('First emergency')
      
      // Clear the emergency stop
      await tradingControlsService.clearEmergencyStop('stop_001', 'Emergency resolved')

      // Immediate second emergency stop should be throttled
      expect(() => {
        tradingControlsService.emergencyStopAll('Second emergency')
      }).toThrow('Emergency action cooling-off period active')
    })
  })

  describe('Data Sanitization', () => {
    it('should sanitize user inputs', async () => {
      const maliciousJustification = '<script>alert("xss")</script>Legitimate reason'
      const logSpy = jest.spyOn(auditService, 'logAction')

      await tradingControlsService.controlAgent('agent_001', 'pause', maliciousJustification)

      // Should sanitize the input in audit logs
      expect(logSpy).toHaveBeenCalledWith(expect.objectContaining({
        justification: 'Legitimate reason' // XSS payload removed
      }))
    })

    it('should prevent SQL injection in audit queries', async () => {
      const maliciousFilter = "'; DROP TABLE audit_logs; --"

      const auditLogs = await tradingControlsService.getAuditLogs({
        action: maliciousFilter as any
      })

      // Should return safe results without executing malicious SQL
      expect(auditLogs).toEqual(expect.any(Array))
    })
  })

  describe('Compliance Validation', () => {
    it('should enforce regulatory compliance rules', async () => {
      const highRiskTradeRequest = {
        action: 'market_buy' as any,
        instrument: 'EUR_USD',
        quantity: 10000000, // Very large position
        accountId: 'account_001',
        justification: 'High risk position for testing'
      }

      const result = await tradingControlsService.submitTradeRequest(highRiskTradeRequest)

      expect(result).toEqual(expect.objectContaining({
        complianceCheck: expect.objectContaining({
          passed: false,
          violations: expect.arrayContaining([
            expect.objectContaining({
              rule: 'position_size_limit',
              severity: 'high'
            })
          ])
        })
      }))
    })

    it('should validate parameter changes against compliance rules', async () => {
      const complianceViolatingValue = 999999 // Exceeds regulatory limits

      const result = await tradingControlsService.updateRiskParameter(
        'leverage_limit', 
        complianceViolatingValue, 
        'Attempt to set excessive leverage'
      )

      expect(result.complianceCheck.passed).toBe(false)
      expect(result.complianceCheck.violations).toContainEqual(
        expect.objectContaining({
          rule: 'max_leverage_regulatory',
          severity: 'critical'
        })
      )
    })
  })

  describe('Session Security', () => {
    it('should invalidate sessions after inactivity timeout', async () => {
      // Mock session timeout
      const expiredUser = { 
        ...mockUser, 
        lastActivity: new Date(Date.now() - 31 * 60 * 1000) // 31 minutes ago
      }
      jest.spyOn(authService, 'getCurrentUser').mockReturnValue(expiredUser)
      jest.spyOn(authService, 'isAuthenticated').mockReturnValue(false)

      expect(() => {
        tradingControlsService.getSystemStatus()
      }).toThrow('Session expired due to inactivity')
    })

    it('should prevent session hijacking', () => {
      const userWithMismatchedSession = {
        ...mockUser,
        sessionId: 'different_session',
        ipAddress: '192.168.1.100'
      }
      
      // Mock request from different IP
      const mockRequest = { ip: '10.0.0.50' }
      jest.spyOn(authService, 'validateSession').mockReturnValue(false)

      expect(() => {
        tradingControlsService.validateSecurityContext(mockRequest)
      }).toThrow('Potential session hijacking detected')
    })
  })
})

describe('Integration Security Tests', () => {
  it('should maintain security context across component interactions', async () => {
    // Test full workflow with security validation at each step
    const service = new TradingControlsService()
    
    // 1. Authentication check
    const systemStatus = await service.getSystemStatus()
    expect(systemStatus).toBeDefined()

    // 2. Agent control with audit logging
    const controlResult = await service.controlAgent('agent_001', 'pause', 'Integration test pause action')
    expect(controlResult).toBe(true)

    // 3. Emergency stop with enhanced logging
    const emergencyResult = await service.emergencyStopAll('Integration test emergency stop')
    expect(emergencyResult).toBe(true)

    // 4. Verify all actions were audited
    const auditLogs = await service.getAuditLogs()
    expect(auditLogs.length).toBeGreaterThanOrEqual(3)
  })

  it('should handle security failures gracefully', async () => {
    const service = new TradingControlsService()
    
    // Mock authentication failure
    jest.spyOn(service.authentication, 'requireAdministrator').mockImplementation(() => {
      throw new SecurityError('Authentication failed')
    })

    // Should not crash the system
    expect(() => service.getSystemStatus()).toThrow(SecurityError)
    
    // Should log the security failure
    const auditLogs = await service.getAuditLogs({ action: 'security_failure' })
    expect(auditLogs.length).toBeGreaterThan(0)
  })
})