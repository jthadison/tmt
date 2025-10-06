/**
 * Intelligence-related types for AI agent disagreement visualization
 * and confidence metrics (Story 7.1)
 */

/**
 * Enhanced trading signal with reasoning and agent context
 */
export interface EnhancedTradingSignal {
  symbol: string;
  action: 'BUY' | 'SELL' | 'NEUTRAL';
  confidence: number; // 0-100
  timestamp: number;
  reasoning?: string[]; // Optional for backward compatibility
  agentId?: string;
  sessionContext?: string;
}

/**
 * Disagreement data showing agent consensus and positions
 */
export interface DisagreementData {
  symbol: string;
  timestamp: number;
  consensusPercentage: number; // 0-100
  finalDecision: 'BUY' | 'SELL' | 'NEUTRAL';
  thresholdMet: boolean;
  requiredThreshold: number;
  agentPositions: AgentPosition[];
}

/**
 * Individual agent position in disagreement analysis
 */
export interface AgentPosition {
  agentId: string;
  agentName: string;
  action: 'BUY' | 'SELL' | 'NEUTRAL';
  confidence: number;
  reasoning: string[];
  timestamp: number;
}

/**
 * Confidence level categories (5 tiers)
 */
export type ConfidenceLevel = 'very-low' | 'low' | 'medium' | 'high' | 'very-high';

/**
 * Configuration for confidence level display
 */
export interface ConfidenceLevelConfig {
  color: string;
  label: string;
  bgColor: string;
}

/**
 * Agent metadata for display
 */
export interface AgentMetadata {
  id: string;
  name: string;
  icon: string;
  port: number;
  description: string;
}

/**
 * Map confidence value to level
 */
export function getConfidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence < 30) return 'very-low';
  if (confidence < 50) return 'low';
  if (confidence < 70) return 'medium';
  if (confidence < 90) return 'high';
  return 'very-high';
}

/**
 * Configuration map for confidence levels
 */
export const confidenceLevelConfig: Record<ConfidenceLevel, ConfidenceLevelConfig> = {
  'very-low': { color: '#ef4444', label: 'Very Low', bgColor: '#fee2e2' },
  'low': { color: '#f59e0b', label: 'Low', bgColor: '#fef3c7' },
  'medium': { color: '#eab308', label: 'Medium', bgColor: '#fef9c3' },
  'high': { color: '#84cc16', label: 'High', bgColor: '#ecfccb' },
  'very-high': { color: '#22c55e', label: 'Very High', bgColor: '#dcfce7' }
};

/**
 * 8 AI Agents metadata
 */
export const AI_AGENTS: AgentMetadata[] = [
  {
    id: 'market-analysis',
    name: 'Market Analysis',
    icon: '📊',
    port: 8001,
    description: 'Market scanning and trend analysis'
  },
  {
    id: 'strategy-analysis',
    name: 'Strategy Analysis',
    icon: '🎯',
    port: 8002,
    description: 'Performance tracking and session optimization'
  },
  {
    id: 'parameter-optimization',
    name: 'Parameter Optimization',
    icon: '⚙️',
    port: 8003,
    description: 'Risk parameter tuning'
  },
  {
    id: 'learning-safety',
    name: 'Learning Safety',
    icon: '🛡️',
    port: 8004,
    description: 'Circuit breakers and anomaly detection'
  },
  {
    id: 'disagreement-engine',
    name: 'Disagreement Engine',
    icon: '🤝',
    port: 8005,
    description: 'Decision disagreement tracking'
  },
  {
    id: 'data-collection',
    name: 'Data Collection',
    icon: '📁',
    port: 8006,
    description: 'Pipeline metrics and data management'
  },
  {
    id: 'continuous-improvement',
    name: 'Continuous Improvement',
    icon: '📈',
    port: 8007,
    description: 'Performance analysis'
  },
  {
    id: 'pattern-detection',
    name: 'Pattern Detection',
    icon: '🔍',
    port: 8008,
    description: 'Wyckoff patterns and VPA analysis'
  }
];
