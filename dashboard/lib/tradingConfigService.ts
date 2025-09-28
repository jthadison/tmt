/**
 * Trading Configuration Service
 * Handles synchronization of trading settings with backend services
 */

interface TradingConfigUpdate {
  tradingEnabled: boolean;
  sessionTargetingEnabled: boolean;
}

interface ServiceResponse {
  success: boolean;
  message?: string;
  data?: any;
}

class TradingConfigService {
  private readonly orchestratorUrl = 'http://localhost:8089';
  private readonly marketAnalysisUrl = 'http://localhost:8001';

  /**
   * Update trading enabled status in orchestrator
   */
  async updateTradingEnabled(enabled: boolean): Promise<ServiceResponse> {
    try {
      const response = await fetch(`${this.orchestratorUrl}/api/trading/enable`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ enabled }),
      });

      if (!response.ok) {
        throw new Error(`Failed to update trading status: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        message: `Trading ${enabled ? 'enabled' : 'disabled'} successfully`,
        data,
      };
    } catch (error) {
      console.error('Error updating trading enabled status:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      };
    }
  }

  /**
   * Update session targeting in market analysis agent
   */
  async updateSessionTargeting(enabled: boolean): Promise<ServiceResponse> {
    try {
      const response = await fetch(`${this.marketAnalysisUrl}/api/config/session-targeting`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ enabled }),
      });

      if (!response.ok) {
        throw new Error(`Failed to update session targeting: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        message: `Session targeting ${enabled ? 'enabled' : 'disabled'} successfully`,
        data,
      };
    } catch (error) {
      console.error('Error updating session targeting:', error);
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error occurred',
      };
    }
  }

  /**
   * Get current trading configuration
   */
  async getCurrentConfig(): Promise<TradingConfigUpdate | null> {
    try {
      // Get orchestrator status for trading enabled
      const orchestratorResponse = await fetch(`${this.orchestratorUrl}/health`);

      if (!orchestratorResponse.ok) {
        throw new Error(`Orchestrator health check failed: ${orchestratorResponse.statusText}`);
      }

      const orchestratorData = await orchestratorResponse.json();

      // Get market analysis config for session targeting
      const marketAnalysisResponse = await fetch(`${this.marketAnalysisUrl}/api/config/current`);

      if (!marketAnalysisResponse.ok) {
        throw new Error(`Market analysis config fetch failed: ${marketAnalysisResponse.statusText}`);
      }

      const marketAnalysisData = await marketAnalysisResponse.json();

      return {
        tradingEnabled: orchestratorData.trading_enabled || false,
        sessionTargetingEnabled: marketAnalysisData.session_targeting_enabled || false,
      };
    } catch (error) {
      console.error('Error fetching current config:', error);
      return null;
    }
  }

  /**
   * Update both trading and session targeting settings
   */
  async updateTradingConfig(config: TradingConfigUpdate): Promise<ServiceResponse[]> {
    const results: ServiceResponse[] = [];

    // Update trading enabled first
    const tradingResult = await this.updateTradingEnabled(config.tradingEnabled);
    results.push(tradingResult);

    // Only update session targeting if trading is enabled
    if (config.tradingEnabled) {
      const sessionResult = await this.updateSessionTargeting(config.sessionTargetingEnabled);
      results.push(sessionResult);
    } else {
      // If trading is disabled, force session targeting off
      const sessionResult = await this.updateSessionTargeting(false);
      results.push(sessionResult);
    }

    return results;
  }

  /**
   * Health check for all trading services
   */
  async checkServicesHealth(): Promise<{
    orchestrator: boolean;
    marketAnalysis: boolean;
    overall: boolean;
  }> {
    try {
      const [orchestratorResponse, marketAnalysisResponse] = await Promise.allSettled([
        fetch(`${this.orchestratorUrl}/health`),
        fetch(`${this.marketAnalysisUrl}/health`),
      ]);

      const orchestratorHealth = orchestratorResponse.status === 'fulfilled' &&
                                orchestratorResponse.value.ok;
      const marketAnalysisHealth = marketAnalysisResponse.status === 'fulfilled' &&
                                  marketAnalysisResponse.value.ok;

      return {
        orchestrator: orchestratorHealth,
        marketAnalysis: marketAnalysisHealth,
        overall: orchestratorHealth && marketAnalysisHealth,
      };
    } catch (error) {
      console.error('Error checking services health:', error);
      return {
        orchestrator: false,
        marketAnalysis: false,
        overall: false,
      };
    }
  }
}

// Export singleton instance
export const tradingConfigService = new TradingConfigService();
export type { TradingConfigUpdate, ServiceResponse };