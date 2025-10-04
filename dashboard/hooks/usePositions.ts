/**
 * Custom hook for managing trading positions
 * Fetches, enriches, and manages real-time position data
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { Position, PositionUpdateMessage, UsePositionsState } from '@/types/positions'
import { enrichPosition } from '@/utils/positionCalculations'
import { useWebSocket } from './useWebSocket'

const EXECUTION_ENGINE_URL = process.env.NEXT_PUBLIC_EXECUTION_ENGINE_URL || 'http://localhost:8082'
const ORCHESTRATOR_WS_URL = process.env.NEXT_PUBLIC_ORCHESTRATOR_WS_URL || 'ws://localhost:8089'

/**
 * Hook for managing positions with real-time updates
 */
export function usePositions(): UsePositionsState {
  const [positions, setPositions] = useState<Position[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Track last update time per position to throttle updates
  const lastUpdateTimeRef = useRef<Map<string, number>>(new Map())
  const UPDATE_THROTTLE_MS = 1000 // 1 second throttle

  // WebSocket connection for real-time updates
  const { lastMessage, isConnected } = useWebSocket({
    url: ORCHESTRATOR_WS_URL,
    reconnectAttempts: 5,
    reconnectInterval: 3000
  })

  /**
   * Fetch all open positions from execution engine
   */
  const fetchPositions = useCallback(async () => {
    try {
      setError(null)

      const response = await fetch(`${EXECUTION_ENGINE_URL}/api/positions`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch positions: ${response.statusText}`)
      }

      const data = await response.json()

      // Enrich positions with calculated fields
      const enrichedPositions: Position[] = (data.positions || []).map((rawPos: any) => {
        const accountId = rawPos.account_id || rawPos.accountId || ''

        return enrichPosition(
          {
            id: rawPos.id,
            instrument: rawPos.instrument,
            units: String(rawPos.units),
            price: String(rawPos.entry_price || rawPos.entryPrice),
            unrealizedPL: String(rawPos.unrealized_pl || rawPos.unrealizedPL || 0),
            openTime: rawPos.open_time || rawPos.openTime,
            stopLoss: rawPos.stop_loss || rawPos.stopLoss,
            takeProfit: rawPos.take_profit || rawPos.takeProfit,
            clientExtensions: {
              agent: rawPos.agent_source || rawPos.agentSource
            }
          },
          rawPos.current_price || rawPos.currentPrice
        )
      }).map((pos: Position) => ({
        ...pos,
        accountId: data.positions.find((rp: any) => rp.id === pos.id)?.account_id ||
                  data.positions.find((rp: any) => rp.id === pos.id)?.accountId ||
                  ''
      }))

      setPositions(enrichedPositions)
      setIsLoading(false)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load positions'
      setError(errorMessage)
      setIsLoading(false)
      console.error('Error fetching positions:', err)
    }
  }, [])

  /**
   * Handle real-time position updates from WebSocket
   */
  useEffect(() => {
    if (!lastMessage) return

    try {
      const message = typeof lastMessage === 'string'
        ? JSON.parse(lastMessage)
        : lastMessage

      if (message.type === 'positions.update') {
        const update = message as PositionUpdateMessage
        const { position_id, current_price, unrealized_pl, timestamp } = update.data

        // Throttle updates to prevent excessive re-renders
        const now = Date.now()
        const lastUpdate = lastUpdateTimeRef.current.get(position_id) || 0

        if (now - lastUpdate < UPDATE_THROTTLE_MS) {
          return // Skip this update
        }

        lastUpdateTimeRef.current.set(position_id, now)

        // Update only the changed position
        setPositions(prevPositions => {
          return prevPositions.map(pos => {
            if (pos.id !== position_id) return pos

            // Recalculate enriched fields with new price
            const entryPrice = pos.entryPrice
            const units = pos.direction === 'long' ? pos.units : -pos.units

            return enrichPosition(
              {
                id: pos.id,
                instrument: pos.instrument,
                units: String(units),
                price: String(entryPrice),
                unrealizedPL: String(unrealized_pl),
                openTime: pos.openTime,
                stopLoss: pos.stopLoss ? String(pos.stopLoss) : undefined,
                takeProfit: pos.takeProfit ? String(pos.takeProfit) : undefined,
                clientExtensions: {
                  agent: pos.agentSource
                }
              },
              current_price
            )
          }).map(pos => ({
            ...pos,
            accountId: positions.find(p => p.id === pos.id)?.accountId || ''
          }))
        })
      }
    } catch (err) {
      console.error('Error handling WebSocket position update:', err)
    }
  }, [lastMessage])

  /**
   * Close a position
   */
  const closePosition = useCallback(async (positionId: string) => {
    try {
      const response = await fetch(
        `${EXECUTION_ENGINE_URL}/api/positions/${positionId}/close`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to close position: ${response.statusText}`)
      }

      const result = await response.json()

      // Remove position from state
      setPositions(prevPositions =>
        prevPositions.filter(pos => pos.id !== positionId)
      )

      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to close position'
      throw new Error(errorMessage)
    }
  }, [])

  /**
   * Modify a position (update SL/TP)
   */
  const modifyPosition = useCallback(async (
    positionId: string,
    stopLoss?: number,
    takeProfit?: number
  ) => {
    try {
      const response = await fetch(
        `${EXECUTION_ENGINE_URL}/api/positions/${positionId}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            stop_loss: stopLoss,
            take_profit: takeProfit
          })
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to modify position: ${response.statusText}`)
      }

      const result = await response.json()

      // Update position in state
      setPositions(prevPositions =>
        prevPositions.map(pos => {
          if (pos.id !== positionId) return pos

          // Re-enrich position with new SL/TP
          const units = pos.direction === 'long' ? pos.units : -pos.units

          return enrichPosition(
            {
              id: pos.id,
              instrument: pos.instrument,
              units: String(units),
              price: String(pos.entryPrice),
              unrealizedPL: String(pos.unrealizedPL),
              openTime: pos.openTime,
              stopLoss: stopLoss ? String(stopLoss) : undefined,
              takeProfit: takeProfit ? String(takeProfit) : undefined,
              clientExtensions: {
                agent: pos.agentSource
              }
            },
            pos.currentPrice
          )
        }).map(pos => ({
          ...pos,
          accountId: positions.find(p => p.id === pos.id)?.accountId || ''
        }))
      )

      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to modify position'
      throw new Error(errorMessage)
    }
  }, [positions])

  /**
   * Refresh positions manually
   */
  const refreshPositions = useCallback(async () => {
    await fetchPositions()
  }, [fetchPositions])

  // Initial fetch on mount
  useEffect(() => {
    fetchPositions()
  }, [fetchPositions])

  // Polling fallback if WebSocket is disconnected
  useEffect(() => {
    if (!isConnected) {
      const pollInterval = setInterval(fetchPositions, 5000) // Poll every 5 seconds
      return () => clearInterval(pollInterval)
    }
  }, [isConnected, fetchPositions])

  return {
    positions,
    isLoading,
    error,
    closePosition,
    modifyPosition,
    refreshPositions
  }
}
