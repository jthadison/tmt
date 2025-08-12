#[cfg(test)]
mod tests {
    use super::super::config::*;
    use super::super::DXTradeEnvironment;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn create_test_cert_files() -> (NamedTempFile, NamedTempFile) {
        let mut cert_file = NamedTempFile::new().unwrap();
        let mut key_file = NamedTempFile::new().unwrap();

        cert_file
            .write_all(b"-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----")
            .unwrap();
        key_file
            .write_all(b"-----BEGIN PRIVATE KEY-----\ntest key\n-----END PRIVATE KEY-----")
            .unwrap();

        (cert_file, key_file)
    }

    #[test]
    fn test_default_config_creation() {
        let config = DXTradeConfig::default();

        assert_eq!(config.fix_settings.fix_version, "FIX.4.4");
        assert_eq!(config.connection.connect_timeout_ms, 5000);
        assert_eq!(config.connection.heartbeat_interval_s, 30);
        assert_eq!(config.performance.message_pool_size, 1000);
        assert!(config.performance.use_zero_copy);
        assert!(config.ssl.verify_peer);
        assert!(config.logging.enable_fix_logging);
    }

    #[test]
    fn test_config_validation_success() {
        let (cert_file, key_file) = create_test_cert_files();
        let mut config = DXTradeConfig::default();

        config.credentials.sender_comp_id = "TEST_SENDER".to_string();
        config.credentials.target_comp_id = "TEST_TARGET".to_string();
        config.credentials.account_id = "TEST_ACCOUNT".to_string();
        config.ssl.cert_file_path = cert_file.path().to_string_lossy().to_string();
        config.ssl.key_file_path = key_file.path().to_string_lossy().to_string();

        let result = config.validate();
        assert!(result.is_ok());
    }

