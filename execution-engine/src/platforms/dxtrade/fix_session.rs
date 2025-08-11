use super::config::DXTradeConfig;
use super::error::{DXTradeError, Result};
use super::fix_messages::{FIXMessage, MessageType};
use super::ssl_handler::SslHandler;
use chrono::{DateTime, Utc};
use std::collections::VecDeque;
use std::sync::atomic::{AtomicU32, AtomicBool, Ordering};
use std::sync::{Arc, Weak};
use std::time::{Duration, Instant};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;
use tokio::sync::{mpsc, Mutex, RwLock};
use tokio::time;
use tokio_native_tls::TlsStream;

#[derive(Debug, Clone)]
pub enum SessionState {
    Disconnected,
    Connecting,
    LogonSent,
    LoggedIn,
    LogoutSent,
    Reconnecting,
    ShuttingDown,
}

pub struct FIXSession {
    config: Arc<DXTradeConfig>,
    ssl_handler: Arc<SslHandler>,
    session_state: Arc<RwLock<SessionState>>,
    next_seq_num_out: Arc<AtomicU32>,
    next_seq_num_in: Arc<AtomicU32>,
    is_active: Arc<AtomicBool>,
    connection: Arc<Mutex<Option<TlsStream<TcpStream>>>>,
    outbound_queue: Arc<Mutex<VecDeque<FIXMessage>>>,
    sequence_store: Arc<Mutex<SequenceStore>>,
    last_heartbeat_sent: Arc<Mutex<Option<Instant>>>,
    last_heartbeat_received: Arc<Mutex<Option<Instant>>>,
    message_sender: mpsc::UnboundedSender<FIXMessage>,
    message_receiver: Arc<Mutex<mpsc::UnboundedReceiver<FIXMessage>>>,
    session_id: String,
}

#[derive(Debug)]
struct SequenceStore {
    sent_messages: VecDeque<(u32, FIXMessage)>,
    max_stored_messages: usize,
    last_persisted_seq: u32,
}

impl FIXSession {
    pub fn new(config: DXTradeConfig, ssl_handler: SslHandler) -> Result<Self> {
        let (tx, rx) = mpsc::unbounded_channel();
        let session_id = format!("{}_{}", 
            config.credentials.sender_comp_id, 
            Utc::now().timestamp()
        );
        
        Ok(Self {
            config: Arc::new(config),
            ssl_handler: Arc::new(ssl_handler),
            session_state: Arc::new(RwLock::new(SessionState::Disconnected)),
            next_seq_num_out: Arc::new(AtomicU32::new(1)),
            next_seq_num_in: Arc::new(AtomicU32::new(1)),
            is_active: Arc::new(AtomicBool::new(false)),
            connection: Arc::new(Mutex::new(None)),
            outbound_queue: Arc::new(Mutex::new(VecDeque::new())),
            sequence_store: Arc::new(Mutex::new(SequenceStore {
                sent_messages: VecDeque::new(),
                max_stored_messages: 1000,
                last_persisted_seq: 0,
            })),
            last_heartbeat_sent: Arc::new(Mutex::new(None)),
            last_heartbeat_received: Arc::new(Mutex::new(None)),
            message_sender: tx,
            message_receiver: Arc::new(Mutex::new(rx)),
            session_id,
        })
    }
    
    pub async fn connect(&self) -> Result<()> {
        {
            let mut state = self.session_state.write().await;
            *state = SessionState::Connecting;
        }
        
        let hostname = self.config.credentials.environment.fix_host();
        let port = self.config.credentials.environment.fix_port();
        
        tracing::info!("Connecting to DXtrade FIX gateway at {}:{}", hostname, port);
        
        let tls_stream = self.ssl_handler.connect_to_server(hostname, port).await?;
        
        {
            let mut connection = self.connection.lock().await;
            *connection = Some(tls_stream);
        }
        
        self.is_active.store(true, Ordering::SeqCst);
        
        self.send_logon().await?;
        
        let session_clone = self.clone_session_handles();
        tokio::spawn(async move {
            if let Err(e) = session_clone.message_processing_loop().await {
                tracing::error!("Message processing loop error: {}", e);
            }
        });
        
        let heartbeat_session = self.clone_session_handles();
        tokio::spawn(async move {
            if let Err(e) = heartbeat_session.heartbeat_loop().await {
                tracing::error!("Heartbeat loop error: {}", e);
            }
        });
        
        Ok(())
    }
    
