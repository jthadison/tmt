use super::config::DXTradeConfig;
use super::error::{DXTradeError, Result};
use aes_gcm::{Aes256Gcm, Nonce, KeyInit};
use aes_gcm::aead::Aead;
use base64::{Engine as _, engine::general_purpose};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use zeroize::{Zeroize, ZeroizeOnDrop};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DXTradeAuth {
    sender_comp_id: String,
    target_comp_id: String,
    sender_sub_id: Option<String>,
    target_sub_id: Option<String>,
    ssl_cert_path: String,
    ssl_key_path: String,
    encrypted_credentials: Option<String>,
    session_token: Option<String>,
    token_expires_at: Option<DateTime<Utc>>,
}

#[derive(Serialize, Deserialize)]
pub struct EncryptedCredentials {
    pub sender_comp_id: String,
    pub target_comp_id: String,
    pub sender_sub_id: Option<String>,
    pub target_sub_id: Option<String>,
    // Note: HashMap doesn't support Zeroize derive, needs manual implementation
    pub additional_fields: HashMap<String, String>,
}

impl Zeroize for EncryptedCredentials {
    fn zeroize(&mut self) {
        self.sender_comp_id.zeroize();
        self.target_comp_id.zeroize();
        if let Some(ref mut sender_sub) = self.sender_sub_id {
            sender_sub.zeroize();
        }
        if let Some(ref mut target_sub) = self.target_sub_id {
            target_sub.zeroize();
        }
        // Manually zeroize HashMap contents
        for (_key, value) in self.additional_fields.iter_mut() {
            value.zeroize();
        }
        self.additional_fields.clear();
    }
}

// Secure wrapper for sensitive strings that automatically zeroize on drop
#[derive(ZeroizeOnDrop)]
pub struct SecureString(String);

impl SecureString {
    pub fn new(value: String) -> Self {
        Self(value)
    }
    
    pub fn as_str(&self) -> &str {
        &self.0
    }
    
    pub fn as_bytes(&self) -> &[u8] {
        self.0.as_bytes()
    }
}

impl From<String> for SecureString {
    fn from(value: String) -> Self {
        Self(value)
    }
}

impl std::fmt::Debug for SecureString {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("[REDACTED]")
    }
}

// Secure credential holder that zeroizes on drop
#[derive(ZeroizeOnDrop)]
pub struct SecureCredentials {
    pub cert_data: Vec<u8>,
    pub key_data: Vec<u8>,
    encryption_key: [u8; 32],
}

#[derive(Debug)]
pub struct AuthContext {
    pub sender_comp_id: String,
    pub target_comp_id: String,
    pub sender_sub_id: Option<String>,
    pub target_sub_id: Option<String>,
    pub session_token: Option<SecureString>,
    pub ssl_cert_data: Vec<u8>,
    pub ssl_key_data: Vec<u8>,
    pub authenticated_at: DateTime<Utc>,
    pub expires_at: Option<DateTime<Utc>>,
}

impl Zeroize for AuthContext {
    fn zeroize(&mut self) {
        self.sender_comp_id.zeroize();
        self.target_comp_id.zeroize();
        if let Some(ref mut sender_sub) = self.sender_sub_id {
            sender_sub.zeroize();
        }
        if let Some(ref mut target_sub) = self.target_sub_id {
            target_sub.zeroize();
        }
        // session_token (SecureString) will zeroize itself on drop
        self.ssl_cert_data.zeroize();
        self.ssl_key_data.zeroize();
        // DateTime fields don't contain sensitive data that needs zeroization
    }
}

impl Drop for AuthContext {
    fn drop(&mut self) {
        self.zeroize();
        tracing::debug!("AuthContext securely zeroized on drop");
    }
}

impl DXTradeAuth {
    pub fn new(config: &DXTradeConfig) -> Result<Self> {
        let ssl_cert_path = config.ssl.cert_file_path.clone();
        let ssl_key_path = config.ssl.key_file_path.clone();
        
        if !std::path::Path::new(&ssl_cert_path).exists() {
            return Err(DXTradeError::AuthenticationError(
                format!("SSL certificate file not found: {}", ssl_cert_path)
            ));
        }
        
        if !std::path::Path::new(&ssl_key_path).exists() {
            return Err(DXTradeError::AuthenticationError(
                format!("SSL key file not found: {}", ssl_key_path)
            ));
        }
        
        Ok(Self {
            sender_comp_id: config.credentials.sender_comp_id.clone(),
            target_comp_id: config.credentials.target_comp_id.clone(),
            sender_sub_id: config.credentials.sender_sub_id.clone(),
            target_sub_id: config.credentials.target_sub_id.clone(),
            ssl_cert_path,
            ssl_key_path,
            encrypted_credentials: None,
            session_token: None,
            token_expires_at: None,
        })
    }
    
