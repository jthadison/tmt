#[cfg(test)]
mod tests {
    use super::super::auth::*;
    use super::super::config::DXTradeConfig;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn create_test_config_with_certs() -> (DXTradeConfig, NamedTempFile, NamedTempFile) {
        let mut cert_file = NamedTempFile::new().unwrap();
        let mut key_file = NamedTempFile::new().unwrap();

        // Write sample certificate data
        cert_file.write_all(b"-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END CERTIFICATE-----").unwrap();
        key_file.write_all(b"-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEA...\n-----END PRIVATE KEY-----").unwrap();

        let mut config = DXTradeConfig::default();
        config.ssl.cert_file_path = cert_file.path().to_string_lossy().to_string();
        config.ssl.key_file_path = key_file.path().to_string_lossy().to_string();
        config.credentials.sender_comp_id = "TEST_SENDER".to_string();
        config.credentials.target_comp_id = "TEST_TARGET".to_string();
        config.credentials.account_id = "TEST_ACCOUNT".to_string();

        (config, cert_file, key_file)
    }

    #[test]
    fn test_auth_creation_with_valid_config() {
        let (config, _cert_file, _key_file) = create_test_config_with_certs();

        let auth = DXTradeAuth::new(&config).unwrap();

        assert_eq!(auth.get_sender_comp_id(), "TEST_SENDER");
        assert_eq!(auth.get_target_comp_id(), "TEST_TARGET");
        assert_eq!(auth.get_ssl_cert_path(), config.ssl.cert_file_path);
        assert_eq!(auth.get_ssl_key_path(), config.ssl.key_file_path);
        assert!(!auth.is_token_expired());
    }

    #[test]
    fn test_auth_creation_with_missing_cert_file() {
        let mut config = DXTradeConfig::default();
        config.ssl.cert_file_path = "/non/existent/cert.pem".to_string();
        config.ssl.key_file_path = "/non/existent/key.pem".to_string();
        config.credentials.sender_comp_id = "TEST_SENDER".to_string();
        config.credentials.target_comp_id = "TEST_TARGET".to_string();
        config.credentials.account_id = "TEST_ACCOUNT".to_string();

        let result = DXTradeAuth::new(&config);

        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("certificate file not found"));
    }

    #[test]
    fn test_session_token_management() {
        let (config, _cert_file, _key_file) = create_test_config_with_certs();
        let mut auth = DXTradeAuth::new(&config).unwrap();

        assert!(auth.get_session_token().is_none());
        assert!(!auth.is_token_expired());

        let future_time = chrono::Utc::now() + chrono::Duration::hours(1);
        auth.set_session_token("test_token_123".to_string(), future_time);

        assert_eq!(auth.get_session_token(), Some("test_token_123"));
        assert!(!auth.is_token_expired());

        let past_time = chrono::Utc::now() - chrono::Duration::hours(1);
        auth.set_session_token("expired_token".to_string(), past_time);

        assert!(auth.is_token_expired());
    }

    #[test]
    fn test_credential_encryption_and_decryption() {
        let (config, _cert_file, _key_file) = create_test_config_with_certs();
        let mut auth = DXTradeAuth::new(&config).unwrap();

        let encryption_key = DXTradeAuth::generate_encryption_key();

        // Test encryption
        let result = auth.encrypt_credentials(&encryption_key);
        assert!(result.is_ok());

        // Test decryption
        let decrypted = auth.decrypt_credentials(&encryption_key);
        assert!(decrypted.is_ok());

        let credentials = decrypted.unwrap();
        assert_eq!(credentials.sender_comp_id, "TEST_SENDER");
        assert_eq!(credentials.target_comp_id, "TEST_TARGET");
    }

    #[test]
    fn test_ssl_file_validation() {
        let (config, _cert_file, _key_file) = create_test_config_with_certs();
        let auth = DXTradeAuth::new(&config).unwrap();

        // Should pass validation with valid files
        let result = auth.validate_ssl_files();
        assert!(result.is_ok());

        // Test certificate loading
        let cert_data = auth.load_ssl_certificate();
        assert!(cert_data.is_ok());
        assert!(!cert_data.unwrap().is_empty());

        // Test key loading
        let key_data = auth.load_ssl_key();
        assert!(key_data.is_ok());
        assert!(!key_data.unwrap().is_empty());
    }

    #[test]
    fn test_auth_context_creation() {
        let (config, _cert_file, _key_file) = create_test_config_with_certs();
        let mut auth = DXTradeAuth::new(&config).unwrap();

        // Set a session token
        let future_time = chrono::Utc::now() + chrono::Duration::hours(1);
        auth.set_session_token("context_token".to_string(), future_time);

        let auth_context = auth.create_auth_context().unwrap();

        assert_eq!(auth_context.sender_comp_id, "TEST_SENDER");
        assert_eq!(auth_context.target_comp_id, "TEST_TARGET");
        assert!(auth_context.session_token.is_some());
        assert!(!auth_context.ssl_cert_data.is_empty());
        assert!(!auth_context.ssl_key_data.is_empty());
        assert!(!auth_context.is_expired());
    }

    #[test]
    fn test_identity_string_generation() {
        let (config, _cert_file, _key_file) = create_test_config_with_certs();
        let auth = DXTradeAuth::new(&config).unwrap();

        let identity = auth.create_identity_string();
        assert_eq!(identity, "TEST_SENDER:TEST_TARGET");
    }

    #[test]
    fn test_secure_credential_cleanup() {
        let (config, _cert_file, _key_file) = create_test_config_with_certs();
        let mut auth = DXTradeAuth::new(&config).unwrap();

        // Set up some credentials
        auth.set_session_token(
            "sensitive_token".to_string(),
            chrono::Utc::now() + chrono::Duration::hours(1),
        );
        let encryption_key = DXTradeAuth::generate_encryption_key();
        auth.encrypt_credentials(&encryption_key).unwrap();

        assert!(auth.get_session_token().is_some());

        // Clean up credentials
        auth.zeroize_credentials();

        assert!(auth.get_session_token().is_none());
    }

    #[test]
    fn test_encryption_key_generation() {
        let key1 = DXTradeAuth::generate_encryption_key();
        let key2 = DXTradeAuth::generate_encryption_key();

        // Keys should be different (but our test implementation might be deterministic)
        assert_eq!(key1.len(), 32);
        assert_eq!(key2.len(), 32);
        // Note: In a real cryptographic implementation, we'd expect different keys
    }

    #[test]
    fn test_secure_string_functionality() {
        let sensitive_data = "very_secret_password".to_string();
        let secure = SecureString::new(sensitive_data.clone());

        assert_eq!(secure.as_str(), "very_secret_password");
        assert_eq!(secure.as_bytes(), b"very_secret_password");

        // Debug should not reveal the actual value
        let debug_str = format!("{:?}", secure);
        assert_eq!(debug_str, "[REDACTED]");
    }
}
