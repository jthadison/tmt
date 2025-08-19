/**
 * OANDA API Service
 * Handles all interactions with OANDA API including account data, real-time updates, and rate limiting
 */

import { 
  OandaAccount, 
  AccountMetrics, 
  AccountHistoryPoint, 
  AccountPerformanceSummary,
  TradingLimits,
  AggregatedAccountMetrics,
  OandaApiResponse,
  AccountUpdateMessage,
  AccountAlert,
  AccountConnectionStatus,
  TimeFrame,
  CurrencyCode,
  AccountHealthStatus
} from '@/types/oanda'

/**
 * OANDA API configuration
 */
interface OandaConfig {
  apiUrl: string
  streamUrl: string
  apiKey: string
  accountIds: string[]
  rateLimitRequests: number
  rateLimitWindow: number // milliseconds
  retryAttempts: number
  retryDelay: number
}

/**
 * Rate limiting utility
 */
class RateLimiter {
  private requests: number[] = []
  private readonly maxRequests: number
  private readonly windowMs: number

  constructor(maxRequests: number, windowMs: number) {
    this.maxRequests = maxRequests
    this.windowMs = windowMs
  }

  canMakeRequest(): boolean {
    const now = Date.now()
    // Remove requests outside the current window
    this.requests = this.requests.filter(time => now - time < this.windowMs)
    return this.requests.length < this.maxRequests
  }

  recordRequest(): void {
    this.requests.push(Date.now())
  }

  getTimeUntilReset(): number {
    if (this.requests.length === 0) return 0
    const oldestRequest = Math.min(...this.requests)
    return Math.max(0, this.windowMs - (Date.now() - oldestRequest))
  }

  getRemainingRequests(): number {
    const now = Date.now()
    this.requests = this.requests.filter(time => now - time < this.windowMs)
    return Math.max(0, this.maxRequests - this.requests.length)
  }
}

/**
 * OANDA Service for API interactions and data management
 */
export class OandaService {
  private config: OandaConfig
  private rateLimiter: RateLimiter
  private connectionStatus: Map<string, AccountConnectionStatus> = new Map()
  private updateCallbacks: ((update: AccountUpdateMessage) => void)[] = []
  private alertCallbacks: ((alert: AccountAlert) => void)[] = []
  private reconnectTimeouts: Map<string, NodeJS.Timeout> = new Map()

  constructor(config: OandaConfig) {
    this.config = config
    this.rateLimiter = new RateLimiter(config.rateLimitRequests, config.rateLimitWindow)
    
    // Initialize connection status for all accounts
    config.accountIds.forEach(accountId => {
      this.connectionStatus.set(accountId, {
        accountId,
        status: 'disconnected',
        lastConnectionAttempt: new Date(),
        retryCount: 0,
        rateLimitStatus: {
          limited: false,
          requestsRemaining: config.rateLimitRequests
        }
      })
    })
  }

