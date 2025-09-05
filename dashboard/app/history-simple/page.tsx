'use client'

import { useState, useEffect } from 'react'

export default function HistorySimplePage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        console.log('Fetching trade data directly...')
        
        const response = await fetch('/api/trades/history?limit=5')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        
        const result = await response.json()
        console.log('Received data:', result)
        
        setData(result)
        setError(null)
      } catch (err) {
        console.error('Error:', err)
        setError('Error: ' + (err as Error).message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Simple History Test</h1>
        
        {loading && (
          <div className="text-yellow-400">🔄 Loading trade data...</div>
        )}
        
        {error && (
          <div className="bg-red-500/20 border border-red-500 rounded p-4 mb-6">
            <h3 className="font-bold">Error:</h3>
            <p>{error}</p>
          </div>
        )}
        
        {data && (
          <div className="bg-green-500/20 border border-green-500 rounded p-6">
            <h2 className="text-xl font-bold mb-4 text-green-400">
              ✅ Success! Real Trading Data Retrieved
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-gray-800 p-4 rounded">
                <div className="text-sm text-gray-400">Total Trades</div>
                <div className="text-2xl font-bold">{data.stats?.totalTrades || 0}</div>
              </div>
              <div className="bg-gray-800 p-4 rounded">
                <div className="text-sm text-gray-400">Win Rate</div>
                <div className="text-2xl font-bold text-green-400">
                  {data.stats?.winRate?.toFixed(1) || 0}%
                </div>
              </div>
              <div className="bg-gray-800 p-4 rounded">
                <div className="text-sm text-gray-400">Total P&L</div>
                <div className={`text-2xl font-bold ${
                  (data.stats?.totalPnL || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  ${data.stats?.totalPnL?.toFixed(2) || '0.00'}
                </div>
              </div>
            </div>
            
            <div className="mb-4">
              <h3 className="text-lg font-semibold mb-3">Recent Trades:</h3>
              {data.trades?.map((trade: any, index: number) => (
                <div key={trade.id || index} className="bg-gray-800 p-3 rounded mb-2 flex justify-between items-center">
                  <div>
                    <span className="font-bold">{trade.symbol}</span>
                    <span className={`ml-2 px-2 py-1 rounded text-xs ${
                      trade.direction === 'buy' ? 'bg-green-600' : 'bg-red-600'
                    }`}>
                      {trade.direction?.toUpperCase()}
                    </span>
                    <span className="ml-2 text-sm text-gray-400">
                      {trade.status} • {trade.agentName}
                    </span>
                  </div>
                  <div className={`font-bold ${
                    (trade.profit || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    ${trade.profit?.toFixed(2) || '0.00'}
                  </div>
                </div>
              ))}
            </div>
            
            <div className="text-sm text-blue-400 mt-4">
              📡 Connected to live trading system (orchestrator:8089)
            </div>
          </div>
        )}
      </div>
    </div>
  )
}