    async fn send_logon(&self) -> Result<()> {
        let seq_num = self.next_seq_num_out.fetch_add(1, Ordering::SeqCst);
        let logon_message = FIXMessage::create_logon(
            self.config.credentials.sender_comp_id.clone(),
            self.config.credentials.target_comp_id.clone(),
            seq_num,
            self.config.connection.heartbeat_interval_s,
            false,
        )?;
        
        self.send_message(logon_message).await?;
        
        {
            let mut state = self.session_state.write().await;
            *state = SessionState::LogonSent;
        }
        
        tracing::info!("Logon message sent");
        Ok(())
    }
    
    pub async fn send_message(&self, message: FIXMessage) -> Result<()> {
        if !self.is_active.load(Ordering::SeqCst) {
            return Err(DXTradeError::FixSessionError("Session is not active".to_string()));
        }
        
        {
            let mut connection_guard = self.connection.lock().await;
            if let Some(ref mut stream) = connection_guard.as_mut() {
                stream.write_all(message.raw_message.as_bytes()).await
                    .map_err(|e| DXTradeError::FixSessionError(format!("Failed to send message: {}", e)))?;
            } else {
                return Err(DXTradeError::FixSessionError("No active connection".to_string()));
            }
        }
        
        if !message.is_admin_message() {
            let mut store = self.sequence_store.lock().await;
            let seq_num = message.get_field_as_u32(34).unwrap_or(0);
            store.sent_messages.push_back((seq_num, message.clone()));
            
            if store.sent_messages.len() > store.max_stored_messages {
                store.sent_messages.pop_front();
            }
        }
        
        tracing::debug!("Sent FIX message: {}", message.msg_type.to_string());
        Ok(())
    }
    
    async fn message_processing_loop(&self) -> Result<()> {
        let mut buffer = vec![0u8; 8192];
        let mut incomplete_message = String::new();
        
        while self.is_active.load(Ordering::SeqCst) {
            let bytes_read = {
                let mut connection_guard = self.connection.lock().await;
                if let Some(ref mut stream) = connection_guard.as_mut() {
                    match time::timeout(Duration::from_secs(1), stream.read(&mut buffer)).await {
                        Ok(Ok(n)) => Ok(n),
                        Ok(Err(e)) => Err(e),
                        Err(_) => {
                            // Timeout
                            continue;
                        }
                    }
                } else {
                    tokio::time::sleep(Duration::from_millis(100)).await;
                    continue;
                }
            };
            
            match bytes_read {
                Ok(bytes_read) if bytes_read > 0 => {
                    let data = String::from_utf8_lossy(&buffer[..bytes_read]);
                    incomplete_message.push_str(&data);
                    
                    while let Some(end_pos) = incomplete_message.find("10=") {
                        if let Some(msg_end) = incomplete_message[end_pos..].find('\x01') {
                            let full_msg_end = end_pos + msg_end + 1;
                            let message_str = incomplete_message[..full_msg_end].to_string();
                            incomplete_message = incomplete_message[full_msg_end..].to_string();
                            
                            if let Err(e) = self.handle_incoming_message(&message_str).await {
                                tracing::error!("Error handling message: {}", e);
                            }
                        } else {
                            break;
                        }
                    }
                }
                Ok(0) => {
                    tracing::warn!("Connection closed by remote");
                    self.handle_disconnect().await;
                    break;
                }
                Ok(_) => {
                    // Handle any other bytes_read values
                    continue;
                }
                Err(e) => {
                    tracing::error!("Read error: {}", e);
                    self.handle_disconnect().await;
                    break;
                }
            }
        }
        
        Ok(())
    }
    
