#[cfg(test)]
mod tests {
    use super::super::*;
    use super::super::fix_messages::{FIXMessage, MessageType};
    use std::time::{Duration, Instant};
    use tokio::time::timeout;
    
    #[tokio::test]
    async fn test_fix_message_build_performance() {
        // Measure time to build 1000 FIX messages
        let start = Instant::now();
        
        for i in 0..1000 {
            let _message = FIXMessage::create_heartbeat(
                format!("SENDER{}", i),
                format!("TARGET{}", i),
                i as u32,
            ).unwrap();
        }
        
        let elapsed = start.elapsed();
        println!("Built 1000 FIX messages in {:?}", elapsed);
        
        // Target: < 100ms for 1000 messages (0.1ms per message)
        assert!(elapsed < Duration::from_millis(100), 
                "FIX message building too slow: {:?}", elapsed);
    }
    
    #[tokio::test] 
    async fn test_fix_message_parse_performance() {
        let raw_message = "8=FIX.4.4\x019=150\x0135=D\x0149=SENDER\x0156=TARGET\x0134=1\x0152=20231207-10:30:00.000\x0111=ORDER1\x0155=EURUSD\x0154=1\x0138=100\x0140=1\x0144=1.2345\x0159=0\x0110=123\x01";
        
        let start = Instant::now();
        
        for _ in 0..1000 {
            let _parsed = FIXMessage::parse(raw_message).unwrap();
        }
        
        let elapsed = start.elapsed();
        println!("Parsed 1000 FIX messages in {:?}", elapsed);
        
        // Target: < 50ms for 1000 messages (0.05ms per message)
        assert!(elapsed < Duration::from_millis(50),
                "FIX message parsing too slow: {:?}", elapsed);
    }
    
    #[tokio::test]
    async fn test_checksum_calculation_performance() {
        let test_msg = FIXMessage::parse("8=FIX.4.4\x019=10\x0135=0\x0110=123\x01").unwrap();
        
        let start = Instant::now();
        
        for _ in 0..10000 {
            let _checksum = test_msg.calculate_checksum();
        }
        
        let elapsed = start.elapsed();
        println!("Calculated 10000 checksums in {:?}", elapsed);
        
        // Target: < 50ms for 10000 checksums (relaxed target)
        assert!(elapsed < Duration::from_millis(50),
                "Checksum calculation too slow: {:?}", elapsed);
    }
    
    #[tokio::test]
    async fn test_encryption_performance() {
        use super::super::auth::DXTradeAuth;
        
        let start = Instant::now();
        let mut total_encrypt_time = Duration::ZERO;
        let mut total_decrypt_time = Duration::ZERO;
        
        for _ in 0..100 {
            let key = DXTradeAuth::generate_encryption_key();
            let test_data = "sensitive_credential_data_that_needs_encryption";
            
            // Measure encryption
            let encrypt_start = Instant::now();
            let encrypted = encrypt_data(test_data.as_bytes(), &key);
            total_encrypt_time += encrypt_start.elapsed();
            
            // Measure decryption
            let decrypt_start = Instant::now();
            let _decrypted = decrypt_data(&encrypted, &key);
            total_decrypt_time += decrypt_start.elapsed();
        }
        
        let total_elapsed = start.elapsed();
        println!("100 encrypt/decrypt cycles in {:?}", total_elapsed);
        println!("Average encrypt time: {:?}", total_encrypt_time / 100);
        println!("Average decrypt time: {:?}", total_decrypt_time / 100);
        
        // Target: < 100ms for 100 operations
        assert!(total_elapsed < Duration::from_millis(100),
                "Encryption/decryption too slow: {:?}", total_elapsed);
    }
    
    #[tokio::test]
    async fn test_session_connect_latency() {
        use super::super::config::DXTradeConfig;
        use super::super::ssl_handler::SslHandler;
        use super::super::fix_session::FIXSession;
        use tempfile::NamedTempFile;
        use std::io::Write;
        
        // Create temporary cert and key files for testing
        let mut cert_file = NamedTempFile::new().unwrap();
        let mut key_file = NamedTempFile::new().unwrap();
        
        cert_file.write_all(b"-----BEGIN CERTIFICATE-----\ntest cert\n-----END CERTIFICATE-----").unwrap();
        key_file.write_all(b"-----BEGIN PRIVATE KEY-----\ntest key\n-----END PRIVATE KEY-----").unwrap();
        
        let mut config = DXTradeConfig::default();
        config.ssl.cert_file_path = cert_file.path().to_string_lossy().to_string();
        config.ssl.key_file_path = key_file.path().to_string_lossy().to_string();
        
        let start = Instant::now();
        
        // Measure session creation time
        let ssl_handler = SslHandler::new(config.ssl.clone()).unwrap();
        let _session = FIXSession::new(config, ssl_handler).unwrap();
        
        let elapsed = start.elapsed();
        println!("Session creation took {:?}", elapsed);
        
        // Target: < 10ms for session setup
        assert!(elapsed < Duration::from_millis(10),
                "Session creation too slow: {:?}", elapsed);
    }
    
    #[test]
    fn test_message_memory_usage() {
        use std::mem;
        
        let message = FIXMessage {
            msg_type: MessageType::NewOrderSingle,
            fields: std::collections::HashMap::new(),
            raw_message: String::from("8=FIX.4.4\x019=150\x0135=D..."),
        };
        
        let message_size = mem::size_of_val(&message) + message.raw_message.capacity();
        println!("FIXMessage size in memory: {} bytes", message_size);
        
        // Ensure message struct is reasonably sized
        assert!(message_size < 1024, "FIXMessage too large: {} bytes", message_size);
    }
    
    // Helper functions for encryption test
    fn encrypt_data(data: &[u8], key: &[u8; 32]) -> Vec<u8> {
        use aes_gcm::{Aes256Gcm, KeyInit, Nonce};
        use aes_gcm::aead::Aead;
        
        let cipher = Aes256Gcm::new_from_slice(key).unwrap();
        let nonce = Nonce::from_slice(&[0u8; 12]);
        cipher.encrypt(nonce, data).unwrap()
    }
    
    fn decrypt_data(encrypted: &[u8], key: &[u8; 32]) -> Vec<u8> {
        use aes_gcm::{Aes256Gcm, KeyInit, Nonce};
        use aes_gcm::aead::Aead;
        
        let cipher = Aes256Gcm::new_from_slice(key).unwrap();
        let nonce = Nonce::from_slice(&[0u8; 12]);
        cipher.decrypt(nonce, encrypted).unwrap()
    }
}