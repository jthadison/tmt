use super::config::SslConfig;
use super::error::{DXTradeError, Result};
use native_tls::{Certificate, Identity, TlsConnector};
use rustls::{ClientConfig, RootCertStore};
use rustls_native_certs;
use std::fs;
use std::io::BufReader;
use std::sync::Arc;
use tokio::net::TcpStream;
use tokio_native_tls::TlsStream;

pub struct SslHandler {
    config: SslConfig,
    tls_connector: TlsConnector,
}

impl SslHandler {
    pub fn new(config: SslConfig) -> Result<Self> {
        let tls_connector = Self::create_tls_connector(&config)?;
        
        Ok(Self {
            config,
            tls_connector,
        })
    }
    
    fn create_tls_connector(config: &SslConfig) -> Result<TlsConnector> {
        let mut builder = TlsConnector::builder();
        
        let identity = Self::load_identity(config)?;
        builder.identity(identity);
        
        if let Some(ca_path) = &config.ca_file_path {
            let ca_cert = Self::load_ca_certificate(ca_path)?;
            builder.add_root_certificate(ca_cert);
        }
        
        if !config.verify_peer {
            builder.danger_accept_invalid_certs(true);
        }
        
        if !config.verify_hostname {
            builder.danger_accept_invalid_hostnames(true);
        }
        
        builder.build()
            .map_err(|e| DXTradeError::TlsError(format!("Failed to build TLS connector: {}", e)))
    }
    
    fn load_identity(config: &SslConfig) -> Result<Identity> {
        // Read certificate and key files as bytes for binary parsing
        let cert_data = fs::read(&config.cert_file_path)
            .map_err(|e| DXTradeError::SslAuthenticationFailed(
                format!("Failed to read certificate file: {}", e)
            ))?;
            
        let key_data = fs::read(&config.key_file_path)
            .map_err(|e| DXTradeError::SslAuthenticationFailed(
                format!("Failed to read key file: {}", e)
            ))?;
        
        // First try PKCS#8 format (binary or PEM-encoded PKCS#8)
        if let Ok(identity) = Identity::from_pkcs8(&cert_data, &key_data) {
            return Ok(identity);
        }
        
        // If PKCS#8 fails, try PKCS#12 format (common for client certificates)
        if let Ok(identity) = Identity::from_pkcs12(&cert_data, "") {
            return Ok(identity);
        }
        
        // Try with common passwords for PKCS#12
        let common_passwords = ["", "password", "changeit", "123456"];
        for password in &common_passwords {
            if let Ok(identity) = Identity::from_pkcs12(&cert_data, password) {
                tracing::warn!("Successfully loaded PKCS#12 identity with password");
                return Ok(identity);
            }
        }
        
        Err(DXTradeError::SslAuthenticationFailed(
            "Failed to create identity: tried PKCS#8 and PKCS#12 formats. Ensure certificate and key are in supported format.".to_string()
        ))
    }
    
    fn load_ca_certificate(ca_path: &str) -> Result<Certificate> {
        let ca_pem = fs::read_to_string(ca_path)
            .map_err(|e| DXTradeError::SslAuthenticationFailed(
                format!("Failed to read CA certificate file: {}", e)
            ))?;
            
        Certificate::from_pem(ca_pem.as_bytes())
            .map_err(|e| DXTradeError::SslAuthenticationFailed(
                format!("Failed to parse CA certificate: {}", e)
            ))
    }
    
    pub async fn connect_to_server(&self, hostname: &str, port: u16) -> Result<TlsStream<TcpStream>> {
        let tcp_stream = TcpStream::connect(format!("{}:{}", hostname, port)).await
            .map_err(|e| DXTradeError::ConnectionError(
                format!("Failed to connect to {}:{}: {}", hostname, port, e)
            ))?;
        
        let tls_connector = tokio_native_tls::TlsConnector::from(self.tls_connector.clone());
        
        let tls_stream = tls_connector.connect(hostname, tcp_stream).await
            .map_err(|e| DXTradeError::SslAuthenticationFailed(
                format!("TLS handshake failed: {}", e)
            ))?;
        
        tracing::info!("SSL connection established to {}:{}", hostname, port);
        Ok(tls_stream)
    }
    
    pub fn create_rustls_config(&self) -> Result<Arc<ClientConfig>> {
        let mut root_store = RootCertStore::empty();
        
        for cert in rustls_native_certs::load_native_certs()
            .map_err(|e| DXTradeError::TlsError(format!("Failed to load native certs: {}", e)))? 
        {
            root_store.add(&rustls::Certificate(cert.0))
                .map_err(|e| DXTradeError::TlsError(format!("Failed to add certificate: {:?}", e)))?;
        }
        
        let config = ClientConfig::builder()
            .with_safe_defaults()
            .with_root_certificates(root_store)
            .with_no_client_auth();
            
        Ok(Arc::new(config))
    }
    
    pub fn validate_certificate_chain(&self) -> Result<()> {
        let cert_pem = fs::read_to_string(&self.config.cert_file_path)
            .map_err(|e| DXTradeError::SslAuthenticationFailed(
                format!("Failed to read certificate file: {}", e)
            ))?;
            
        let cert = Certificate::from_pem(cert_pem.as_bytes())
            .map_err(|e| DXTradeError::SslAuthenticationFailed(
                format!("Failed to parse certificate: {}", e)
            ))?;
        
        tracing::info!("Certificate validation successful");
        Ok(())
    }
    
    pub fn get_certificate_info(&self) -> Result<CertificateInfo> {
        let cert_pem = fs::read_to_string(&self.config.cert_file_path)
            .map_err(|e| DXTradeError::SslAuthenticationFailed(
                format!("Failed to read certificate file: {}", e)
            ))?;
        
        Ok(CertificateInfo {
            cert_path: self.config.cert_file_path.clone(),
            key_path: self.config.key_file_path.clone(),
            ssl_version: self.config.ssl_version.clone(),
            verify_peer: self.config.verify_peer,
            verify_hostname: self.config.verify_hostname,
        })
    }
}

#[derive(Debug, Clone)]
pub struct CertificateInfo {
    pub cert_path: String,
    pub key_path: String,
    pub ssl_version: String,
    pub verify_peer: bool,
    pub verify_hostname: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;
    use std::io::Write;

    fn create_test_ssl_config() -> SslConfig {
        SslConfig {
            cert_file_path: "/tmp/test.crt".to_string(),
            key_file_path: "/tmp/test.key".to_string(),
            ca_file_path: None,
            verify_peer: true,
            verify_hostname: true,
            ssl_version: "TLSv1.2".to_string(),
            cipher_list: None,
        }
    }

    #[test]
    fn test_ssl_config_creation() {
        let config = create_test_ssl_config();
        assert_eq!(config.ssl_version, "TLSv1.2");
        assert!(config.verify_peer);
        assert!(config.verify_hostname);
    }

    #[test]
    fn test_certificate_info_creation() {
        let config = create_test_ssl_config();
        let cert_info = CertificateInfo {
            cert_path: config.cert_file_path.clone(),
            key_path: config.key_file_path.clone(),
            ssl_version: config.ssl_version.clone(),
            verify_peer: config.verify_peer,
            verify_hostname: config.verify_hostname,
        };
        
        assert_eq!(cert_info.ssl_version, "TLSv1.2");
        assert!(cert_info.verify_peer);
    }
}