    async fn handle_incoming_message(&self, raw_message: &str) -> Result<()> {
        let message = FIXMessage::parse(raw_message)?;
        
        if !message.validate_checksum() {
            tracing::warn!("Received message with invalid checksum");
            return Ok(());
        }
        
        let expected_seq = self.next_seq_num_in.load(Ordering::SeqCst);
        let received_seq = message.get_field_as_u32(34).unwrap_or(0);
        
        if received_seq != expected_seq && !message.is_admin_message() {
            tracing::warn!("Sequence number gap detected. Expected: {}, Received: {}", expected_seq, received_seq);
            return self.handle_sequence_gap(expected_seq, received_seq).await;
        }
        
        if !message.is_admin_message() {
            self.next_seq_num_in.fetch_add(1, Ordering::SeqCst);
        }
        
        match message.msg_type {
            MessageType::Logon => self.handle_logon_response(&message).await?,
            MessageType::Logout => self.handle_logout(&message).await?,
            MessageType::Heartbeat => self.handle_heartbeat(&message).await?,
            MessageType::TestRequest => self.handle_test_request(&message).await?,
            MessageType::ResendRequest => self.handle_resend_request(&message).await?,
            MessageType::SequenceReset => self.handle_sequence_reset(&message).await?,
            MessageType::Reject => self.handle_reject(&message).await?,
            _ => {
                if let Err(e) = self.message_sender.send(message) {
                    tracing::error!("Failed to queue message: {}", e);
                }
            }
        }
        
        {
            let mut last_received = self.last_heartbeat_received.lock().await;
            *last_received = Some(Instant::now());
        }
        
        Ok(())
    }
    
    async fn handle_logon_response(&self, message: &FIXMessage) -> Result<()> {
        tracing::info!("Received logon response");
        
        {
            let mut state = self.session_state.write().await;
            *state = SessionState::LoggedIn;
        }
        
        Ok(())
    }
    
    async fn handle_logout(&self, message: &FIXMessage) -> Result<()> {
        tracing::info!("Received logout message");
        
        let seq_num = self.next_seq_num_out.fetch_add(1, Ordering::SeqCst);
        let logout_response = FIXMessage::create_logout(
            self.config.credentials.sender_comp_id.clone(),
            self.config.credentials.target_comp_id.clone(),
            seq_num,
            None,
        )?;
        
        self.send_message(logout_response).await?;
        self.handle_disconnect().await;
        
        Ok(())
    }
    
    async fn handle_heartbeat(&self, _message: &FIXMessage) -> Result<()> {
        tracing::debug!("Received heartbeat");
        Ok(())
    }
    
    async fn handle_test_request(&self, message: &FIXMessage) -> Result<()> {
        tracing::debug!("Received test request");
        
        let test_req_id = message.get_field(112).cloned().unwrap_or_default();
        let seq_num = self.next_seq_num_out.fetch_add(1, Ordering::SeqCst);
        
        let heartbeat = FIXMessage::create_heartbeat(
            self.config.credentials.sender_comp_id.clone(),
            self.config.credentials.target_comp_id.clone(),
            seq_num,
        )?;
        
        self.send_message(heartbeat).await?;
        
        Ok(())
    }
    
    async fn handle_resend_request(&self, message: &FIXMessage) -> Result<()> {
        let begin_seq_no = message.get_field_as_u32(7).unwrap_or(0);
        let end_seq_no = message.get_field_as_u32(16).unwrap_or(0);
        
        tracing::info!("Handling resend request for sequences {} to {}", begin_seq_no, end_seq_no);
        
        let store = self.sequence_store.lock().await;
        for (seq_num, stored_message) in &store.sent_messages {
            if *seq_num >= begin_seq_no && (end_seq_no == 0 || *seq_num <= end_seq_no) {
                self.send_message(stored_message.clone()).await?;
            }
        }
        
        Ok(())
    }
    
    async fn handle_sequence_reset(&self, message: &FIXMessage) -> Result<()> {
        let new_seq_no = message.get_field_as_u32(36).unwrap_or(1);
        tracing::info!("Handling sequence reset to {}", new_seq_no);
        
        self.next_seq_num_in.store(new_seq_no, Ordering::SeqCst);
        
        Ok(())
    }
    
    async fn handle_reject(&self, message: &FIXMessage) -> Result<()> {
        let ref_seq_num = message.get_field_as_u32(45).unwrap_or(0);
        let reject_reason = message.get_field(58).cloned().unwrap_or("Unknown".to_string());
        
        tracing::error!("Received reject for sequence {}: {}", ref_seq_num, reject_reason);
        
        Ok(())
    }
    
    async fn handle_sequence_gap(&self, expected: u32, received: u32) -> Result<()> {
        if received > expected {
            tracing::info!("Sending resend request for sequences {} to {}", expected, received - 1);
            
            let seq_num = self.next_seq_num_out.fetch_add(1, Ordering::SeqCst);
            let resend_request = FIXMessage {
                msg_type: MessageType::ResendRequest,
                fields: [
                    (8, "FIX.4.4".to_string()),
                    (35, "2".to_string()),
                    (49, self.config.credentials.sender_comp_id.clone()),
                    (56, self.config.credentials.target_comp_id.clone()),
                    (34, seq_num.to_string()),
                    (52, Utc::now().format("%Y%m%d-%H:%M:%S%.3f").to_string()),
                    (7, expected.to_string()),
                    (16, (received - 1).to_string()),
                ].iter().cloned().collect(),
                raw_message: String::new(),
            };
            
            self.send_message(resend_request).await?;
        }
        
        Ok(())
    }
    
