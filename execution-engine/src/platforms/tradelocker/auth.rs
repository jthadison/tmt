use std::sync::Arc;
use tokio::sync::RwLock;
use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use reqwest::Client;
use tracing::{debug, error, info, warn};

use crate::utils::vault::VaultClient;
use super::{TradeLockerCredentials, TradeLockerEnvironment, TradeLockerError, Result};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthToken {
    pub access_token: String,
    pub refresh_token: String,
    pub expires_at: DateTime<Utc>,
    pub token_type: String,
}

impl AuthToken {
    pub fn is_expired(&self) -> bool {
        Utc::now() >= self.expires_at - Duration::minutes(5)
    }

    pub fn needs_refresh(&self) -> bool {
        Utc::now() >= self.expires_at - Duration::minutes(15)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct TokenRequest {
    grant_type: String,
    client_id: String,
    client_secret: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    refresh_token: Option<String>,
}

#[derive(Debug, Deserialize)]
struct TokenResponse {
    access_token: String,
    refresh_token: String,
    expires_in: i64,
    token_type: String,
}

pub struct TradeLockerAuth {
    credentials: Arc<RwLock<Vec<TradeLockerCredentials>>>,
    tokens: Arc<RwLock<Vec<(String, AuthToken)>>>,  // (account_id, token)
    client: Client,
    vault_client: Arc<VaultClient>,
}

impl TradeLockerAuth {
    pub async fn new(vault_client: Arc<VaultClient>) -> Result<Self> {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .map_err(|e| TradeLockerError::Connection(e.to_string()))?;

        Ok(Self {
            credentials: Arc::new(RwLock::new(Vec::new())),
            tokens: Arc::new(RwLock::new(Vec::new())),
            client,
            vault_client,
        })
    }

    pub async fn load_credentials(&self) -> Result<()> {
        info!("Loading TradeLocker credentials from Vault");
        
        let secrets = self.vault_client
            .list_secrets("tradelocker/accounts")
            .await
            .map_err(|e| TradeLockerError::Auth(format!("Failed to load credentials: {}", e)))?;

        let mut creds = Vec::new();
        for (account_id, secret_data) in secrets {
            if let Ok(cred) = serde_json::from_value::<TradeLockerCredentials>(secret_data) {
                creds.push(cred);
            } else {
                warn!("Failed to parse credentials for account: {}", account_id);
            }
        }

        let mut credentials = self.credentials.write().await;
        *credentials = creds;
        
        info!("Loaded {} TradeLocker account credentials", credentials.len());
        Ok(())
    }

    pub async fn authenticate(&self, account_id: &str) -> Result<AuthToken> {
        let credentials = self.credentials.read().await;
        let cred = credentials
            .iter()
            .find(|c| c.account_id == account_id)
            .ok_or_else(|| TradeLockerError::Auth(format!("No credentials for account: {}", account_id)))?
            .clone();
        drop(credentials);

        // Check if we have a valid token
        let tokens = self.tokens.read().await;
        if let Some((_, token)) = tokens.iter().find(|(id, _)| id == account_id) {
            if !token.is_expired() {
                debug!("Using cached token for account: {}", account_id);
                return Ok(token.clone());
            }
            
            if !token.needs_refresh() {
                debug!("Token still valid for account: {}", account_id);
                return Ok(token.clone());
            }
        }
        drop(tokens);

        // Need to get a new token or refresh existing
        self.refresh_or_authenticate(account_id, cred).await
    }

    async fn refresh_or_authenticate(
        &self, 
        account_id: &str, 
        cred: TradeLockerCredentials
    ) -> Result<AuthToken> {
        // Try to refresh first if we have a refresh token
        let tokens = self.tokens.read().await;
        let existing_token = tokens
            .iter()
            .find(|(id, _)| id == account_id)
            .map(|(_, t)| t.clone());
        drop(tokens);

        let token = if let Some(existing) = existing_token {
            if !existing.refresh_token.is_empty() {
                match self.refresh_token(&cred, &existing.refresh_token).await {
                    Ok(token) => token,
                    Err(e) => {
                        warn!("Token refresh failed, authenticating fresh: {}", e);
                        self.authenticate_fresh(&cred).await?
                    }
                }
            } else {
                self.authenticate_fresh(&cred).await?
            }
        } else {
            self.authenticate_fresh(&cred).await?
        };

        // Store the new token
        let mut tokens = self.tokens.write().await;
        tokens.retain(|(id, _)| id != account_id);
        tokens.push((account_id.to_string(), token.clone()));

        // Also persist to Vault
        self.persist_token(account_id, &token).await?;

        Ok(token)
    }

    async fn authenticate_fresh(&self, cred: &TradeLockerCredentials) -> Result<AuthToken> {
        info!("Authenticating fresh for account: {}", cred.account_id);

        let request = TokenRequest {
            grant_type: "client_credentials".to_string(),
            client_id: cred.api_key.clone(),
            client_secret: cred.api_secret.clone(),
            refresh_token: None,
        };

        let url = format!("{}/auth/token", cred.environment.base_url());
        
        let response = self.client
            .post(&url)
            .json(&request)
            .send()
            .await
            .map_err(|e| TradeLockerError::Connection(e.to_string()))?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            return Err(TradeLockerError::Auth(
                format!("Authentication failed: {} - {}", status, error_text)
            ));
        }

        let token_response: TokenResponse = response
            .json()
            .await
            .map_err(|e| TradeLockerError::Auth(format!("Failed to parse token response: {}", e)))?;

        Ok(AuthToken {
            access_token: token_response.access_token,
            refresh_token: token_response.refresh_token,
            expires_at: Utc::now() + Duration::seconds(token_response.expires_in),
            token_type: token_response.token_type,
        })
    }

    async fn refresh_token(&self, cred: &TradeLockerCredentials, refresh_token: &str) -> Result<AuthToken> {
        debug!("Refreshing token for account: {}", cred.account_id);

        let request = TokenRequest {
            grant_type: "refresh_token".to_string(),
            client_id: cred.api_key.clone(),
            client_secret: cred.api_secret.clone(),
            refresh_token: Some(refresh_token.to_string()),
        };

        let url = format!("{}/auth/token", cred.environment.base_url());
        
        let response = self.client
            .post(&url)
            .json(&request)
            .send()
            .await
            .map_err(|e| TradeLockerError::Connection(e.to_string()))?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            return Err(TradeLockerError::Auth(
                format!("Token refresh failed: {} - {}", status, error_text)
            ));
        }

        let token_response: TokenResponse = response
            .json()
            .await
            .map_err(|e| TradeLockerError::Auth(format!("Failed to parse refresh response: {}", e)))?;

        Ok(AuthToken {
            access_token: token_response.access_token,
            refresh_token: token_response.refresh_token,
            expires_at: Utc::now() + Duration::seconds(token_response.expires_in),
            token_type: token_response.token_type,
        })
    }