    pub fn encrypt_credentials(&mut self, encryption_key: &[u8; 32]) -> Result<()> {
        let credentials = EncryptedCredentials {
            sender_comp_id: self.sender_comp_id.clone(),
            target_comp_id: self.target_comp_id.clone(),
            sender_sub_id: self.sender_sub_id.clone(),
            target_sub_id: self.target_sub_id.clone(),
            additional_fields: HashMap::new(),
        };
        
        let mut credentials_json = serde_json::to_string(&credentials)
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Failed to serialize credentials: {}", e)
            ))?;
        
        let cipher = Aes256Gcm::new_from_slice(encryption_key)
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Failed to create cipher: {}", e)
            ))?;
            
        // Use secure random nonce in production
        let nonce_bytes = [0u8; 12]; // TODO: Use cryptographically secure random nonce
        let nonce = Nonce::from_slice(&nonce_bytes);
        
        let encrypted_data = cipher.encrypt(nonce, credentials_json.as_bytes())
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Failed to encrypt credentials: {}", e)
            ))?;
        
        // Zeroize the plaintext JSON before dropping
        credentials_json.zeroize();
        
        self.encrypted_credentials = Some(general_purpose::STANDARD.encode(&encrypted_data));
        
        Ok(())
    }
    
    pub fn decrypt_credentials(&self, encryption_key: &[u8; 32]) -> Result<EncryptedCredentials> {
        let encrypted_data = self.encrypted_credentials.as_ref()
            .ok_or_else(|| DXTradeError::AuthenticationError(
                "No encrypted credentials available".to_string()
            ))?;
        
        let mut encrypted_bytes = general_purpose::STANDARD.decode(encrypted_data)
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Failed to decode encrypted credentials: {}", e)
            ))?;
        
        let cipher = Aes256Gcm::new_from_slice(encryption_key)
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Failed to create cipher: {}", e)
            ))?;
        let nonce_bytes = [0u8; 12]; // Must match encryption nonce
        let nonce = Nonce::from_slice(&nonce_bytes);
        
        let mut decrypted_data = cipher.decrypt(nonce, encrypted_bytes.as_ref())
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Failed to decrypt credentials: {}", e)
            ))?;
        
        // Zeroize encrypted data
        encrypted_bytes.zeroize();
        
        let mut credentials_json = String::from_utf8(decrypted_data.clone())
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Invalid UTF-8 in decrypted credentials: {}", e)
            ))?;
        
        // Zeroize the raw decrypted data
        decrypted_data.zeroize();
        
        let credentials = serde_json::from_str(&credentials_json)
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Failed to deserialize credentials: {}", e)
            ))?;
            
        // Zeroize the JSON string
        credentials_json.zeroize();
        
        Ok(credentials)
    }
    
    pub fn load_ssl_certificate(&self) -> Result<Vec<u8>> {
        fs::read(&self.ssl_cert_path)
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Failed to read SSL certificate: {}", e)
            ))
    }
    
    pub fn load_ssl_key(&self) -> Result<Vec<u8>> {
        fs::read(&self.ssl_key_path)
            .map_err(|e| DXTradeError::AuthenticationError(
                format!("Failed to read SSL private key: {}", e)
            ))
    }
    
    pub fn validate_ssl_files(&self) -> Result<()> {
        let cert_data = self.load_ssl_certificate()?;
        let key_data = self.load_ssl_key()?;
        
        if cert_data.is_empty() {
            return Err(DXTradeError::AuthenticationError(
                "SSL certificate file is empty".to_string()
            ));
        }
        
        if key_data.is_empty() {
            return Err(DXTradeError::AuthenticationError(
                "SSL private key file is empty".to_string()
            ));
        }
        
        let cert_str = String::from_utf8_lossy(&cert_data);
        if !cert_str.contains("-----BEGIN CERTIFICATE-----") {
            return Err(DXTradeError::AuthenticationError(
                "Invalid SSL certificate format".to_string()
            ));
        }
        
        let key_str = String::from_utf8_lossy(&key_data);
        if !key_str.contains("-----BEGIN PRIVATE KEY-----") && 
           !key_str.contains("-----BEGIN RSA PRIVATE KEY-----") {
            return Err(DXTradeError::AuthenticationError(
                "Invalid SSL private key format".to_string()
            ));
        }
        
        Ok(())
    }
    
    pub fn create_auth_context(&self) -> Result<AuthContext> {
        self.validate_ssl_files()?;
        
        let ssl_cert_data = self.load_ssl_certificate()?;
        let ssl_key_data = self.load_ssl_key()?;
        
        let secure_token = self.session_token.as_ref()
            .map(|token| SecureString::new(token.clone()));
        
        Ok(AuthContext {
            sender_comp_id: self.sender_comp_id.clone(),
            target_comp_id: self.target_comp_id.clone(),
            sender_sub_id: self.sender_sub_id.clone(),
            target_sub_id: self.target_sub_id.clone(),
            session_token: secure_token,
            ssl_cert_data,
            ssl_key_data,
            authenticated_at: Utc::now(),
            expires_at: self.token_expires_at,
        })
    }
    
    pub fn is_token_expired(&self) -> bool {
        if let Some(expires_at) = self.token_expires_at {
            Utc::now() >= expires_at
        } else {
            false
        }
    }
    
    pub fn set_session_token(&mut self, token: String, expires_at: DateTime<Utc>) {
        self.session_token = Some(token);
        self.token_expires_at = Some(expires_at);
    }
    
    pub fn clear_session_token(&mut self) {
        // Explicitly zeroize sensitive token data
        if let Some(ref mut token) = self.session_token {
            token.zeroize();
        }
        self.session_token = None;
        self.token_expires_at = None;
    }
    
    /// Securely clear all sensitive authentication data from memory
    pub fn zeroize_credentials(&mut self) {
        // Clear session token securely
        self.clear_session_token();
        
        // Clear encrypted credentials if present
        if let Some(ref mut encrypted) = self.encrypted_credentials {
            encrypted.zeroize();
        }
        self.encrypted_credentials = None;
        
        tracing::debug!("Credentials securely zeroized from memory");
    }
    
    pub fn get_sender_comp_id(&self) -> &str {
        &self.sender_comp_id
    }
    
    pub fn get_target_comp_id(&self) -> &str {
        &self.target_comp_id
    }
    
    pub fn get_sender_sub_id(&self) -> Option<&str> {
        self.sender_sub_id.as_deref()
    }
    
    pub fn get_target_sub_id(&self) -> Option<&str> {
        self.target_sub_id.as_deref()
    }
    
    pub fn get_session_token(&self) -> Option<&str> {
        self.session_token.as_deref()
    }
    
    pub fn get_ssl_cert_path(&self) -> &str {
        &self.ssl_cert_path
    }
    
    pub fn get_ssl_key_path(&self) -> &str {
        &self.ssl_key_path
    }
    
    pub fn create_identity_string(&self) -> String {
        let mut identity = format!("{}:{}", self.sender_comp_id, self.target_comp_id);
        
        if let Some(sender_sub_id) = &self.sender_sub_id {
            identity.push_str(&format!(":{}", sender_sub_id));
        }
        
        if let Some(target_sub_id) = &self.target_sub_id {
            identity.push_str(&format!(":{}", target_sub_id));
        }
        
        identity
    }
    
    pub fn generate_encryption_key() -> [u8; 32] {
        use rand::Rng;
        
        let mut key = [0u8; 32];
        rand::thread_rng().fill(&mut key);
        key
    }
}

