use super::config::DXTradeConfig;
use super::error::{DXTradeError, Result};
use super::fix_session::{FIXSession, SessionState};
use super::fix_messages::FIXMessage;
use super::ssl_handler::SslHandler;
use super::auth::DXTradeAuth;
use std::sync::Arc;
use tokio::sync::RwLock;

pub struct FIXClient {
    config: Arc<DXTradeConfig>,
    auth: Arc<RwLock<DXTradeAuth>>,
    session: Arc<RwLock<Option<FIXSession>>>,
    ssl_handler: Arc<SslHandler>,
}

impl FIXClient {
    pub fn new(config: DXTradeConfig) -> Result<Self> {
        let auth = DXTradeAuth::new(&config)?;
        let ssl_handler = SslHandler::new(config.ssl.clone())?;
        
        Ok(Self {
            config: Arc::new(config),
            auth: Arc::new(RwLock::new(auth)),
            session: Arc::new(RwLock::new(None)),
            ssl_handler: Arc::new(ssl_handler),
        })
    }
    
    pub async fn connect(&self) -> Result<()> {
        let ssl_handler_clone = SslHandler::new(self.config.ssl.clone())?;
        let session = FIXSession::new((*self.config).clone(), ssl_handler_clone)?;
        session.connect().await?;
        
        let mut session_guard = self.session.write().await;
        *session_guard = Some(session);
        
        Ok(())
    }
    
    pub async fn disconnect(&self) -> Result<()> {
        let session_guard = self.session.read().await;
        if let Some(ref session) = *session_guard {
            session.disconnect().await?;
        }
        
        drop(session_guard);
        let mut session_guard = self.session.write().await;
        *session_guard = None;
        
        Ok(())
    }
    
    pub async fn send_message(&self, message: FIXMessage) -> Result<()> {
        let session_guard = self.session.read().await;
        if let Some(ref session) = *session_guard {
            session.send_message(message).await
        } else {
            Err(DXTradeError::FixSessionError("No active session".to_string()))
        }
    }
    
    pub async fn get_session_state(&self) -> Option<SessionState> {
        let session_guard = self.session.read().await;
        if let Some(ref session) = *session_guard {
            Some(session.get_session_state().await)
        } else {
            None
        }
    }
    
    pub async fn is_connected(&self) -> bool {
        matches!(self.get_session_state().await, Some(SessionState::LoggedIn))
    }
}