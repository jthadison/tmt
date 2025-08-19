/**
 * Real-time Store Tests
 */

import RealTimeStore from '@/store/realTimeStore'
import { WebSocketMessage, MessageType, AccountUpdate } from '@/types/websocket'

describe('RealTimeStore', () => {
  let store: RealTimeStore
  
  beforeEach(() => {
    store = new RealTimeStore()
  })

  describe('processMessage', () => {
    it('should process account update messages', (done) => {
      const accountUpdate: AccountUpdate = {
        account_id: 'acc-001',
        balance: 10000,
        equity: 10500,
        margin: 1000,
        free_margin: 9500,
        margin_level: 1050
      }
      
      const message: WebSocketMessage = {
        type: MessageType.ACCOUNT_UPDATE,
        data: accountUpdate,
        timestamp: new Date().toISOString(),
        correlation_id: 'test-123'
      }
      
      // Subscribe to state changes
      store.subscribe((state) => {
        const account = state.accounts.get('acc-001')
        if (account) {
          expect(account.balance).toBe(10000)
          expect(account.equity).toBe(10500)
          expect(account.status).toBe('healthy')
          done()
        }
      })
      
      store.processMessage(message)
    })
    
    it('should batch multiple messages', (done) => {
      let updateCount = 0
      
      store.subscribe(() => {
        updateCount++
      })
      
      // Send multiple messages rapidly
      for (let i = 0; i < 5; i++) {
        const message: WebSocketMessage = {
          type: MessageType.ACCOUNT_UPDATE,
          data: {
            account_id: `acc-${i}`,
            balance: 10000 + i,
            equity: 10000 + i,
            margin: 0,
            free_margin: 10000 + i,
            margin_level: 0
          },
          timestamp: new Date().toISOString(),
          correlation_id: `test-${i}`
        }
        store.processMessage(message)
      }
      
      // Messages should be batched
      setTimeout(() => {
        // Should have received fewer updates than messages due to batching
        expect(updateCount).toBeLessThan(6) // Initial + batched updates
        expect(store.getState().accounts.size).toBe(5)
        done()
      }, 100)
    })
  })

  describe('subscribe', () => {
    it('should notify subscribers of state changes', () => {
      const callback = jest.fn()
      const unsubscribe = store.subscribe(callback)
      
      // Should receive initial state
      expect(callback).toHaveBeenCalledTimes(1)
      expect(callback).toHaveBeenCalledWith(
        expect.objectContaining({
          accounts: expect.any(Map),
          positions: expect.any(Map),
          prices: expect.any(Map),
          systemStatus: expect.any(Map),
          connectionStatus: 'disconnected'
        })
      )
      
      // Update connection status
      store.setConnectionStatus('connected')
      expect(callback).toHaveBeenCalledTimes(2)
      
      // Unsubscribe
      unsubscribe()
      
      // Should not receive further updates
      store.setConnectionStatus('disconnected')
      expect(callback).toHaveBeenCalledTimes(2)
    })
  })

  describe('onMessage', () => {
    it('should call registered message handlers', (done) => {
      const handler = jest.fn()
      
      const unsubscribe = store.onMessage(MessageType.ACCOUNT_UPDATE, handler)
      
      const message: WebSocketMessage = {
        type: MessageType.ACCOUNT_UPDATE,
        data: {
          account_id: 'acc-001',
          balance: 10000,
          equity: 10000,
          margin: 0,
          free_margin: 10000,
          margin_level: 0
        },
        timestamp: new Date().toISOString(),
        correlation_id: 'test-123'
      }
      
      store.processMessage(message)
      
      setTimeout(() => {
        expect(handler).toHaveBeenCalledWith(message)
        unsubscribe()
        done()
      }, 100)
    })
    
    it('should not call handlers for different message types', (done) => {
      const handler = jest.fn()
      
      store.onMessage(MessageType.POSITION_UPDATE, handler)
      
      const message: WebSocketMessage = {
        type: MessageType.ACCOUNT_UPDATE,
        data: {},
        timestamp: new Date().toISOString(),
        correlation_id: 'test-123'
      }
      
      store.processMessage(message)
      
      setTimeout(() => {
        expect(handler).not.toHaveBeenCalled()
        done()
      }, 100)
    })
  })

  describe('account status determination', () => {
    it('should set correct status based on margin level', (done) => {
      const testCases = [
        { margin_level: 50, expected: 'danger' },
        { margin_level: 150, expected: 'warning' },
        { margin_level: 300, expected: 'healthy' }
      ]
      
      let processedCount = 0
      
      store.subscribe((state) => {
        if (state.accounts.size === testCases.length) {
          testCases.forEach((testCase, index) => {
            const account = state.accounts.get(`acc-${index}`)
            expect(account?.status).toBe(testCase.expected)
          })
          done()
        }
      })
      
      testCases.forEach((testCase, index) => {
        const message: WebSocketMessage = {
          type: MessageType.ACCOUNT_UPDATE,
          data: {
            account_id: `acc-${index}`,
            balance: 10000,
            equity: 10000,
            margin: 1000,
            free_margin: 9000,
            margin_level: testCase.margin_level
          },
          timestamp: new Date().toISOString(),
          correlation_id: `test-${index}`
        }
        store.processMessage(message)
      })
    })
  })

  describe('clear', () => {
    it('should clear all state', () => {
      // Add some data
      const message: WebSocketMessage = {
        type: MessageType.ACCOUNT_UPDATE,
        data: {
          account_id: 'acc-001',
          balance: 10000,
          equity: 10000,
          margin: 0,
          free_margin: 10000,
          margin_level: 0
        },
        timestamp: new Date().toISOString(),
        correlation_id: 'test-123'
      }
      
      store.processMessage(message)
      store.setConnectionStatus('connected')
      
      // Wait for processing
      setTimeout(() => {
        expect(store.getState().accounts.size).toBeGreaterThan(0)
        expect(store.getState().connectionStatus).toBe('connected')
        
        // Clear
        store.clear()
        
        const state = store.getState()
        expect(state.accounts.size).toBe(0)
        expect(state.positions.size).toBe(0)
        expect(state.prices.size).toBe(0)
        expect(state.systemStatus.size).toBe(0)
        expect(state.connectionStatus).toBe('disconnected')
        expect(state.lastUpdate).toBeNull()
      }, 100)
    })
  })
})