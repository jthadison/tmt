// Type definitions for broker integration dashboard

export enum ConnectionStatus {
  CONNECTED = "connected",
  DISCONNECTED = "disconnected",
  RECONNECTING = "reconnecting",
  ERROR = "error"
}

export interface BrokerAccount {
  id: string;
  broker_name: string;
  account_type: "live" | "demo";
  display_name: string;
  balance: number;
  equity: number;
  unrealized_pl: number;
  realized_pl: number;
  margin_used: number;
  margin_available: number;
  connection_status: ConnectionStatus;
  last_update: string;
  capabilities: string[];
  metrics: Record<string, any>;
  currency: string;
  logo_url?: string;
}

export interface AggregateData {
  total_balance: number;
  total_equity: number;
  total_unrealized_pl: number;
  total_realized_pl: number;
  total_margin_used: number;
  total_margin_available: number;
  account_count: number;
  connected_count: number;
  best_performer?: string;
  worst_performer?: string;
  daily_pl: number;
  weekly_pl: number;
  monthly_pl: number;
  last_update: string;
}

export interface BrokerPerformanceMetrics {
  avg_latency_ms: number;
  fill_quality_score: number;
  uptime_percentage: number;
  total_trades: number;
  successful_trades: number;
  failed_trades: number;
  avg_slippage_pips: number;
  connection_stability: number;
}

export interface BrokerCapability {
  name: string;
  description: string;
  enabled: boolean;
}

export interface WebSocketMessage {
  type: "BROKER_UPDATE" | "AGGREGATE_UPDATE" | "ACCOUNT_REMOVED";
  account_id?: string;
  data?: any;
}

export interface BrokerConfig {
  broker_name: string;
  account_id?: string;
  account_type: "live" | "demo";
  display_name: string;
  credentials: Record<string, string>;
  [key: string]: any;
}

export interface PLData {
  timestamp: string;
  value: number;
  broker_id?: string;
}

export interface BrokerComparison {
  broker_id: string;
  broker_name: string;
  performance_score: number;
  metrics: BrokerPerformanceMetrics;
}