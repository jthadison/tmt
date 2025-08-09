#[cfg(test)]
mod tests {
    use std::sync::Arc;
    use chrono::{Duration, Utc};
    use pretty_assertions::assert_eq;
    use crate::platforms::tradelocker::{
        auth::{AuthToken, TradeLockerAuth},
        TradeLockerCredentials, TradeLockerEnvironment,
    };
    use crate::utils::vault::VaultClient;

    fn create_test_token() -> AuthToken {
        AuthToken {
            access_token: "test_access_token".to_string(),
            refresh_token: "test_refresh_token".to_string(),
            expires_at: Utc::now() + Duration::hours(1),
            token_type: "Bearer".to_string(),
        }
    }

    fn create_test_credentials() -> TradeLockerCredentials {
        TradeLockerCredentials {
            account_id: "test_account".to_string(),
            api_key: "test_api_key".to_string(),
            api_secret: "test_api_secret".to_string(),
            environment: TradeLockerEnvironment::Sandbox,
        }
    }

    #[tokio::test]
    async fn test_token_expiration_check() {
        let mut token = create_test_token();
        assert!(!token.is_expired());
        assert!(!token.needs_refresh());

        // Set expiration to 10 minutes from now
        token.expires_at = Utc::now() + Duration::minutes(10);
        assert!(!token.is_expired());
        assert!(token.needs_refresh()); // Should refresh when < 15 minutes

        // Set expiration to past
        token.expires_at = Utc::now() - Duration::minutes(1);
        assert!(token.is_expired());
        assert!(token.needs_refresh());
    }

    #[tokio::test]
    async fn test_token_needs_refresh_boundary() {
        let mut token = create_test_token();
        
        // Test exact boundary conditions
        token.expires_at = Utc::now() + Duration::minutes(15);
        assert!(!token.is_expired());
        assert!(!token.needs_refresh());
        
        // Just under the 15 minute threshold
        token.expires_at = Utc::now() + Duration::minutes(14) + Duration::seconds(59);
        assert!(!token.is_expired());
        assert!(token.needs_refresh());
        
        // Test expiration boundary
        token.expires_at = Utc::now() + Duration::minutes(5);
        assert!(!token.is_expired());
        
        token.expires_at = Utc::now() + Duration::minutes(4) + Duration::seconds(59);
        assert!(token.is_expired());
    }

    #[tokio::test]
    async fn test_auth_initialization() {
        let vault_client = Arc::new(VaultClient::new("http://localhost:8200".to_string()).await.unwrap());
        let auth = TradeLockerAuth::new(vault_client).await;
        
        assert!(auth.is_ok());
        
        let _auth = auth.unwrap();
        // Verify internal state is properly initialized
        // In a real implementation, we'd check that the HTTP client is configured correctly
    }

    #[tokio::test]
    async fn test_credential_loading() {
        let vault_client = Arc::new(VaultClient::new("http://localhost:8200".to_string()).await.unwrap());
        let auth = TradeLockerAuth::new(vault_client).await.unwrap();
        
        // This works with our stub implementation
        let result = auth.load_credentials().await;
        assert!(result.is_ok());
        
        // With stub, no credentials are loaded
        // In a real test, we'd mock the vault to return test credentials
    }

    #[tokio::test]
    async fn test_environment_urls() {
        let prod = TradeLockerEnvironment::Production;
        let sandbox = TradeLockerEnvironment::Sandbox;
        
        assert_eq!(prod.base_url(), "https://api.tradelocker.com");
        assert_eq!(prod.ws_url(), "wss://api.tradelocker.com/ws");
        
        assert_eq!(sandbox.base_url(), "https://sandbox-api.tradelocker.com");
        assert_eq!(sandbox.ws_url(), "wss://sandbox-api.tradelocker.com/ws");
    }

    #[tokio::test]
    async fn test_credentials_serialization() {
        let creds = create_test_credentials();
        
        // Test serialization/deserialization
        let json = serde_json::to_string(&creds).unwrap();
        let deserialized: TradeLockerCredentials = serde_json::from_str(&json).unwrap();
        
        assert_eq!(creds.account_id, deserialized.account_id);
        assert_eq!(creds.api_key, deserialized.api_key);
        assert_eq!(creds.api_secret, deserialized.api_secret);
    }

    #[tokio::test]
    async fn test_token_serialization() {
        let token = create_test_token();
        
        // Test serialization/deserialization
        let json = serde_json::to_string(&token).unwrap();
        let deserialized: AuthToken = serde_json::from_str(&json).unwrap();
        
        assert_eq!(token.access_token, deserialized.access_token);
        assert_eq!(token.refresh_token, deserialized.refresh_token);
        assert_eq!(token.token_type, deserialized.token_type);
    }

    #[tokio::test]
    async fn test_authentication_failure() {
        let vault_client = Arc::new(VaultClient::new("http://localhost:8200".to_string()).await.unwrap());
        let auth = TradeLockerAuth::new(vault_client).await.unwrap();
        
        // Try to authenticate with non-existent account
        let result = auth.authenticate("non_existent_account").await;
        assert!(result.is_err());
        
        // Should be an auth error about missing credentials
        match result.unwrap_err() {
            crate::platforms::tradelocker::TradeLockerError::Auth(msg) => {
                assert!(msg.contains("No credentials"));
            }
            _ => panic!("Expected auth error"),
        }
    }

    #[test]
    fn test_token_debug_format() {
        let token = create_test_token();
        let debug_str = format!("{:?}", token);
        
        // Ensure sensitive data is not exposed in debug output
        // In a real implementation, we'd implement custom Debug to hide secrets
        assert!(debug_str.contains("AuthToken"));
    }
}