    async fn heartbeat_loop(&self) -> Result<()> {
        let heartbeat_interval = self.config.heartbeat_interval();
        let test_request_delay = Duration::from_secs(self.config.connection.test_request_delay_s as u64);
        
        while self.is_active.load(Ordering::SeqCst) {
            tokio::time::sleep(heartbeat_interval).await;
            
            let should_send_heartbeat = {
                let last_sent = self.last_heartbeat_sent.lock().await;
                last_sent.map_or(true, |t| t.elapsed() >= heartbeat_interval)
            };
            
            if should_send_heartbeat {
                let seq_num = self.next_seq_num_out.fetch_add(1, Ordering::SeqCst);
                let heartbeat = FIXMessage::create_heartbeat(
                    self.config.credentials.sender_comp_id.clone(),
                    self.config.credentials.target_comp_id.clone(),
                    seq_num,
                )?;
                
                if let Err(e) = self.send_message(heartbeat).await {
                    tracing::error!("Failed to send heartbeat: {}", e);
                    break;
                }
                
                {
                    let mut last_sent = self.last_heartbeat_sent.lock().await;
                    *last_sent = Some(Instant::now());
                }
            }
            
            let should_send_test_request = {
                let last_received = self.last_heartbeat_received.lock().await;
                last_received.map_or(false, |t| t.elapsed() >= test_request_delay)
            };
            
            if should_send_test_request {
                let seq_num = self.next_seq_num_out.fetch_add(1, Ordering::SeqCst);
                let test_request = FIXMessage::create_test_request(
                    self.config.credentials.sender_comp_id.clone(),
                    self.config.credentials.target_comp_id.clone(),
                    seq_num,
                    format!("TEST-{}", Utc::now().timestamp()),
                )?;
                
                if let Err(e) = self.send_message(test_request).await {
                    tracing::error!("Failed to send test request: {}", e);
                    break;
                }
            }
        }
        
        Ok(())
    }
    
    async fn handle_disconnect(&self) -> Result<()> {
        tracing::info!("Handling session disconnect");
        
        self.is_active.store(false, Ordering::SeqCst);
        
        {
            let mut connection = self.connection.lock().await;
            *connection = None;
        }
        
        {
            let mut state = self.session_state.write().await;
            *state = SessionState::Disconnected;
        }
        
        Ok(())
    }
    
    pub async fn disconnect(&self) -> Result<()> {
        let seq_num = self.next_seq_num_out.fetch_add(1, Ordering::SeqCst);
        let logout_message = FIXMessage::create_logout(
            self.config.credentials.sender_comp_id.clone(),
            self.config.credentials.target_comp_id.clone(),
            seq_num,
            Some("Session termination requested".to_string()),
        )?;
        
        {
            let mut state = self.session_state.write().await;
            *state = SessionState::LogoutSent;
        }
        
        self.send_message(logout_message).await?;
        
        tokio::time::sleep(Duration::from_secs(2)).await;
        
        self.handle_disconnect().await?;
        
        Ok(())
    }
    
    pub async fn get_session_state(&self) -> SessionState {
        self.session_state.read().await.clone()
    }
    
    pub fn get_session_id(&self) -> &str {
        &self.session_id
    }
    
    pub fn get_next_seq_num_out(&self) -> u32 {
        self.next_seq_num_out.load(Ordering::SeqCst)
    }
    
    pub fn get_next_seq_num_in(&self) -> u32 {
        self.next_seq_num_in.load(Ordering::SeqCst)
    }
    