    async fn persist_token(&self, account_id: &str, token: &AuthToken) -> Result<()> {
        let key = format!("tradelocker/tokens/{}", account_id);
        
        self.vault_client
            .store_secret(&key, serde_json::to_value(token).unwrap())
            .await
            .map_err(|e| TradeLockerError::Auth(format!("Failed to persist token: {}", e)))?;

        Ok(())
    }

    pub async fn get_token(&self, account_id: &str) -> Result<String> {
        let token = self.authenticate(account_id).await?;
        Ok(token.access_token)
    }

    pub async fn invalidate_token(&self, account_id: &str) {
        let mut tokens = self.tokens.write().await;
        tokens.retain(|(id, _)| id != account_id);
        
        // Also remove from Vault
        let key = format!("tradelocker/tokens/{}", account_id);
        if let Err(e) = self.vault_client.delete_secret(&key).await {
            error!("Failed to delete token from Vault: {}", e);
        }
    }

    pub async fn refresh_all_tokens(&self) -> Result<()> {
        info!("Refreshing all TradeLocker tokens");
        
        let credentials = self.credentials.read().await.clone();
        
        for cred in credentials {
            if let Err(e) = self.authenticate(&cred.account_id).await {
                error!("Failed to refresh token for account {}: {}", cred.account_id, e);
            }
        }
        
        Ok(())
    }

    pub async fn monitor_token_expiry(&self) {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(300)); // Check every 5 minutes
        
        loop {
            interval.tick().await;
            
            let tokens = self.tokens.read().await.clone();
            for (account_id, token) in tokens {
                if token.needs_refresh() {
                    info!("Token needs refresh for account: {}", account_id);
                    if let Err(e) = self.authenticate(&account_id).await {
                        error!("Failed to refresh token for account {}: {}", account_id, e);
                    }
                }
            }
        }
    }
}