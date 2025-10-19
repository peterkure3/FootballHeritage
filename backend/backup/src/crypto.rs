#![allow(dead_code)]
#![allow(deprecated)]
use aes_gcm::{Aes256Gcm, KeyInit};
use aes_gcm::aead::{Aead, OsRng, generic_array::GenericArray};
use argon2::{Argon2, PasswordHash, PasswordHasher, PasswordVerifier};
use argon2::password_hash::{rand_core::OsRng as ArgonRng, SaltString};
use ring::hmac;
use base64::{Engine as _, engine::general_purpose};
use rand::{RngCore, thread_rng};
use std::error::Error;
use crate::errors::AppError;
use crate::config::AppConfig;
use bigdecimal::BigDecimal;
use std::str::FromStr;

pub struct CryptoService {
    encryption_key: [u8; 32],
    hmac_key: [u8; 32],
}

impl CryptoService {
    pub fn new(config: &AppConfig) -> Result<Self, Box<dyn Error>> {
        if !config.validate_encryption_key() {
            return Err("Encryption key must be exactly 32 bytes".into());
        }

        let mut encryption_key = [0u8; 32];
        let key_bytes = config.encryption_key.as_bytes();
        let key_len = key_bytes.len().min(32);
        encryption_key[..key_len].copy_from_slice(&key_bytes[..key_len]);

        let mut hmac_key = [0u8; 32];
        let mut rng = thread_rng();
        rng.fill_bytes(&mut hmac_key);

        Ok(Self {
            encryption_key,
            hmac_key,
        })
    }

    /// Create CryptoService directly from a 32-byte key
    pub fn from_key(key: &[u8; 32]) -> Self {
        let mut hmac_key = [0u8; 32];
        let mut rng = thread_rng();
        rng.fill_bytes(&mut hmac_key);

        Self {
            encryption_key: *key,
            hmac_key,
        }
    }

    /// Create CryptoService from a string key (will be padded/truncated to 32 bytes)
    pub fn from_string(key_str: &str) -> Self {
        let mut encryption_key = [0u8; 32];
        let key_bytes = key_str.as_bytes();
        let key_len = key_bytes.len().min(32);
        encryption_key[..key_len].copy_from_slice(&key_bytes[..key_len]);

        let mut hmac_key = [0u8; 32];
        let mut rng = thread_rng();
        rng.fill_bytes(&mut hmac_key);

        Self {
            encryption_key,
            hmac_key,
        }
    }

    /// Hash password using Argon2 with strong parameters
    pub fn hash_password(&self, password: &str) -> Result<String, AppError> {
        let salt = SaltString::generate(&mut ArgonRng);

        let argon2 = Argon2::new(
            argon2::Algorithm::Argon2id,
            argon2::Version::V0x13,
            argon2::Params::new(65536, 3, 1, Some(32))
                .map_err(|e| AppError::Encryption(format!("Argon2 params error: {}", e)))?,
        );

        let password_hash = argon2
            .hash_password(password.as_bytes(), &salt)
            .map_err(|e| AppError::Encryption(format!("Password hashing failed: {}", e)))?;

        Ok(password_hash.to_string())
    }

    /// Verify password against hash
    pub fn verify_password(&self, password: &str, hash: &str) -> Result<bool, AppError> {
        let parsed_hash = PasswordHash::new(hash)
            .map_err(|e| AppError::Encryption(format!("Invalid password hash: {}", e)))?;

        let argon2 = Argon2::default();

        match argon2.verify_password(password.as_bytes(), &parsed_hash) {
            Ok(()) => Ok(true),
            Err(argon2::password_hash::Error::Password) => Ok(false),
            Err(e) => Err(AppError::Encryption(format!("Password verification error: {}", e))),
        }
    }

    /// Encrypt wallet balance using AES-256-GCM
    pub fn encrypt_balance(&self, amount: &BigDecimal) -> Result<(String, String), AppError> {
        let cipher = Aes256Gcm::new_from_slice(&self.encryption_key)
            .map_err(|e| AppError::Encryption(format!("Cipher creation failed: {}", e)))?;

        let amount_str = amount.to_string();
        let amount_bytes = amount_str.as_bytes();

        let mut nonce_bytes = [0u8; 12];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = GenericArray::from_slice(&nonce_bytes);

        let ciphertext = cipher
            .encrypt(nonce, amount_bytes)
            .map_err(|e| AppError::Encryption(format!("Encryption failed: {}", e)))?;

        let encrypted_balance = general_purpose::STANDARD.encode(&ciphertext);
        let iv = general_purpose::STANDARD.encode(&nonce_bytes);

        Ok((encrypted_balance, iv))
    }