  /**
   * Make authenticated API request with rate limiting
   */
  private async makeRequest<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<OandaApiResponse<T>> {
    // Check rate limit
    if (!this.rateLimiter.canMakeRequest()) {
      const resetTime = new Date(Date.now() + this.rateLimiter.getTimeUntilReset())
      return {
        data: null as T,
        timestamp: new Date(),
        rateLimit: {
          limit: this.config.rateLimitRequests,
          remaining: this.rateLimiter.getRemainingRequests(),
          reset: resetTime
        },
        status: 'rate_limited',
        error: 'Rate limit exceeded'
      }
    }

    this.rateLimiter.recordRequest()

    try {
      const response = await fetch(`${this.config.apiUrl}${endpoint}`, {
        ...options,
        headers: {
          'Authorization': `Bearer ${this.config.apiKey}`,
          'Content-Type': 'application/json',
          ...options.headers
        }
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.message || `HTTP ${response.status}`)
      }

      return {
        data,
        timestamp: new Date(),
        rateLimit: {
          limit: this.config.rateLimitRequests,
          remaining: this.rateLimiter.getRemainingRequests(),
          reset: new Date(Date.now() + this.rateLimiter.getTimeUntilReset())
        },
        status: 'success'
      }
    } catch (error) {
      return {
        data: null as T,
        timestamp: new Date(),
        rateLimit: {
          limit: this.config.rateLimitRequests,
          remaining: this.rateLimiter.getRemainingRequests(),
          reset: new Date(Date.now() + this.rateLimiter.getTimeUntilReset())
        },
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    }
  }

  /**
   * Get account information
   */
  async getAccount(accountId: string): Promise<OandaApiResponse<OandaAccount>> {
    const response = await this.makeRequest<any>(`/v3/accounts/${accountId}`)
    
    if (response.status === 'success' && response.data) {
      const oandaAccount = this.transformAccountData(response.data.account)
      return { ...response, data: oandaAccount }
    }
    
    return response as OandaApiResponse<OandaAccount>
  }

  /**
   * Get all configured accounts
   */
  async getAllAccounts(): Promise<OandaApiResponse<OandaAccount[]>> {
    const accounts: OandaAccount[] = []
    let hasErrors = false
    let lastError = ''

    for (const accountId of this.config.accountIds) {
      const response = await this.getAccount(accountId)
      if (response.status === 'success' && response.data) {
        accounts.push(response.data)
      } else {
        hasErrors = true
        lastError = response.error || 'Unknown error'
        this.updateConnectionStatus(accountId, 'error', response.error)
      }
    }

    return {
      data: accounts,
      timestamp: new Date(),
      rateLimit: {
        limit: this.config.rateLimitRequests,
        remaining: this.rateLimiter.getRemainingRequests(),
        reset: new Date(Date.now() + this.rateLimiter.getTimeUntilReset())
      },
      status: hasErrors ? (accounts.length > 0 ? 'success' : 'error') : 'success',
      error: hasErrors ? lastError : undefined
    }
  }

  /**
   * Get real-time account metrics
   */
  async getAccountMetrics(accountId: string): Promise<OandaApiResponse<AccountMetrics>> {
    const response = await this.makeRequest<any>(`/v3/accounts/${accountId}/summary`)
    
    if (response.status === 'success' && response.data) {
      const metrics = this.transformAccountMetrics(accountId, response.data.account)
      return { ...response, data: metrics }
    }
    
    return response as OandaApiResponse<AccountMetrics>
  }

  /**
   * Get account history for charts
   */
  async getAccountHistory(
    accountId: string, 
    timeFrame: TimeFrame, 
    startDate: Date, 
    endDate: Date
  ): Promise<OandaApiResponse<AccountHistoryPoint[]>> {
    // In a real implementation, this would fetch historical account data
    // For now, we'll generate mock historical data
    const mockHistory = this.generateMockHistory(accountId, timeFrame, startDate, endDate)
    
    return {
      data: mockHistory,
      timestamp: new Date(),
      rateLimit: {
        limit: this.config.rateLimitRequests,
        remaining: this.rateLimiter.getRemainingRequests(),
        reset: new Date(Date.now() + this.rateLimiter.getTimeUntilReset())
      },
      status: 'success'
    }
  }

  /**
   * Get account performance summary
   */
  async getPerformanceSummary(
    accountId: string, 
    startDate: Date, 
    endDate: Date
  ): Promise<OandaApiResponse<AccountPerformanceSummary>> {
    const historyResponse = await this.getAccountHistory(accountId, '1D', startDate, endDate)
    
    if (historyResponse.status === 'success' && historyResponse.data) {
      const summary = this.calculatePerformanceSummary(accountId, historyResponse.data, startDate, endDate)
      return { ...historyResponse, data: summary }
    }
    
    return historyResponse as OandaApiResponse<AccountPerformanceSummary>
  }

  /**
   * Get trading limits for account
   */
  async getTradingLimits(accountId: string): Promise<OandaApiResponse<TradingLimits>> {
    // This would typically fetch from your risk management system
    const mockLimits = this.generateMockTradingLimits(accountId)
    
    return {
      data: mockLimits,
      timestamp: new Date(),
      rateLimit: {
        limit: this.config.rateLimitRequests,
        remaining: this.rateLimiter.getRemainingRequests(),
        reset: new Date(Date.now() + this.rateLimiter.getTimeUntilReset())
      },
      status: 'success'
    }
  }

  /**
   * Get aggregated metrics for all accounts
   */
  async getAggregatedMetrics(): Promise<OandaApiResponse<AggregatedAccountMetrics>> {
    const accountsResponse = await this.getAllAccounts()
    
    if (accountsResponse.status === 'success' && accountsResponse.data) {
      const aggregated = this.calculateAggregatedMetrics(accountsResponse.data)
      return { ...accountsResponse, data: aggregated }
    }
    
    return accountsResponse as OandaApiResponse<AggregatedAccountMetrics>
  }

  /**
   * Subscribe to real-time account updates
   */
  subscribeToUpdates(callback: (update: AccountUpdateMessage) => void): void {
    this.updateCallbacks.push(callback)
    
    // Start real-time updates for all accounts
    this.config.accountIds.forEach(accountId => {
      this.startRealTimeUpdates(accountId)
    })
  }

  /**
   * Subscribe to account alerts
   */
  subscribeToAlerts(callback: (alert: AccountAlert) => void): void {
    this.alertCallbacks.push(callback)
  }

  /**
   * Get connection status for all accounts
   */
  getConnectionStatus(): AccountConnectionStatus[] {
    return Array.from(this.connectionStatus.values())
  }

  /**
   * Reconnect to specific account
   */
  async reconnectAccount(accountId: string): Promise<void> {
    const status = this.connectionStatus.get(accountId)
    if (status) {
      status.status = 'connecting'
      status.lastConnectionAttempt = new Date()
      this.connectionStatus.set(accountId, status)
      
      await this.startRealTimeUpdates(accountId)
    }
  }

  /**
   * Transform OANDA API account data to our format
   */
  private transformAccountData(oandaData: any): OandaAccount {
    const healthStatus = this.calculateHealthStatus(oandaData)
    
    return {
      id: oandaData.id,
      alias: oandaData.alias || `Account ${oandaData.id}`,
      type: oandaData.mt4AccountID ? 'mt4' : 'live',
      currency: oandaData.currency as CurrencyCode,
      balance: parseFloat(oandaData.balance),
      NAV: parseFloat(oandaData.NAV),
      unrealizedPL: parseFloat(oandaData.unrealizedPL || '0'),
      realizedPL: parseFloat(oandaData.pl || '0'),
      marginUsed: parseFloat(oandaData.marginUsed || '0'),
      marginAvailable: parseFloat(oandaData.marginAvailable || '0'),
      marginRate: parseFloat(oandaData.marginRate || '0.02'),
      openTradeCount: parseInt(oandaData.openTradeCount || '0'),
      openPositionCount: parseInt(oandaData.openPositionCount || '0'),
      pendingOrderCount: parseInt(oandaData.pendingOrderCount || '0'),
      createdTime: oandaData.createdTime,
      lastTransactionID: oandaData.lastTransactionID,
      commission: oandaData.commission || {
        homeConversionFactor: 1,
        unitsAvailable: {
          default: {
            long: '1000000',
            short: '1000000'
          }
        }
      },
      financing: oandaData.financing || {
        dividendAdjustment: 0
      },
      healthStatus,
      lastUpdate: new Date()
    }
  }

  /**
   * Transform account data to metrics format
   */
  private transformAccountMetrics(accountId: string, oandaData: any): AccountMetrics {
    const balance = parseFloat(oandaData.balance)
    const marginUsed = parseFloat(oandaData.marginUsed || '0')
    const marginAvailable = parseFloat(oandaData.marginAvailable || '0')
    const totalMargin = marginUsed + marginAvailable
    
    return {
      accountId,
      timestamp: new Date(),
      balance,
      equity: parseFloat(oandaData.NAV),
      marginUsed,
      marginAvailable,
      marginUtilization: totalMargin > 0 ? (marginUsed / totalMargin) * 100 : 0,
      freeMargin: marginAvailable,
      marginLevel: marginUsed > 0 ? (parseFloat(oandaData.NAV) / marginUsed) * 100 : 999999,
      dailyPL: parseFloat(oandaData.unrealizedPL || '0'), // Simplified
      unrealizedPL: parseFloat(oandaData.unrealizedPL || '0'),
      openPositions: parseInt(oandaData.openPositionCount || '0'),
      totalExposure: marginUsed * 50, // Simplified calculation
      riskScore: this.calculateRiskScore(oandaData)
    }
  }

  /**
   * Calculate account health status
   */
  private calculateHealthStatus(oandaData: any): AccountHealthStatus {
    const nav = parseFloat(oandaData.NAV)
    const marginUsed = parseFloat(oandaData.marginUsed || '0')
    const marginLevel = marginUsed > 0 ? (nav / marginUsed) * 100 : 999999
    
    if (marginLevel < 120) return 'margin_call'
    if (marginLevel < 200) return 'danger'
    if (marginLevel < 300) return 'warning'
    return 'healthy'
  }

  /**
   * Calculate risk score (0-100)
   */
  private calculateRiskScore(oandaData: any): number {
    const nav = parseFloat(oandaData.NAV)
    const marginUsed = parseFloat(oandaData.marginUsed || '0')
    const marginLevel = marginUsed > 0 ? (nav / marginUsed) * 100 : 999999
    const openPositions = parseInt(oandaData.openPositionCount || '0')
    
    let score = 0
    
    // Margin level component (0-40 points)
    if (marginLevel < 150) score += 40
    else if (marginLevel < 200) score += 30
    else if (marginLevel < 300) score += 20
    else if (marginLevel < 500) score += 10
    
    // Position count component (0-30 points)
    if (openPositions > 10) score += 30
    else if (openPositions > 5) score += 20
    else if (openPositions > 2) score += 10
    
    // Unrealized P&L component (0-30 points)
    const unrealizedPL = parseFloat(oandaData.unrealizedPL || '0')
    const balance = parseFloat(oandaData.balance)
    const plPercent = balance > 0 ? (unrealizedPL / balance) * 100 : 0
    
    if (plPercent < -10) score += 30
    else if (plPercent < -5) score += 20
    else if (plPercent < -2) score += 10
    
    return Math.min(100, score)
  }

  /**
   * Generate mock historical data
   */
  private generateMockHistory(
    accountId: string, 
    timeFrame: TimeFrame, 
    startDate: Date, 
    endDate: Date
  ): AccountHistoryPoint[] {
    const points: AccountHistoryPoint[] = []
    const startBalance = 10000 + Math.random() * 40000 // Random starting balance
    let currentBalance = startBalance
    let peakBalance = startBalance
    
    const timeInterval = this.getTimeInterval(timeFrame)
    const current = new Date(startDate)
    
    while (current <= endDate) {
      // Generate realistic price movements
      const change = (Math.random() - 0.5) * 200 // Random change
      currentBalance = Math.max(0, currentBalance + change)
      peakBalance = Math.max(peakBalance, currentBalance)
      
      const drawdown = peakBalance - currentBalance
      const drawdownPercent = peakBalance > 0 ? (drawdown / peakBalance) * 100 : 0
      
      points.push({
        timestamp: new Date(current),
        balance: currentBalance,
        equity: currentBalance + (Math.random() - 0.5) * 100, // Add some noise for equity
        unrealizedPL: (Math.random() - 0.5) * 500,
        realizedPL: currentBalance - startBalance,
        marginUsed: Math.random() * currentBalance * 0.1,
        drawdown,
        drawdownPercent
      })
      
      current.setTime(current.getTime() + timeInterval)
    }
    
    return points
  }

  /**
   * Get time interval in milliseconds for timeframe
   */
  private getTimeInterval(timeFrame: TimeFrame): number {
    switch (timeFrame) {
      case '1H': return 60 * 60 * 1000
      case '4H': return 4 * 60 * 60 * 1000
      case '1D': return 24 * 60 * 60 * 1000
      case '1W': return 7 * 24 * 60 * 60 * 1000
      case '1M': return 30 * 24 * 60 * 60 * 1000
      default: return 24 * 60 * 60 * 1000
    }
  }

  /**
   * Calculate performance summary from history
   */
  private calculatePerformanceSummary(
    accountId: string,
    history: AccountHistoryPoint[],
    startDate: Date,
    endDate: Date
  ): AccountPerformanceSummary {
    if (history.length === 0) {
      throw new Error('No history data available')
    }
    
    const startingBalance = history[0].balance
    const endingBalance = history[history.length - 1].balance
    const totalReturn = endingBalance - startingBalance
    const totalReturnPercent = startingBalance > 0 ? (totalReturn / startingBalance) * 100 : 0
    
    const peakBalance = Math.max(...history.map(h => h.balance))
    const maxDrawdown = Math.max(...history.map(h => h.drawdown))
    const maxDrawdownPercent = Math.max(...history.map(h => h.drawdownPercent))
    
    const currentDrawdown = peakBalance - endingBalance
    const currentDrawdownPercent = peakBalance > 0 ? (currentDrawdown / peakBalance) * 100 : 0
    
    // Mock trading statistics (would be calculated from actual trade data)
    const totalTrades = Math.floor(history.length / 10) + Math.floor(Math.random() * 50)
    const winningTrades = Math.floor(totalTrades * (0.4 + Math.random() * 0.4))
    const losingTrades = totalTrades - winningTrades
    const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0
    
    const averageWin = totalReturn > 0 && winningTrades > 0 ? (totalReturn * 1.5) / winningTrades : 100
    const averageLoss = totalReturn < 0 && losingTrades > 0 ? Math.abs(totalReturn * 0.8) / losingTrades : 50
    
    const profitFactor = averageLoss > 0 ? averageWin / averageLoss : 1
    
    // Simplified Sharpe ratio calculation
    const returns = history.slice(1).map((h, i) => 
      history[i].balance > 0 ? (h.balance - history[i].balance) / history[i].balance : 0
    )
    const avgReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length
    const returnStdDev = Math.sqrt(
      returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length
    )
    const sharpeRatio = returnStdDev > 0 ? avgReturn / returnStdDev : 0
    
    // Simplified Sortino ratio (using downside deviation)
    const downsideReturns = returns.filter(r => r < 0)
    const downsideStdDev = downsideReturns.length > 0 ? Math.sqrt(
      downsideReturns.reduce((sum, r) => sum + Math.pow(r, 2), 0) / downsideReturns.length
    ) : 0
    const sortinoRatio = downsideStdDev > 0 ? avgReturn / downsideStdDev : 0
    
    return {
      accountId,
      startDate,
      endDate,
      startingBalance,
      endingBalance,
      totalReturn,
      totalReturnPercent,
      peakBalance,
      maxDrawdown,
      maxDrawdownPercent,
      currentDrawdown,
      currentDrawdownPercent,
      winRate,
      totalTrades,
      winningTrades,
      losingTrades,
      averageWin,
      averageLoss,
      profitFactor,
      sharpeRatio,
      sortinoRatio
    }
  }

  /**
   * Generate mock trading limits
   */
  private generateMockTradingLimits(accountId: string): TradingLimits {
    return {
      accountId,
      maxDailyLoss: 1000,
      maxTotalLoss: 5000,
      maxPositionSize: 100000,
      maxOpenPositions: 10,
      maxMarginUtilization: 80,
      currentDailyLoss: Math.random() * 500,
      currentTotalLoss: Math.random() * 2000,
      currentPositions: Math.floor(Math.random() * 5),
      currentMarginUtilization: Math.random() * 60,
      riskScoreThreshold: 75,
      currentRiskScore: Math.random() * 50,
      limitsEnabled: true,
      lastUpdated: new Date()
    }
  }

  /**
   * Calculate aggregated metrics
   */
  private calculateAggregatedMetrics(accounts: OandaAccount[]): AggregatedAccountMetrics {
    const totalBalance = accounts.reduce((sum, acc) => sum + acc.balance, 0)
    const totalEquity = accounts.reduce((sum, acc) => sum + acc.NAV, 0)
    const totalUnrealizedPL = accounts.reduce((sum, acc) => sum + acc.unrealizedPL, 0)
    const totalMarginUsed = accounts.reduce((sum, acc) => sum + acc.marginUsed, 0)
    const totalMarginAvailable = accounts.reduce((sum, acc) => sum + acc.marginAvailable, 0)
    
    const healthStatusBreakdown = {
      healthy: accounts.filter(acc => acc.healthStatus === 'healthy').length,
      warning: accounts.filter(acc => acc.healthStatus === 'warning').length,
      danger: accounts.filter(acc => acc.healthStatus === 'danger').length,
      marginCall: accounts.filter(acc => acc.healthStatus === 'margin_call').length
    }
    
    // Calculate currency breakdown
    const currencyBreakdown: AggregatedAccountMetrics['currencyBreakdown'] = {}
    accounts.forEach(account => {
      if (!currencyBreakdown[account.currency]) {
        currencyBreakdown[account.currency] = {
          accountCount: 0,
          totalBalance: 0,
          totalEquity: 0
        }
      }
      currencyBreakdown[account.currency]!.accountCount++
      currencyBreakdown[account.currency]!.totalBalance += account.balance
      currencyBreakdown[account.currency]!.totalEquity += account.NAV
    })
    
    return {
      totalAccounts: accounts.length,
      activeAccounts: accounts.filter(acc => acc.healthStatus !== 'margin_call').length,
      totalBalance,
      totalEquity,
      totalUnrealizedPL,
      totalMarginUsed,
      totalMarginAvailable,
      averageMarginUtilization: accounts.length > 0 ? 
        accounts.reduce((sum, acc) => {
          const total = acc.marginUsed + acc.marginAvailable
          return sum + (total > 0 ? (acc.marginUsed / total) * 100 : 0)
        }, 0) / accounts.length : 0,
      totalDailyPL: totalUnrealizedPL, // Simplified
      totalOpenPositions: accounts.reduce((sum, acc) => sum + acc.openPositionCount, 0),
      healthStatusBreakdown,
      portfolioRiskScore: accounts.length > 0 ? 
        accounts.reduce((sum, acc) => {
          // Calculate risk score based on health status
          const riskScore = acc.healthStatus === 'margin_call' ? 100 :
                           acc.healthStatus === 'danger' ? 75 :
                           acc.healthStatus === 'warning' ? 50 : 25
          return sum + riskScore
        }, 0) / accounts.length : 0,
      currencyBreakdown,
      lastUpdate: new Date()
    }
  }

  /**
   * Start real-time updates for an account
   */
  private async startRealTimeUpdates(accountId: string): Promise<void> {
    try {
      this.updateConnectionStatus(accountId, 'connecting')
      
      // Simulate connection delay
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
      
      this.updateConnectionStatus(accountId, 'connected')
      
      // Start periodic updates (in real implementation, this would be WebSocket)
      const updateInterval = setInterval(async () => {
        try {
          const metricsResponse = await this.getAccountMetrics(accountId)
          if (metricsResponse.status === 'success' && metricsResponse.data) {
            const updateMessage: AccountUpdateMessage = {
              type: 'account_update',
              accountId,
              metrics: metricsResponse.data,
              timestamp: new Date()
            }
            
            // Notify all subscribers
            this.updateCallbacks.forEach(callback => callback(updateMessage))
            
            // Check for alerts
            this.checkAndTriggerAlerts(accountId, metricsResponse.data)
          }
        } catch (error) {
          console.error(`Error updating account ${accountId}:`, error)
          this.updateConnectionStatus(accountId, 'error', error instanceof Error ? error.message : 'Unknown error')
        }
      }, 5000) // Update every 5 seconds
      
      // Store interval for cleanup
      this.reconnectTimeouts.set(accountId, updateInterval)
      
    } catch (error) {
      this.updateConnectionStatus(accountId, 'error', error instanceof Error ? error.message : 'Unknown error')
      
      // Schedule reconnection
      setTimeout(() => {
        const status = this.connectionStatus.get(accountId)
        if (status && status.retryCount < this.config.retryAttempts) {
          status.retryCount++
          this.startRealTimeUpdates(accountId)
        }
      }, this.config.retryDelay * (Math.pow(2, this.connectionStatus.get(accountId)?.retryCount || 0)))
    }
  }

  /**
   * Update connection status
   */
  private updateConnectionStatus(
    accountId: string, 
    status: AccountConnectionStatus['status'], 
    error?: string
  ): void {
    const currentStatus = this.connectionStatus.get(accountId)
    if (currentStatus) {
      currentStatus.status = status
      currentStatus.lastConnectionAttempt = new Date()
      if (status === 'connected') {
        currentStatus.lastSuccessfulConnection = new Date()
        currentStatus.retryCount = 0
        currentStatus.connectionError = undefined
      } else if (status === 'error') {
        currentStatus.connectionError = error
      }
      currentStatus.rateLimitStatus.requestsRemaining = this.rateLimiter.getRemainingRequests()
      
      this.connectionStatus.set(accountId, currentStatus)
    }
  }

  /**
   * Check and trigger alerts based on account metrics
   */
  private checkAndTriggerAlerts(accountId: string, metrics: AccountMetrics): void {
    const alerts: AccountAlert[] = []
    
    // Margin warning alert
    if (metrics.marginLevel < 300 && metrics.marginLevel >= 200) {
      alerts.push({
        id: `${accountId}-margin-warning`,
        accountId,
        type: 'margin_warning',
        threshold: 300,
        currentValue: metrics.marginLevel,
        enabled: true,
        triggered: true,
        lastTriggered: new Date(),
        message: `Margin level is ${metrics.marginLevel.toFixed(1)}% - approaching dangerous levels`,
        severity: 'warning',
        createdAt: new Date(),
        updatedAt: new Date()
      })
    }
    
    // Drawdown warning
    if (metrics.unrealizedPL < -1000) {
      alerts.push({
        id: `${accountId}-drawdown-warning`,
        accountId,
        type: 'drawdown_warning',
        threshold: -1000,
        currentValue: metrics.unrealizedPL,
        enabled: true,
        triggered: true,
        lastTriggered: new Date(),
        message: `Large unrealized loss: $${metrics.unrealizedPL.toFixed(2)}`,
        severity: 'critical',
        createdAt: new Date(),
        updatedAt: new Date()
      })
    }
    
    // Risk score alert
    if (metrics.riskScore > 75) {
      alerts.push({
        id: `${accountId}-risk-score`,
        accountId,
        type: 'risk_score',
        threshold: 75,
        currentValue: metrics.riskScore,
        enabled: true,
        triggered: true,
        lastTriggered: new Date(),
        message: `High risk score: ${metrics.riskScore.toFixed(1)}`,
        severity: 'warning',
        createdAt: new Date(),
        updatedAt: new Date()
      })
    }
    
    // Trigger alert callbacks
    alerts.forEach(alert => {
      this.alertCallbacks.forEach(callback => callback(alert))
    })
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.reconnectTimeouts.forEach(timeout => clearInterval(timeout))
    this.reconnectTimeouts.clear()
    this.updateCallbacks.length = 0
    this.alertCallbacks.length = 0
  }
}