    fn clone_session_handles(&self) -> SessionHandles {
        SessionHandles {
            config: Arc::downgrade(&self.config),
            ssl_handler: Arc::downgrade(&self.ssl_handler),
            session_state: Arc::downgrade(&self.session_state),
            next_seq_num_out: Arc::downgrade(&self.next_seq_num_out),
            next_seq_num_in: Arc::downgrade(&self.next_seq_num_in),
            is_active: Arc::downgrade(&self.is_active),
            connection: Arc::downgrade(&self.connection),
            outbound_queue: Arc::downgrade(&self.outbound_queue),
            sequence_store: Arc::downgrade(&self.sequence_store),
            last_heartbeat_sent: Arc::downgrade(&self.last_heartbeat_sent),
            last_heartbeat_received: Arc::downgrade(&self.last_heartbeat_received),
            message_sender: self.message_sender.clone(),
            session_id: self.session_id.clone(),
        }
    }
}

struct SessionHandles {
    config: Weak<DXTradeConfig>,
    ssl_handler: Weak<SslHandler>,
    session_state: Weak<RwLock<SessionState>>,
    next_seq_num_out: Weak<AtomicU32>,
    next_seq_num_in: Weak<AtomicU32>,
    is_active: Weak<AtomicBool>,
    connection: Weak<Mutex<Option<TlsStream<TcpStream>>>>,
    outbound_queue: Weak<Mutex<VecDeque<FIXMessage>>>,
    sequence_store: Weak<Mutex<SequenceStore>>,
    last_heartbeat_sent: Weak<Mutex<Option<Instant>>>,
    last_heartbeat_received: Weak<Mutex<Option<Instant>>>,
    message_sender: mpsc::UnboundedSender<FIXMessage>,
    session_id: String,
}

impl SessionHandles {
    async fn message_processing_loop(&self) -> Result<()> {
        // Upgrade weak references to strong ones, exit if session was dropped
        let is_active = self.is_active.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
        let connection = self.connection.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
        let next_seq_num_in = self.next_seq_num_in.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
        let last_heartbeat_received = self.last_heartbeat_received.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
            
        let mut buffer = vec![0u8; 8192];
        let mut incomplete_message = String::new();
        
        while is_active.load(Ordering::SeqCst) {
            // Check if references are still valid
            if self.is_active.upgrade().is_none() {
                tracing::debug!("Session dropped, exiting message processing loop");
                break;
            }
            
            let bytes_read = {
                let mut connection_guard = connection.lock().await;
                if let Some(ref mut stream) = connection_guard.as_mut() {
                    match time::timeout(Duration::from_secs(1), stream.read(&mut buffer)).await {
                        Ok(Ok(n)) => Ok(n),
                        Ok(Err(e)) => Err(e),
                        Err(_) => {
                            // Timeout, continue loop
                            continue;
                        }
                    }
                } else {
                    tokio::time::sleep(Duration::from_millis(100)).await;
                    continue;
                }
            };
            
            match bytes_read {
                Ok(bytes_read) if bytes_read > 0 => {
                    let data = String::from_utf8_lossy(&buffer[..bytes_read]);
                    incomplete_message.push_str(&data);
                    
                    while let Some(end_pos) = incomplete_message.find("10=") {
                        if let Some(msg_end) = incomplete_message[end_pos..].find('\x01') {
                            let full_msg_end = end_pos + msg_end + 1;
                            let message_str = incomplete_message[..full_msg_end].to_string();
                            incomplete_message = incomplete_message[full_msg_end..].to_string();
                            
                            if let Err(e) = self.handle_incoming_message(&message_str).await {
                                tracing::error!("Error handling message: {}", e);
                            }
                        } else {
                            break;
                        }
                    }
                }
                Ok(0) => {
                    tracing::warn!("Connection closed by remote");
                    self.handle_disconnect().await;
                    break;
                }
                Ok(_) => {
                    continue;
                }
                Err(e) => {
                    tracing::error!("Read error: {}", e);
                    self.handle_disconnect().await;
                    break;
                }
            }
        }
        
        Ok(())
    }
    
