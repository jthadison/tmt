use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Key, Nonce,
};
use anyhow::{anyhow, Result};
use base64::{engine::general_purpose, Engine as _};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use zeroize::Zeroize;

/// Encrypted storage for sensitive trading parameters
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedTradingParams {
    /// Encrypted API keys and credentials
    pub encrypted_credentials: HashMap<String, EncryptedValue>,
    /// Encrypted account identifiers
    pub encrypted_account_ids: HashMap<String, EncryptedValue>,
    /// Encrypted position sizes and limits
    pub encrypted_limits: HashMap<String, EncryptedValue>,
    /// Encrypted prop firm specific parameters
    pub encrypted_prop_firm_params: HashMap<String, EncryptedValue>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedValue {
    /// Base64 encoded encrypted data
    pub data: String,
    /// Base64 encoded nonce
    pub nonce: String,
    /// Timestamp when encrypted
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

impl Zeroize for EncryptedValue {
    fn zeroize(&mut self) {
        self.data.zeroize();
        self.nonce.zeroize();
    }
}

impl Drop for EncryptedValue {
    fn drop(&mut self) {
        self.zeroize();
    }
}

/// Secure key derivation and management
pub struct EncryptionManager {
    /// Master key for encryption/decryption
    cipher: Aes256Gcm,
    /// Key ID for rotation tracking
    key_id: String,
}

impl Drop for EncryptionManager {
    fn drop(&mut self) {
        // Zeroize sensitive data on drop
        self.key_id.zeroize();
        // Note: Aes256Gcm doesn't implement Zeroize, so we can't clear it directly
        // This is a limitation of the aes-gcm crate
    }
}

impl EncryptionManager {
    /// Create new encryption manager with random key
    pub fn new() -> Result<Self> {
        let key = Aes256Gcm::generate_key(OsRng);
        let cipher = Aes256Gcm::new(&key);
        let key_id = uuid::Uuid::new_v4().to_string();

        Ok(Self { cipher, key_id })
    }

    /// Create encryption manager from existing key
    pub fn from_key(key_bytes: &[u8], key_id: String) -> Result<Self> {
        if key_bytes.len() != 32 {
            return Err(anyhow!("Key must be exactly 32 bytes"));
        }

        let key = Key::<Aes256Gcm>::from_slice(key_bytes);
        let cipher = Aes256Gcm::new(key);

        Ok(Self { cipher, key_id })
    }

    /// Encrypt sensitive string data
    pub fn encrypt_string(&self, plaintext: &str) -> Result<EncryptedValue> {
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
        let ciphertext = self
            .cipher
            .encrypt(&nonce, plaintext.as_bytes())
            .map_err(|e| anyhow!("Encryption failed: {}", e))?;

        let encrypted_value = EncryptedValue {
            data: general_purpose::STANDARD.encode(ciphertext),
            nonce: general_purpose::STANDARD.encode(nonce),
            timestamp: chrono::Utc::now(),
        };

        Ok(encrypted_value)
    }

    /// Decrypt sensitive string data
    pub fn decrypt_string(&self, encrypted: &EncryptedValue) -> Result<String> {
        let ciphertext = general_purpose::STANDARD
            .decode(&encrypted.data)
            .map_err(|e| anyhow!("Failed to decode ciphertext: {}", e))?;

        let nonce_bytes = general_purpose::STANDARD
            .decode(&encrypted.nonce)
            .map_err(|e| anyhow!("Failed to decode nonce: {}", e))?;

        if nonce_bytes.len() != 12 {
            return Err(anyhow!("Invalid nonce length"));
        }

        let nonce = Nonce::from_slice(&nonce_bytes);
        let plaintext = self
            .cipher
            .decrypt(nonce, ciphertext.as_slice())
            .map_err(|e| anyhow!("Decryption failed: {}", e))?;

        String::from_utf8(plaintext).map_err(|e| anyhow!("Invalid UTF-8 in decrypted data: {}", e))
    }

    /// Get current key ID
    pub fn key_id(&self) -> &str {
        &self.key_id
    }
}

/// Secure parameter store with encryption
pub struct SecureParameterStore {
    encryption_manager: EncryptionManager,
    parameters: EncryptedTradingParams,
}

impl Drop for SecureParameterStore {
    fn drop(&mut self) {
        // Clear sensitive parameters on drop
        for (_, mut value) in self.parameters.encrypted_credentials.drain() {
            value.zeroize();
        }
        for (_, mut value) in self.parameters.encrypted_account_ids.drain() {
            value.zeroize();
        }
        for (_, mut value) in self.parameters.encrypted_limits.drain() {
            value.zeroize();
        }
        for (_, mut value) in self.parameters.encrypted_prop_firm_params.drain() {
            value.zeroize();
        }
    }
}

impl SecureParameterStore {
    /// Create new secure parameter store
    pub fn new() -> Result<Self> {
        Ok(Self {
            encryption_manager: EncryptionManager::new()?,
            parameters: EncryptedTradingParams {
                encrypted_credentials: HashMap::new(),
                encrypted_account_ids: HashMap::new(),
                encrypted_limits: HashMap::new(),
                encrypted_prop_firm_params: HashMap::new(),
            },
        })
    }

    /// Store API key securely
    pub fn store_api_key(&mut self, platform: &str, api_key: &str) -> Result<()> {
        let encrypted = self.encryption_manager.encrypt_string(api_key)?;
        self.parameters
            .encrypted_credentials
            .insert(format!("{}_api_key", platform), encrypted);
        Ok(())
    }

    /// Retrieve API key securely
    pub fn get_api_key(&self, platform: &str) -> Result<String> {
        let key = format!("{}_api_key", platform);
        let encrypted = self
            .parameters
            .encrypted_credentials
            .get(&key)
            .ok_or_else(|| anyhow!("API key not found for platform: {}", platform))?;

        self.encryption_manager.decrypt_string(encrypted)
    }

    /// Store account secret securely
    pub fn store_account_secret(&mut self, account_name: &str, secret: &str) -> Result<()> {
        let encrypted = self.encryption_manager.encrypt_string(secret)?;
        self.parameters
            .encrypted_account_ids
            .insert(format!("{}_secret", account_name), encrypted);
        Ok(())
    }

    /// Retrieve account secret securely  
    pub fn get_account_secret(&self, account_name: &str) -> Result<String> {
        let key = format!("{}_secret", account_name);
        let encrypted = self
            .parameters
            .encrypted_account_ids
            .get(&key)
            .ok_or_else(|| anyhow!("Account secret not found for: {}", account_name))?;

        self.encryption_manager.decrypt_string(encrypted)
    }

    /// Store risk limit securely
    pub fn store_risk_limit(&mut self, limit_type: &str, value: &str) -> Result<()> {
        let encrypted = self.encryption_manager.encrypt_string(value)?;
        self.parameters
            .encrypted_limits
            .insert(limit_type.to_string(), encrypted);
        Ok(())
    }

    /// Retrieve risk limit securely
    pub fn get_risk_limit(&self, limit_type: &str) -> Result<String> {
        let encrypted = self
            .parameters
            .encrypted_limits
            .get(limit_type)
            .ok_or_else(|| anyhow!("Risk limit not found: {}", limit_type))?;

        self.encryption_manager.decrypt_string(encrypted)
    }

    /// Store prop firm specific parameter
    pub fn store_prop_firm_param(&mut self, firm: &str, param: &str, value: &str) -> Result<()> {
        let encrypted = self.encryption_manager.encrypt_string(value)?;
        let key = format!("{}_{}", firm, param);
        self.parameters
            .encrypted_prop_firm_params
            .insert(key, encrypted);
        Ok(())
    }

    /// Retrieve prop firm specific parameter
    pub fn get_prop_firm_param(&self, firm: &str, param: &str) -> Result<String> {
        let key = format!("{}_{}", firm, param);
        let encrypted = self
            .parameters
            .encrypted_prop_firm_params
            .get(&key)
            .ok_or_else(|| anyhow!("Prop firm parameter not found: {}_{}", firm, param))?;

        self.encryption_manager.decrypt_string(encrypted)
    }

    /// Export encrypted parameters for storage
    pub fn export_encrypted(&self) -> Result<String> {
        let json = serde_json::to_string_pretty(&self.parameters)?;
        Ok(json)
    }

    /// Import encrypted parameters from storage
    pub fn import_encrypted(&mut self, encrypted_data: &str) -> Result<()> {
        let params: EncryptedTradingParams = serde_json::from_str(encrypted_data)?;
        self.parameters = params;
        Ok(())
    }

    /// Validate parameter age and recommend refresh
    pub fn audit_parameter_age(&self) -> Vec<String> {
        let mut warnings = Vec::new();
        let now = chrono::Utc::now();
        let max_age = chrono::Duration::days(90); // 90 days max age

        // Check all encrypted values for age
        for (key, value) in &self.parameters.encrypted_credentials {
            if now - value.timestamp > max_age {
                warnings.push(format!("Credential '{}' is older than 90 days", key));
            }
        }

        for (key, value) in &self.parameters.encrypted_account_ids {
            if now - value.timestamp > max_age {
                warnings.push(format!("Account ID '{}' is older than 90 days", key));
            }
        }

        for (key, value) in &self.parameters.encrypted_limits {
            if now - value.timestamp > max_age {
                warnings.push(format!("Risk limit '{}' is older than 90 days", key));
            }
        }

        for (key, value) in &self.parameters.encrypted_prop_firm_params {
            if now - value.timestamp > max_age {
                warnings.push(format!("Prop firm param '{}' is older than 90 days", key));
            }
        }

        warnings
    }
}

impl Default for SecureParameterStore {
    fn default() -> Self {
        Self::new().expect("Failed to create default SecureParameterStore")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encryption_round_trip() {
        let manager = EncryptionManager::new().unwrap();
        let plaintext = "super_secret_api_key_12345";

        let encrypted = manager.encrypt_string(plaintext).unwrap();
        let decrypted = manager.decrypt_string(&encrypted).unwrap();

        assert_eq!(plaintext, decrypted);
    }

    #[test]
    fn test_secure_parameter_store() {
        let mut store = SecureParameterStore::new().unwrap();

        // Store and retrieve API key
        store.store_api_key("metatrader", "secret_key_123").unwrap();
        let retrieved = store.get_api_key("metatrader").unwrap();
        assert_eq!("secret_key_123", retrieved);

        // Store and retrieve account secret
        store
            .store_account_secret("account1", "account_secret_456")
            .unwrap();
        let retrieved = store.get_account_secret("account1").unwrap();
        assert_eq!("account_secret_456", retrieved);

        // Store and retrieve risk limit
        store.store_risk_limit("max_position", "100000").unwrap();
        let retrieved = store.get_risk_limit("max_position").unwrap();
        assert_eq!("100000", retrieved);
    }

    #[test]
    fn test_export_import() {
        let mut store1 = SecureParameterStore::new().unwrap();
        store1.store_api_key("test", "secret123").unwrap();

        let exported = store1.export_encrypted().unwrap();

        let mut store2 = SecureParameterStore::new().unwrap();
        store2.import_encrypted(&exported).unwrap();

        // Should fail because different encryption keys
        assert!(store2.get_api_key("test").is_err());
    }

    #[test]
    fn test_parameter_age_audit() {
        let store = SecureParameterStore::new().unwrap();
        let warnings = store.audit_parameter_age();
        assert!(warnings.is_empty()); // New store should have no old parameters
    }
}