    /// Decrypt wallet balance
    pub fn decrypt_balance(&self, encrypted_balance: &str, iv: &str) -> Result<BigDecimal, AppError> {
        let cipher = Aes256Gcm::new_from_slice(&self.encryption_key)
            .map_err(|e| AppError::Encryption(format!("Cipher creation failed: {}", e)))?;

        let ciphertext = general_purpose::STANDARD
            .decode(encrypted_balance)
            .map_err(|e| AppError::Encryption(format!("Base64 decode failed: {}", e)))?;

        let nonce_bytes = general_purpose::STANDARD
            .decode(iv)
            .map_err(|e| AppError::Encryption(format!("IV decode failed: {}", e)))?;

        if nonce_bytes.len() != 12 {
            return Err(AppError::Encryption("Invalid IV length".to_string()));
        }

        let nonce = GenericArray::from_slice(&nonce_bytes);

        let plaintext = cipher
            .decrypt(nonce, ciphertext.as_ref())
            .map_err(|e| AppError::Encryption(format!("Decryption failed: {}", e)))?;

        let amount_str = String::from_utf8(plaintext)
            .map_err(|e| AppError::Encryption(format!("UTF-8 decode failed: {}", e)))?;

        BigDecimal::from_str(&amount_str)
            .map_err(|e| AppError::Encryption(format!("BigDecimal parse failed: {}", e)))
    }

    /// Generate secure random token for CSRF protection
    pub fn generate_csrf_token(&self) -> String {
        let mut token_bytes = [0u8; 32];
        thread_rng().fill_bytes(&mut token_bytes);
        general_purpose::STANDARD.encode(&token_bytes)
    }

    /// Verify CSRF token
    pub fn verify_csrf_token(&self, token: &str, expected_token: &str) -> bool {
        // Use constant-time comparison to prevent timing attacks
        if token.len() != expected_token.len() {
            return false;
        }

        let token_bytes = match general_purpose::STANDARD.decode(token) {
            Ok(bytes) => bytes,
            Err(_) => return false,
        };

        let expected_bytes = match general_purpose::STANDARD.decode(expected_token) {
            Ok(bytes) => bytes,
            Err(_) => return false,
        };

        let mut result = 0u8;
        for (a, b) in token_bytes.iter().zip(expected_bytes.iter()) {
            result |= a ^ b;
        }

        result == 0
    }

    /// Generate secure session token
    pub fn generate_session_token(&self) -> String {
        let mut token_bytes = [0u8; 64];
        thread_rng().fill_bytes(&mut token_bytes);
        general_purpose::STANDARD.encode(&token_bytes)
    }

    /// Create HMAC signature for sensitive data
    pub fn create_hmac(&self, data: &[u8]) -> Result<String, AppError> {
        let key = hmac::Key::new(hmac::HMAC_SHA256, &self.hmac_key);
        let tag = hmac::sign(&key, data);
        Ok(general_purpose::STANDARD.encode(tag.as_ref()))
    }

    /// Verify HMAC signature
    pub fn verify_hmac(&self, data: &[u8], signature: &str) -> Result<bool, AppError> {
        let signature_bytes = general_purpose::STANDARD
            .decode(signature)
            .map_err(|e| AppError::Encryption(format!("HMAC decode failed: {}", e)))?;

        let key = hmac::Key::new(hmac::HMAC_SHA256, &self.hmac_key);

        match hmac::verify(&key, data, &signature_bytes) {
            Ok(()) => Ok(true),
            Err(_) => Ok(false),
        }
    }

    /// Generate secure random bytes
    pub fn generate_random_bytes(&self, length: usize) -> Vec<u8> {
        let mut bytes = vec![0u8; length];
        thread_rng().fill_bytes(&mut bytes);
        bytes
    }

