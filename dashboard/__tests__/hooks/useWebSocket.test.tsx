import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { ConnectionStatus, MessageType } from '@/types/websocket'

// Crypto is already mocked in jest.setup.js

describe('useWebSocket Hook', () => {
  let mockWebSocket: any

  beforeEach(() => {
    // Reset WebSocket mock
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(() => {
        mockWebSocket.readyState = WebSocket.CLOSED
        if (mockWebSocket.onclose) {
          mockWebSocket.onclose({ wasClean: true })
        }
      }),
      readyState: WebSocket.CONNECTING,
      onopen: null,
      onclose: null,
      onmessage: null,
      onerror: null,
      url: ''
    }
    
    // Mock WebSocket constructor
    global.WebSocket = jest.fn((url) => {
      mockWebSocket.url = url
      mockWebSocket.readyState = WebSocket.CONNECTING
      return mockWebSocket
    }) as any
    
    // Add static constants
    global.WebSocket.CONNECTING = 0
    global.WebSocket.OPEN = 1
    global.WebSocket.CLOSING = 2
    global.WebSocket.CLOSED = 3
    
    jest.clearAllTimers()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
    jest.restoreAllMocks()
  })

  it('initializes with disconnected status', () => {
    const { result } = renderHook(() => 
      useWebSocket({ url: 'ws://localhost:8080' })
    )

    expect(result.current.connectionStatus).toBe(ConnectionStatus.DISCONNECTED)
    expect(result.current.lastMessage).toBeNull()
  })

  it('connects to WebSocket when connect is called', () => {
    const { result } = renderHook(() => 
      useWebSocket({ url: 'ws://localhost:8080' })
    )

    act(() => {
      result.current.connect()
    })

    expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8080', undefined)
    expect(result.current.connectionStatus).toBe(ConnectionStatus.CONNECTING)
  })

  it('updates status to connected when WebSocket opens', () => {
    const { result } = renderHook(() => 
      useWebSocket({ url: 'ws://localhost:8080' })
    )

    act(() => {
      result.current.connect()
    })

    // Simulate WebSocket open event
    act(() => {
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen()
      }
    })

    expect(result.current.connectionStatus).toBe(ConnectionStatus.CONNECTED)
  })

  it('sends messages when connected', () => {
    const { result } = renderHook(() => 
      useWebSocket({ url: 'ws://localhost:8080' })
    )

    act(() => {
      result.current.connect()
    })

    act(() => {
      mockWebSocket.readyState = WebSocket.OPEN
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen()
      }
    })

    const testMessage = { type: 'test', data: 'hello' }
    
    act(() => {
      result.current.sendMessage(testMessage)
    })

    expect(mockWebSocket.send).toHaveBeenCalledWith(
      expect.stringContaining('"type":"test"')
    )
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      expect.stringContaining('"data":"hello"')
    )
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      expect.stringContaining('"correlation_id":"test-uuid"')
    )
  })

  it('handles incoming messages', () => {
    const { result } = renderHook(() => 
      useWebSocket({ url: 'ws://localhost:8080' })
    )

    act(() => {
      result.current.connect()
    })

    const testMessage = {
      type: MessageType.ACCOUNT_UPDATE,
      data: { balance: 1000 },
      timestamp: '2023-01-01T00:00:00Z',
      correlation_id: 'test-id'
    }

    // Simulate receiving a message
    act(() => {
      if (mockWebSocket.onmessage) {
        mockWebSocket.onmessage({
          data: JSON.stringify(testMessage)
        })
      }
    })

    expect(result.current.lastMessage).toEqual(testMessage)
  })

  it('disconnects WebSocket when disconnect is called', () => {
    const { result } = renderHook(() => 
      useWebSocket({ url: 'ws://localhost:8080' })
    )

    act(() => {
      result.current.connect()
    })

    act(() => {
      result.current.disconnect()
    })

    expect(mockWebSocket.close).toHaveBeenCalled()
    expect(result.current.connectionStatus).toBe(ConnectionStatus.DISCONNECTED)
  })

  it('attempts reconnection on connection close', () => {
    const { result } = renderHook(() => 
      useWebSocket({ 
        url: 'ws://localhost:8080',
        reconnectAttempts: 2,
        reconnectInterval: 1000
      })
    )

    act(() => {
      result.current.connect()
    })

    // First connect to open state
    act(() => {
      mockWebSocket.readyState = WebSocket.OPEN
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen()
      }
    })

    // Simulate connection close (not manual disconnect)
    act(() => {
      mockWebSocket.readyState = WebSocket.CLOSED
      if (mockWebSocket.onclose) {
        mockWebSocket.onclose({ wasClean: false })
      }
    })

    expect(result.current.connectionStatus).toBe(ConnectionStatus.RECONNECTING)
    
    // Fast-forward time to trigger reconnection
    act(() => {
      jest.advanceTimersByTime(1000)
    })

    // Should attempt to create new WebSocket connection
    expect(global.WebSocket).toHaveBeenCalledTimes(2)
  })

  it('sends heartbeat messages when connected', () => {
    const { result } = renderHook(() => 
      useWebSocket({ 
        url: 'ws://localhost:8080',
        heartbeatInterval: 1000
      })
    )

    act(() => {
      result.current.connect()
    })

    act(() => {
      mockWebSocket.readyState = WebSocket.OPEN
      if (mockWebSocket.onopen) {
        mockWebSocket.onopen()
      }
    })

    // Fast-forward to trigger heartbeat
    act(() => {
      jest.advanceTimersByTime(1001)
    })

    expect(mockWebSocket.send).toHaveBeenCalledWith(
      expect.stringContaining(MessageType.HEARTBEAT)
    )
  })

  it('handles connection errors', () => {
    const { result } = renderHook(() => 
      useWebSocket({ url: 'ws://localhost:8080' })
    )

    act(() => {
      result.current.connect()
    })

    // Simulate WebSocket error
    act(() => {
      mockWebSocket.readyState = WebSocket.CLOSED
      if (mockWebSocket.onerror) {
        mockWebSocket.onerror(new Error('Connection failed'))
      }
    })

    expect(result.current.connectionStatus).toBe(ConnectionStatus.ERROR)
  })

  it('does not send message when not connected', () => {
    const { result } = renderHook(() => 
      useWebSocket({ url: 'ws://localhost:8080' })
    )

    // Don't connect, so WebSocket is null
    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation()

    act(() => {
      result.current.sendMessage({ type: 'test' })
    })

    expect(consoleSpy).toHaveBeenCalledWith(
      'WebSocket is not connected. Message not sent:',
      { type: 'test' }
    )

    consoleSpy.mockRestore()
  })
})