// Custom hook for managing broker data and WebSocket connections

import { useState, useEffect, useCallback, useRef } from 'react';
import { BrokerAccount, AggregateData, WebSocketMessage, ConnectionStatus } from '../types/broker';

interface UseBrokerDataReturn {
  brokerAccounts: BrokerAccount[];
  aggregateData: AggregateData | null;
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  isLoading: boolean;
  error: string | null;
  reconnectBroker: (accountId: string) => Promise<void>;
  addBrokerAccount: (config: any) => Promise<void>;
  removeBrokerAccount: (accountId: string) => Promise<void>;
  refreshData: () => Promise<void>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/dashboard';

export const useBrokerData = (): UseBrokerDataReturn => {
  const [brokerAccounts, setBrokerAccounts] = useState<BrokerAccount[]>([]);
  const [aggregateData, setAggregateData] = useState<AggregateData | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // Fetch initial data from REST API
  const fetchInitialData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Fetch broker accounts
      const brokersResponse = await fetch(`${API_BASE_URL}/api/brokers`);
      if (!brokersResponse.ok) {
        throw new Error(`Failed to fetch brokers: ${brokersResponse.statusText}`);
      }
      const brokersData = await brokersResponse.json();
      setBrokerAccounts(brokersData);

      // Fetch aggregate data
      const aggregateResponse = await fetch(`${API_BASE_URL}/api/aggregate`);
      if (!aggregateResponse.ok) {
        throw new Error(`Failed to fetch aggregate data: ${aggregateResponse.statusText}`);
      }
      const aggregateData = await aggregateResponse.json();
      setAggregateData(aggregateData);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching initial data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // WebSocket connection management
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus('connecting');
    
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
        setError(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          switch (message.type) {
            case 'BROKER_UPDATE':
              if (message.account_id && message.data) {
                setBrokerAccounts(prev => {
                  const updated = [...prev];
                  const index = updated.findIndex(acc => acc.id === message.account_id);
                  
                  if (index >= 0) {
                    updated[index] = message.data;
                  } else {
                    updated.push(message.data);
                  }
                  
                  return updated;
                });
              }
              break;

            case 'AGGREGATE_UPDATE':
              if (message.data) {
                setAggregateData(message.data);
              }
              break;

            case 'ACCOUNT_REMOVED':
              if (message.account_id) {
                setBrokerAccounts(prev => 
                  prev.filter(acc => acc.id !== message.account_id)
                );
              }
              break;

            default:
              console.warn('Unknown WebSocket message type:', message.type);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionStatus('disconnected');
        
        // Attempt reconnection with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000; // Exponential backoff
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connectWebSocket();
          }, delay);
        } else {
          setConnectionStatus('error');
          setError('Failed to establish WebSocket connection after multiple attempts');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        setError('WebSocket connection error');
      };

    } catch (err) {
      console.error('Error creating WebSocket:', err);
      setConnectionStatus('error');
      setError('Failed to create WebSocket connection');
    }
  }, []);

  // Cleanup WebSocket connection
  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnectionStatus('disconnected');
  }, []);

  // API functions
  const reconnectBroker = useCallback(async (accountId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/brokers/${accountId}/reconnect`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to reconnect broker: ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log(`Broker ${accountId} reconnection result:`, result);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to reconnect broker';
      setError(errorMessage);
      throw err;
    }
  }, []);

  const addBrokerAccount = useCallback(async (config: any) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/brokers`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to add broker account: ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('Broker account added:', result);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add broker account';
      setError(errorMessage);
      throw err;
    }
  }, []);

  const removeBrokerAccount = useCallback(async (accountId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/brokers/${accountId}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to remove broker account: ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log(`Broker account ${accountId} removed:`, result);
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to remove broker account';
      setError(errorMessage);
      throw err;
    }
  }, []);

  const refreshData = useCallback(async () => {
    await fetchInitialData();
  }, [fetchInitialData]);

  // Initialize connection and data
  useEffect(() => {
    fetchInitialData();
    connectWebSocket();
    
    return () => {
      disconnectWebSocket();
    };
  }, [fetchInitialData, connectWebSocket, disconnectWebSocket]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    brokerAccounts,
    aggregateData,
    connectionStatus,
    isLoading,
    error,
    reconnectBroker,
    addBrokerAccount,
    removeBrokerAccount,
    refreshData,
  };
};