    /// Derive a key from password using PBKDF2 (for additional security)
    pub fn derive_key(&self, password: &str, salt: &[u8], iterations: u32) -> Result<[u8; 32], AppError> {
        use ring::pbkdf2;

        let mut key = [0u8; 32];
        pbkdf2::derive(
            pbkdf2::PBKDF2_HMAC_SHA256,
            std::num::NonZeroU32::new(iterations).unwrap(),
            salt,
            password.as_bytes(),
            &mut key,
        );

        Ok(key)
    }

    /// Check password strength using zxcvbn
    pub fn check_password_strength(&self, password: &str) -> Result<u8, AppError> {
        use zxcvbn::zxcvbn;

        let estimate = zxcvbn(password, &[])
            .map_err(|e| AppError::Encryption(format!("Password strength check failed: {}", e)))?;

        // Return score (0-4), we require minimum score of 2
        Ok(estimate.score() as u8)
    }

    /// Generate secure API key
    pub fn generate_api_key(&self) -> String {
        let mut key_bytes = [0u8; 32];
        thread_rng().fill_bytes(&mut key_bytes);
        format!("fh_{}", general_purpose::STANDARD.encode(&key_bytes))
    }

    /// Obfuscate sensitive data for logging
    pub fn obfuscate_email(&self, email: &str) -> String {
        if let Some(at_pos) = email.find('@') {
            let domain = &email[at_pos..];
            let local = &email[..at_pos];

            if local.len() <= 2 {
                format!("***{}", domain)
            } else {
                format!("{}***{}", &local[..2], domain)
            }
        } else {
            "***".to_string()
        }
    }

    /// Obfuscate credit card number
    pub fn obfuscate_card(&self, card: &str) -> String {
        if card.len() <= 4 {
            "****".to_string()
        } else {
            format!("****-****-****-{}", &card[card.len()-4..])
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::AppConfig;

    fn get_test_config() -> AppConfig {
        AppConfig {
            database_url: "test".to_string(),
            jwt_secret: "test_jwt_secret_that_is_long_enough".to_string(),
            jwt_expiration_hours: 24,
            encryption_key: "32_byte_long_encryption_key_test".to_string(),
            host: "127.0.0.1".to_string(),
            port: 8080,
            https_enabled: false,
            tls_cert_path: "".to_string(),
            tls_key_path: "".to_string(),
            bet_rate_limit_per_minute: 5,
            login_rate_limit_per_minute: 10,
            register_rate_limit_per_hour: 5,
            bcrypt_cost: 12,
            session_timeout_minutes: 30,
            max_login_attempts: 5,
            account_lock_minutes: 15,
            default_daily_loss_limit: 1000.0,
            default_weekly_loss_limit: 5000.0,
            default_monthly_loss_limit: 15000.0,
            default_daily_bet_limit: 2000.0,
            default_weekly_bet_limit: 10000.0,
            default_monthly_bet_limit: 30000.0,
            default_max_single_bet: 500.0,
            log_level: "info".to_string(),
            fraud_alert_email: "test@example.com".to_string(),
            allowed_origins: vec!["http://localhost:3000".to_string()],
            metrics_enabled: true,
            health_check_interval_seconds: 30,
        }
    }

    #[test]
    fn test_password_hashing() {
        let config = get_test_config();
        let crypto = CryptoService::new(&config).unwrap();

        let password = "TestPassword123!";
        let hash = crypto.hash_password(password).unwrap();

        assert!(hash.starts_with("$argon2id$"));
        assert!(crypto.verify_password(password, &hash).unwrap());
        assert!(!crypto.verify_password("wrongpassword", &hash).unwrap());
    }

    #[test]
    fn test_balance_encryption() {
        let config = get_test_config();
        let crypto = CryptoService::new(&config).unwrap();

        let amount = BigDecimal::from_str("1234.56").unwrap();
        let (encrypted, iv) = crypto.encrypt_balance(&amount).unwrap();

        let decrypted = crypto.decrypt_balance(&encrypted, &iv).unwrap();
        assert_eq!(amount, decrypted);
    }

    #[test]
    fn test_csrf_token() {
        let config = get_test_config();
        let crypto = CryptoService::new(&config).unwrap();

        let token = crypto.generate_csrf_token();
        assert!(!token.is_empty());
        assert!(token.len() > 32);

        assert!(crypto.verify_csrf_token(&token, &token));
        assert!(!crypto.verify_csrf_token(&token, "wrong_token"));
    }
}