impl AuthContext {
    pub fn is_expired(&self) -> bool {
        if let Some(expires_at) = self.expires_at {
            Utc::now() >= expires_at
        } else {
            false
        }
    }
    
    pub fn time_until_expiry(&self) -> Option<chrono::Duration> {
        self.expires_at.map(|exp| exp.signed_duration_since(Utc::now()))
    }
    
    pub fn is_about_to_expire(&self, threshold_minutes: i64) -> bool {
        if let Some(time_left) = self.time_until_expiry() {
            time_left.num_minutes() <= threshold_minutes
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn create_test_config() -> DXTradeConfig {
        let mut cert_file = NamedTempFile::new().unwrap();
        let mut key_file = NamedTempFile::new().unwrap();
        
        cert_file.write_all(b"-----BEGIN CERTIFICATE-----\ntest cert data\n-----END CERTIFICATE-----").unwrap();
        key_file.write_all(b"-----BEGIN PRIVATE KEY-----\ntest key data\n-----END PRIVATE KEY-----").unwrap();
        
        let mut config = DXTradeConfig::default();
        config.ssl.cert_file_path = cert_file.path().to_string_lossy().to_string();
        config.ssl.key_file_path = key_file.path().to_string_lossy().to_string();
        config.credentials.sender_comp_id = "TEST_SENDER".to_string();
        config.credentials.target_comp_id = "TEST_TARGET".to_string();
        
        std::mem::forget(cert_file);
        std::mem::forget(key_file);
        
        config
    }

    #[test]
    fn test_auth_creation() {
        let config = create_test_config();
        let auth = DXTradeAuth::new(&config).unwrap();
        
        assert_eq!(auth.get_sender_comp_id(), "TEST_SENDER");
        assert_eq!(auth.get_target_comp_id(), "TEST_TARGET");
    }

    #[test]
    fn test_identity_string_creation() {
        let config = create_test_config();
        let auth = DXTradeAuth::new(&config).unwrap();
        
        let identity = auth.create_identity_string();
        assert_eq!(identity, "TEST_SENDER:TEST_TARGET");
    }

    #[test]
    fn test_token_expiry() {
        let config = create_test_config();
        let mut auth = DXTradeAuth::new(&config).unwrap();
        
        assert!(!auth.is_token_expired());
        
        let past_time = Utc::now() - chrono::Duration::hours(1);
        auth.set_session_token("test_token".to_string(), past_time);
        
        assert!(auth.is_token_expired());
    }

    #[test]
    fn test_encryption_key_generation() {
        let key1 = DXTradeAuth::generate_encryption_key();
        let key2 = DXTradeAuth::generate_encryption_key();
        
        // Keys should be different (cryptographically random)
        assert_ne!(key1, key2);
        assert_eq!(key1.len(), 32);
        assert_eq!(key2.len(), 32);
        
        // Verify keys are not all zeros (properly generated)
        assert!(key1.iter().any(|&b| b != 0));
        assert!(key2.iter().any(|&b| b != 0));
    }
}