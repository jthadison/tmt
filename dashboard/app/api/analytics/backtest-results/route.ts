import { NextRequest, NextResponse } from 'next/server'
import { readFileSync, readdirSync, statSync } from 'fs'
import { join } from 'path'

export interface BacktestResults {
  strategyName: string
  testPeriod: {
    startDate: string
    endDate: string
    totalDays: number
  }
  metrics: {
    winRate: number // %
    avgWin: number // $
    avgLoss: number // $
    profitFactor: number
    maxDrawdown: number // $
    maxDrawdownPercent: number // %
    sharpeRatio: number
    totalTrades: number
    totalProfit: number // $
  }
  sessionOptimization?: {
    session: string
    winRate: number
    trades: number
  }[]
  parsedAt: number
  sourceFile: string
}

function parseBacktestJSON(filePath: string, fileName: string): BacktestResults | null {
  try {
    const content = readFileSync(filePath, 'utf-8')
    const data = JSON.parse(content)

    // Extract best result from optimization or use baseline/improved
    let bestResult = data.baseline_result || data.improved_result

    if (data.optimization_results && data.optimization_results.length > 0) {
      // Find best performing optimization result
      bestResult = data.optimization_results.reduce((best: any, current: any) => {
        if (current.total_pnl > best.total_pnl) return current
        return best
      }, data.optimization_results[0])
    }

    if (!bestResult) {
      console.error(`No valid results found in ${fileName}`)
      return null
    }

    // Calculate test period days
    const startDate = new Date(bestResult.start_date)
    const endDate = new Date(bestResult.end_date)
    const totalDays = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))

    // Calculate max drawdown percentage (assuming starting capital of $10,000)
    const startingCapital = 10000
    const maxDrawdownPercent = bestResult.max_drawdown ?
      (Math.abs(bestResult.max_drawdown) / startingCapital) * 100 : 0

    return {
      strategyName: bestResult.configuration || 'Unknown Strategy',
      testPeriod: {
        startDate: bestResult.start_date,
        endDate: bestResult.end_date,
        totalDays
      },
      metrics: {
        winRate: bestResult.win_rate || 0,
        avgWin: bestResult.average_win || 0,
        avgLoss: Math.abs(bestResult.average_loss || 0),
        profitFactor: bestResult.profit_factor || 0,
        maxDrawdown: Math.abs(bestResult.max_drawdown || 0),
        maxDrawdownPercent,
        sharpeRatio: bestResult.sharpe_ratio || 0,
        totalTrades: bestResult.executed_trades || 0,
        totalProfit: bestResult.total_pnl || 0
      },
      parsedAt: Date.now(),
      sourceFile: fileName
    }
  } catch (error) {
    console.error(`Error parsing backtest file ${fileName}:`, error)
    return null
  }
}

export async function GET(request: NextRequest) {
  try {
    const backtestDir = join(process.cwd(), '..', 'backtest_results')

    // Check if directory exists
    try {
      statSync(backtestDir)
    } catch {
      return NextResponse.json(
        { error: 'Backtest results directory not found' },
        { status: 404 }
      )
    }

    // Read all JSON files from directory
    const files = readdirSync(backtestDir)
      .filter(file => file.endsWith('.json'))
      .sort((a, b) => {
        // Sort by date in filename (newest first)
        const dateA = a.match(/\d{8}_\d{6}/)?.[0] || ''
        const dateB = b.match(/\d{8}_\d{6}/)?.[0] || ''
        return dateB.localeCompare(dateA)
      })

    if (files.length === 0) {
      return NextResponse.json(
        { error: 'No backtest results found' },
        { status: 404 }
      )
    }

    // Parse latest backtest file
    const latestFile = files[0]
    const filePath = join(backtestDir, latestFile)
    const backtestResults = parseBacktestJSON(filePath, latestFile)

    if (!backtestResults) {
      return NextResponse.json(
        { error: 'Failed to parse backtest results' },
        { status: 500 }
      )
    }

    return NextResponse.json(backtestResults)
  } catch (error) {
    console.error('Error reading backtest results:', error)
    return NextResponse.json(
      { error: 'Failed to read backtest results' },
      { status: 500 }
    )
  }
}
