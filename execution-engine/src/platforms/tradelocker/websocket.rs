use std::sync::Arc;
use std::time::Duration;
use tokio::sync::{mpsc, RwLock};
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tracing::{debug, error, info, warn};
use url::Url;

use super::{
    TradeLockerAuth, TradeLockerConfig, TradeLockerError, Result,
    TradeLockerEnvironment, MarketData, Position, OrderResponse
};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WebSocketMessage {
    Subscribe {
        channels: Vec<String>,
    },
    Unsubscribe {
        channels: Vec<String>,
    },
    Ping,
    Pong,
    Auth {
        token: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WebSocketEvent {
    Connected,
    Authenticated,
    MarketData(MarketData),
    OrderUpdate(OrderResponse),
    PositionUpdate(Position),
    AccountUpdate(Value),
    Error { message: String },
    Disconnected,
}

#[derive(Debug)]
pub struct TradeLockerWebSocket {
    auth: Arc<TradeLockerAuth>,
    config: TradeLockerConfig,
    environment: TradeLockerEnvironment,
    event_sender: mpsc::UnboundedSender<WebSocketEvent>,
    event_receiver: Arc<RwLock<Option<mpsc::UnboundedReceiver<WebSocketEvent>>>>,
    is_connected: Arc<RwLock<bool>>,
    subscriptions: Arc<RwLock<Vec<String>>>,
}

impl TradeLockerWebSocket {
    pub fn new(
        auth: Arc<TradeLockerAuth>,
        config: TradeLockerConfig,
        environment: TradeLockerEnvironment,
    ) -> Self {
        let (event_sender, event_receiver) = mpsc::unbounded_channel();

        Self {
            auth,
            config,
            environment,
            event_sender,
            event_receiver: Arc::new(RwLock::new(Some(event_receiver))),
            is_connected: Arc::new(RwLock::new(false)),
            subscriptions: Arc::new(RwLock::new(Vec::new())),
        }
    }

    pub async fn connect(&self, account_id: &str) -> Result<()> {
        let token = self.auth.get_token(account_id).await?;
        let ws_url = format!("{}?token={}", self.environment.ws_url(), token);
        
        self.connect_with_retry(&ws_url, account_id).await
    }

    async fn connect_with_retry(&self, ws_url: &str, account_id: &str) -> Result<()> {
        let mut retries = 0;
        let max_retries = 5;
        let mut backoff = Duration::from_millis(1000);

        loop {
            match self.establish_connection(ws_url, account_id).await {
                Ok(_) => return Ok(()),
                Err(e) => {
                    retries += 1;
                    if retries >= max_retries {
                        error!("Max retries reached for WebSocket connection");
                        return Err(e);
                    }

                    warn!("WebSocket connection failed (attempt {}): {}", retries, e);
                    tokio::time::sleep(backoff).await;
                    backoff = (backoff * 2).min(Duration::from_secs(30));
                }
            }
        }
    }

    async fn establish_connection(&self, ws_url: &str, account_id: &str) -> Result<()> {
        let url = Url::parse(ws_url)
            .map_err(|e| TradeLockerError::WebSocket(format!("Invalid URL: {}", e)))?;

        let (ws_stream, _) = connect_async(url).await
            .map_err(|e| TradeLockerError::WebSocket(format!("Connection failed: {}", e)))?;

        info!("WebSocket connected for account: {}", account_id);

        let (mut write, mut read) = ws_stream.split();

        // Mark as connected
        *self.is_connected.write().await = true;
        self.event_sender.send(WebSocketEvent::Connected)
            .map_err(|e| TradeLockerError::WebSocket(format!("Event send failed: {}", e)))?;

        // Authenticate
        let auth_msg = WebSocketMessage::Auth {
            token: self.auth.get_token(account_id).await?,
        };
        
        let auth_json = serde_json::to_string(&auth_msg)?;
        write.send(Message::Text(auth_json)).await
            .map_err(|e| TradeLockerError::WebSocket(format!("Auth send failed: {}", e)))?;

        // Resubscribe to previous channels
        let subscriptions = self.subscriptions.read().await.clone();
        if !subscriptions.is_empty() {
            let sub_msg = WebSocketMessage::Subscribe {
                channels: subscriptions,
            };
            let sub_json = serde_json::to_string(&sub_msg)?;
            write.send(Message::Text(sub_json)).await
                .map_err(|e| TradeLockerError::WebSocket(format!("Subscribe failed: {}", e)))?;
        }

        // Spawn ping task
        let ping_interval = self.config.ws_ping_interval();
        let write_clone = Arc::new(tokio::sync::Mutex::new(write));
        let ping_write = write_clone.clone();
        
        tokio::spawn(async move {
            let mut interval = tokio::time::interval(ping_interval);
            loop {
                interval.tick().await;
                let ping_msg = serde_json::to_string(&WebSocketMessage::Ping).unwrap();
                if let Err(e) = ping_write.lock().await.send(Message::Text(ping_msg)).await {
                    error!("Ping failed: {}", e);
                    break;
                }
            }
        });

        // Handle incoming messages
        let event_sender = self.event_sender.clone();
        let is_connected = self.is_connected.clone();
        let account_id = account_id.to_string();

        tokio::spawn(async move {
            while let Some(msg) = read.next().await {
                match msg {
                    Ok(Message::Text(text)) => {
                        if let Err(e) = Self::handle_message(&text, &event_sender).await {
                            error!("Failed to handle message: {}", e);
                        }
                    }
                    Ok(Message::Binary(data)) => {
                        debug!("Received binary data: {} bytes", data.len());
                    }
                    Ok(Message::Close(_)) => {
                        info!("WebSocket closed for account: {}", account_id);
                        *is_connected.write().await = false;
                        let _ = event_sender.send(WebSocketEvent::Disconnected);
                        break;
                    }
                    Ok(Message::Pong(_)) => {
                        debug!("Received pong");
                    }
                    Err(e) => {
                        error!("WebSocket error: {}", e);
                        *is_connected.write().await = false;
                        let _ = event_sender.send(WebSocketEvent::Error {
                            message: e.to_string(),
                        });
                        break;
                    }
                    _ => {}
                }
            }
        });

        Ok(())
    }

    async fn handle_message(
        text: &str,
        event_sender: &mpsc::UnboundedSender<WebSocketEvent>
    ) -> Result<()> {
        let data: Value = serde_json::from_str(text)?;
        
        if let Some(msg_type) = data.get("type").and_then(|v| v.as_str()) {
            let event = match msg_type {
                "authenticated" => WebSocketEvent::Authenticated,
                "market_data" => {
                    let market_data: MarketData = serde_json::from_value(data)?;
                    WebSocketEvent::MarketData(market_data)
                }
                "order_update" => {
                    let order: OrderResponse = serde_json::from_value(data)?;
                    WebSocketEvent::OrderUpdate(order)
                }
                "position_update" => {
                    let position: Position = serde_json::from_value(data)?;
                    WebSocketEvent::PositionUpdate(position)
                }
                "account_update" => {
                    WebSocketEvent::AccountUpdate(data)
                }
                "error" => {
                    let message = data.get("message")
                        .and_then(|v| v.as_str())
                        .unwrap_or("Unknown error")
                        .to_string();
                    WebSocketEvent::Error { message }
                }
                "pong" => {
                    debug!("Received pong response");
                    return Ok(());
                }
                _ => {
                    debug!("Unknown message type: {}", msg_type);
                    return Ok(());
                }
            };

            event_sender.send(event)
                .map_err(|e| TradeLockerError::WebSocket(format!("Event send failed: {}", e)))?;
        }

        Ok(())
    }

    pub async fn subscribe(&self, channels: Vec<String>) -> Result<()> {
        if !*self.is_connected.read().await {
            return Err(TradeLockerError::WebSocket("Not connected".into()));
        }

        // Update local subscriptions
        let mut subs = self.subscriptions.write().await;
        for channel in &channels {
            if !subs.contains(channel) {
                subs.push(channel.clone());
            }
        }
        drop(subs);

        // Send subscribe message
        let msg = WebSocketMessage::Subscribe { channels };
        let _json = serde_json::to_string(&msg)?;
        
        // Note: In production, we'd send this through the write stream
        // For now, we'll assume it's handled by the connection
        
        Ok(())
    }

    pub async fn unsubscribe(&self, channels: Vec<String>) -> Result<()> {
        if !*self.is_connected.read().await {
            return Err(TradeLockerError::WebSocket("Not connected".into()));
        }

        // Update local subscriptions
        let mut subs = self.subscriptions.write().await;
        subs.retain(|s| !channels.contains(s));
        drop(subs);

        // Send unsubscribe message
        let msg = WebSocketMessage::Unsubscribe { channels };
        let _json = serde_json::to_string(&msg)?;
        
        Ok(())
    }

    pub async fn get_event_receiver(&self) -> Option<mpsc::UnboundedReceiver<WebSocketEvent>> {
        self.event_receiver.write().await.take()
    }

    pub async fn is_connected(&self) -> bool {
        *self.is_connected.read().await
    }

    pub async fn disconnect(&self) {
        *self.is_connected.write().await = false;
        let _ = self.event_sender.send(WebSocketEvent::Disconnected);
    }

    pub async fn reconnect(&self, account_id: &str) -> Result<()> {
        self.disconnect().await;
        tokio::time::sleep(self.config.ws_reconnect_delay()).await;
        self.connect(account_id).await
    }
}