    #[test]
    fn test_config_validation_empty_sender_comp_id() {
        let (cert_file, key_file) = create_test_cert_files();
        let mut config = DXTradeConfig::default();

        config.credentials.sender_comp_id = "".to_string(); // Empty - should fail
        config.credentials.target_comp_id = "TEST_TARGET".to_string();
        config.credentials.account_id = "TEST_ACCOUNT".to_string();
        config.ssl.cert_file_path = cert_file.path().to_string_lossy().to_string();
        config.ssl.key_file_path = key_file.path().to_string_lossy().to_string();

        let result = config.validate();
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("sender_comp_id cannot be empty"));
    }

    #[test]
    fn test_config_validation_missing_cert_file() {
        let mut config = DXTradeConfig::default();

        config.credentials.sender_comp_id = "TEST_SENDER".to_string();
        config.credentials.target_comp_id = "TEST_TARGET".to_string();
        config.credentials.account_id = "TEST_ACCOUNT".to_string();
        config.ssl.cert_file_path = "/non/existent/cert.pem".to_string();
        config.ssl.key_file_path = "/non/existent/key.pem".to_string();

        let result = config.validate();
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("certificate file not found"));
    }

    #[test]
    fn test_config_validation_invalid_heartbeat_interval() {
        let (cert_file, key_file) = create_test_cert_files();
        let mut config = DXTradeConfig::default();

        config.credentials.sender_comp_id = "TEST_SENDER".to_string();
        config.credentials.target_comp_id = "TEST_TARGET".to_string();
        config.credentials.account_id = "TEST_ACCOUNT".to_string();
        config.ssl.cert_file_path = cert_file.path().to_string_lossy().to_string();
        config.ssl.key_file_path = key_file.path().to_string_lossy().to_string();
        config.connection.heartbeat_interval_s = 5; // Too low - should fail

        let result = config.validate();
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("heartbeat_interval_s must be at least 10 seconds"));
    }

    #[test]
    fn test_config_timeout_methods() {
        let config = DXTradeConfig::default();

        assert_eq!(config.connect_timeout().as_millis(), 5000);
        assert_eq!(config.read_timeout().as_millis(), 30000);
        assert_eq!(config.write_timeout().as_millis(), 5000);
        assert_eq!(config.heartbeat_interval().as_secs(), 30);
        assert_eq!(config.reconnect_backoff().as_millis(), 1000);
    }

    #[test]
    fn test_dxtrade_environment_urls() {
        let prod = DXTradeEnvironment::Production;
        let test = DXTradeEnvironment::Test;
        let staging = DXTradeEnvironment::Staging;

        assert_eq!(prod.fix_host(), "fix.dxtrade.com");
        assert_eq!(test.fix_host(), "fix-test.dxtrade.com");
        assert_eq!(staging.fix_host(), "fix-staging.dxtrade.com");

        assert_eq!(prod.fix_port(), 443);
        assert_eq!(test.fix_port(), 443);
        assert_eq!(staging.fix_port(), 443);

        assert_eq!(prod.rest_base_url(), "https://api.dxtrade.com/v2");
        assert_eq!(test.rest_base_url(), "https://api-test.dxtrade.com/v2");
        assert_eq!(
            staging.rest_base_url(),
            "https://api-staging.dxtrade.com/v2"
        );
    }

    #[test]
    fn test_connection_config_defaults() {
        let config = ConnectionConfig::default();

        assert_eq!(config.connect_timeout_ms, 5000);
        assert_eq!(config.read_timeout_ms, 30000);
        assert_eq!(config.write_timeout_ms, 5000);
        assert_eq!(config.heartbeat_interval_s, 30);
        assert_eq!(config.test_request_delay_s, 120);
        assert_eq!(config.max_reconnect_attempts, 5);
        assert_eq!(config.reconnect_backoff_ms, 1000);
        assert_eq!(config.max_reconnect_delay_ms, 30000);
    }

    #[test]
    fn test_fix_settings_defaults() {
        let settings = FIXSettings::default();

        assert_eq!(settings.fix_version, "FIX.4.4");
        assert_eq!(settings.begin_string, "FIX.4.4");
        assert!(!settings.reset_on_logon);
        assert!(settings.validate_length_and_checksum);
        assert!(settings.validate_fields_out_of_order);
        assert!(settings.validate_fields_have_values);
        assert!(settings.check_company_id);
        assert!(settings.check_latency);
        assert_eq!(settings.max_latency_ms, 1000);
    }

    #[test]
    fn test_performance_config_defaults() {
        let perf = PerformanceConfig::default();

        assert_eq!(perf.message_pool_size, 1000);
        assert!(perf.use_zero_copy);
        assert!(!perf.enable_batching);
        assert_eq!(perf.max_batch_size, 10);
        assert_eq!(perf.batch_timeout_ms, 10);
        assert!(!perf.enable_binary_encoding);
        assert!(perf.pre_allocate_buffers);
        assert_eq!(perf.buffer_size, 8192);
    }

    #[test]
    fn test_ssl_config_defaults() {
        let ssl = SslConfig::default();

        assert_eq!(ssl.cert_file_path, "");
        assert_eq!(ssl.key_file_path, "");
        assert!(ssl.ca_file_path.is_none());
        assert!(ssl.verify_peer);
        assert!(ssl.verify_hostname);
        assert_eq!(ssl.ssl_version, "TLSv1.2");
        assert!(ssl.cipher_list.is_none());
    }

    #[test]
    fn test_logging_config_defaults() {
        let logging = LoggingConfig::default();

        assert!(logging.enable_fix_logging);
        assert!(logging.log_incoming_messages);
        assert!(logging.log_outgoing_messages);
        assert!(!logging.log_heartbeats);
        assert!(!logging.log_test_requests);
        assert!(logging.log_sequence_resets);
        assert_eq!(logging.log_directory, "./logs/dxtrade/fix");
        assert_eq!(logging.max_log_file_size_mb, 100);
        assert_eq!(logging.max_log_files, 30);
        assert!(logging.compress_logs);
    }
}