    async fn heartbeat_loop(&self) -> Result<()> {
        // Upgrade weak references to strong ones, exit if session was dropped
        let is_active = self.is_active.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
        let config = self.config.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
        let next_seq_num_out = self.next_seq_num_out.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
        let last_heartbeat_sent = self.last_heartbeat_sent.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
        let last_heartbeat_received = self.last_heartbeat_received.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
            
        let heartbeat_interval = config.heartbeat_interval();
        let test_request_delay = Duration::from_secs(config.connection.test_request_delay_s as u64);
        
        while is_active.load(Ordering::SeqCst) {
            // Check if references are still valid
            if self.is_active.upgrade().is_none() {
                tracing::debug!("Session dropped, exiting heartbeat loop");
                break;
            }
            
            tokio::time::sleep(heartbeat_interval).await;
            
            let should_send_heartbeat = {
                let last_sent = last_heartbeat_sent.lock().await;
                last_sent.map_or(true, |t| t.elapsed() >= heartbeat_interval)
            };
            
            if should_send_heartbeat {
                let seq_num = next_seq_num_out.fetch_add(1, Ordering::SeqCst);
                let heartbeat = FIXMessage::create_heartbeat(
                    config.credentials.sender_comp_id.clone(),
                    config.credentials.target_comp_id.clone(),
                    seq_num,
                )?;
                
                if let Err(e) = self.send_message(heartbeat).await {
                    tracing::error!("Failed to send heartbeat: {}", e);
                    break;
                }
                
                {
                    let mut last_sent = last_heartbeat_sent.lock().await;
                    *last_sent = Some(Instant::now());
                }
            }
            
            let should_send_test_request = {
                let last_received = last_heartbeat_received.lock().await;
                last_received.map_or(false, |t| t.elapsed() >= test_request_delay)
            };
            
            if should_send_test_request {
                let seq_num = next_seq_num_out.fetch_add(1, Ordering::SeqCst);
                let test_request = FIXMessage::create_test_request(
                    config.credentials.sender_comp_id.clone(),
                    config.credentials.target_comp_id.clone(),
                    seq_num,
                    format!("TEST-{}", Utc::now().timestamp()),
                )?;
                
                if let Err(e) = self.send_message(test_request).await {
                    tracing::error!("Failed to send test request: {}", e);
                    break;
                }
            }
        }
        
        Ok(())
    }
    
    async fn handle_incoming_message(&self, raw_message: &str) -> Result<()> {
        let message = FIXMessage::parse(raw_message)?;
        
        if !message.validate_checksum() {
            tracing::warn!("Received message with invalid checksum");
            return Ok(());
        }
        
        // Try to upgrade weak references
        let next_seq_num_in = self.next_seq_num_in.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
        let last_heartbeat_received = self.last_heartbeat_received.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
            
        let expected_seq = next_seq_num_in.load(Ordering::SeqCst);
        let received_seq = message.get_field_as_u32(34).unwrap_or(0);
        
        if received_seq != expected_seq && !message.is_admin_message() {
            tracing::warn!("Sequence number gap detected. Expected: {}, Received: {}", expected_seq, received_seq);
            // For simplicity, just log the gap in this handles version
        }
        
        if !message.is_admin_message() {
            next_seq_num_in.fetch_add(1, Ordering::SeqCst);
        }
        
        // Send application messages to the main session
        if !message.is_admin_message() {
            if let Err(e) = self.message_sender.send(message) {
                tracing::error!("Failed to queue message: {}", e);
            }
        }
        
        {
            let mut last_received = last_heartbeat_received.lock().await;
            *last_received = Some(Instant::now());
        }
        
        Ok(())
    }
    
    async fn send_message(&self, message: FIXMessage) -> Result<()> {
        let is_active = self.is_active.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
        let connection = self.connection.upgrade()
            .ok_or_else(|| DXTradeError::FixSessionError("Session was dropped".to_string()))?;
            
        if !is_active.load(Ordering::SeqCst) {
            return Err(DXTradeError::FixSessionError("Session is not active".to_string()));
        }
        
        {
            let mut connection_guard = connection.lock().await;
            if let Some(ref mut stream) = connection_guard.as_mut() {
                stream.write_all(message.raw_message.as_bytes()).await
                    .map_err(|e| DXTradeError::FixSessionError(format!("Failed to send message: {}", e)))?;
            } else {
                return Err(DXTradeError::FixSessionError("No active connection".to_string()));
            }
        }
        
        tracing::debug!("Sent FIX message: {}", message.msg_type.to_string());
        Ok(())
    }
    
    async fn handle_disconnect(&self) -> Result<()> {
        tracing::info!("Handling session disconnect in background task");
        
        if let Some(is_active) = self.is_active.upgrade() {
            is_active.store(false, Ordering::SeqCst);
        }
        
        if let Some(connection) = self.connection.upgrade() {
            let mut conn = connection.lock().await;
            *conn = None;
        }
        
        if let Some(session_state) = self.session_state.upgrade() {
            let mut state = session_state.write().await;
            *state = SessionState::Disconnected;
        }
        
        Ok(())
    }
}