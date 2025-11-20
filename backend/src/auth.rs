use crate::models::{Claims, User};
use crate::errors::{AppError, AppResult};
use crate::config::AppConfig;
use chrono::{Duration, Utc};
use jsonwebtoken::{encode, decode, Header, Validation, EncodingKey, DecodingKey};
use uuid::Uuid;
use std::sync::Arc;
use dashmap::DashMap;

#[derive(Clone)]
pub struct AuthService {
    config: Arc<AppConfig>,
    jwt_secret: String,
    active_sessions: Arc<DashMap<String, SessionInfo>>,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct SessionInfo {
    pub user_id: Uuid,
    pub email: String,
    pub ip_address: String,
    pub user_agent: String,
    pub created_at: chrono::DateTime<Utc>,
    pub last_activity: chrono::DateTime<Utc>,
    pub is_active: bool,
}

impl AuthService {
    pub fn new(config: Arc<AppConfig>) -> Self {
        Self {
            jwt_secret: config.jwt_secret.clone(),
            config,
            active_sessions: Arc::new(DashMap::new()),
        }
    }

    /// Generate JWT token for authenticated user
    pub fn generate_token(&self, user: &User, session_id: &str) -> AppResult<String> {
        let now = Utc::now();
        let exp = now + Duration::hours(self.config.jwt_expiration_hours as i64);

        let claims = Claims {
            sub: user.id.to_string(),
            email: user.email.clone(),
            exp: exp.timestamp() as usize,
            iat: now.timestamp() as usize,
            iss: "football-heritage-api".to_string(),
            aud: "football-heritage-client".to_string(),
            session_id: session_id.to_string(),
            role: user.role.clone().unwrap_or_else(|| "user".to_string()),
        };

        let header = Header::default();
        let key = EncodingKey::from_secret(self.jwt_secret.as_ref());

        encode(&header, &claims, &key)
            .map_err(|e| AppError::JWT(e))
    }

    /// Validate and decode JWT token
    pub fn validate_token(&self, token: &str) -> AppResult<Claims> {
        let key = DecodingKey::from_secret(self.jwt_secret.as_ref());
        let mut validation = Validation::default();
        // Don't validate aud/iss since we set custom values
        validation.validate_aud = false;
        validation.set_required_spec_claims(&["exp", "sub"]);

        let token_data = decode::<Claims>(token, &key, &validation)
            .map_err(|e| AppError::JWT(e))?;
        let claims = token_data.claims;

        self.ensure_active_session(&claims)?;

        Ok(claims)
    }

    /// Extract token from Authorization header
    #[allow(dead_code)]
    pub fn extract_token_from_header(&self, auth_header: &str) -> AppResult<String> {
        if !auth_header.starts_with("Bearer ") {
            return Err(AppError::Authentication("Invalid authorization header format".to_string()));
        }

        let token = auth_header[7..].trim();
        if token.is_empty() {
            return Err(AppError::Authentication("Token not provided".to_string()));
        }

        Ok(token.to_string())
    }

    /// Create new session
    pub fn create_session(&self, user: &User, session_id: &str, ip_address: &str, user_agent: &str) {
        let session_info = SessionInfo {
            user_id: user.id,
            email: user.email.clone(),
            ip_address: ip_address.to_string(),
            user_agent: user_agent.to_string(),
            created_at: Utc::now(),
            last_activity: Utc::now(),
            is_active: true,
        };

        self.active_sessions.insert(session_id.to_string(), session_info);
    }

    /// Get session information
    #[allow(dead_code)]
    pub fn get_session(&self, session_id: &str) -> Option<SessionInfo> {
        self.active_sessions.get(session_id).map(|session| session.clone())
    }

    /// Update session activity
    pub fn update_session_activity(&self, session_id: &str) -> AppResult<()> {
        if let Some(mut session) = self.active_sessions.get_mut(session_id) {
            session.last_activity = Utc::now();
            Ok(())
        } else {
            Err(AppError::SessionExpired)
        }
    }

    /// Invalidate session
    #[allow(dead_code)]
    pub fn invalidate_session(&self, session_id: &str) {
        self.active_sessions.remove(session_id);
    }

    /// Clean up expired sessions
    #[allow(dead_code)]
    pub fn cleanup_expired_sessions(&self) {
        let now = Utc::now();
        let timeout_duration = Duration::minutes(self.config.session_timeout_minutes as i64);

        let expired_sessions: Vec<String> = self.active_sessions
            .iter()
            .filter(|entry| {
                let session = entry.value();
                now.signed_duration_since(session.last_activity) > timeout_duration || !session.is_active
            })
            .map(|entry| entry.key().clone())
            .collect();

        for session_id in expired_sessions {
            self.active_sessions.remove(&session_id);
        }
    }

    /// Check if user has active sessions
    #[allow(dead_code)]
    pub fn has_active_sessions(&self, user_id: &Uuid) -> bool {
        self.active_sessions
            .iter()
            .any(|entry| entry.value().user_id == *user_id && entry.value().is_active)
    }

    /// Invalidate all sessions for a user
    #[allow(dead_code)]
    pub fn invalidate_user_sessions(&self, user_id: &Uuid) {
        let sessions_to_remove: Vec<String> = self.active_sessions
            .iter()
            .filter(|entry| entry.value().user_id == *user_id)
            .map(|entry| entry.key().clone())
            .collect();

        for session_id in sessions_to_remove {
            self.active_sessions.remove(&session_id);
        }
    }

    /// Get active session count for a user
    #[allow(dead_code)]
    pub fn get_user_session_count(&self, user_id: &Uuid) -> usize {
        self.active_sessions
            .iter()
            .filter(|entry| entry.value().user_id == *user_id && entry.value().is_active)
            .count()
    }

    /// Detect suspicious login patterns
    #[allow(dead_code)]
    pub fn detect_suspicious_login(&self, user_id: &Uuid, ip_address: &str) -> bool {
        let user_sessions: Vec<SessionInfo> = self.active_sessions
            .iter()
            .filter(|entry| entry.value().user_id == *user_id)
            .map(|entry| entry.value().clone())
            .collect();

        // Check for multiple IPs in short time
        let unique_ips: std::collections::HashSet<&str> = user_sessions
            .iter()
            .map(|s| s.ip_address.as_str())
            .collect();

        if unique_ips.len() > 3 {
            return true;
        }

        // Check for rapid successive logins
        let recent_logins: Vec<_> = user_sessions
            .iter()
            .filter(|s| {
                Utc::now().signed_duration_since(s.created_at).num_minutes() < 10
            })
            .collect();

        if recent_logins.len() > 2 {
            return true;
        }

        // Check for login from new geographic location (simplified check)
        if !user_sessions.is_empty() {
            let last_ip = user_sessions.last().unwrap().ip_address.clone();
            if last_ip != ip_address {
                return true;
            }
        }

        false
    }

    /// Generate secure refresh token
    #[allow(dead_code)]
    pub fn generate_refresh_token(&self) -> String {
        use base64::{Engine as _, engine::general_purpose};
        use rand::{RngCore, thread_rng};

        let mut token_bytes = [0u8; 32];
        thread_rng().fill_bytes(&mut token_bytes);
        format!("refresh_{}", general_purpose::STANDARD.encode(&token_bytes))
    }

    /// Validate refresh token format
    #[allow(dead_code)]
    pub fn validate_refresh_token(&self, token: &str) -> bool {
        token.starts_with("refresh_") && token.len() > 50
    }

    /// Check if user is verified
    #[allow(dead_code)]
    pub fn is_user_verified(user: &User) -> bool {
        user.is_verified
    }

    /// Check if user account is locked
    #[allow(dead_code)]
    pub fn is_account_locked(user: &User) -> bool {
        if let Some(locked_until) = user.locked_until {
            return locked_until > Utc::now();
        }
        false
    }

    /// Check if user has exceeded max login attempts
    #[allow(dead_code)]
    pub fn has_exceeded_max_attempts(user: &User, max_attempts: u32) -> bool {
        user.failed_login_attempts >= max_attempts as i32
    }

    /// Calculate account lock duration
    #[allow(dead_code)]
    pub fn calculate_lock_duration(failed_attempts: i32, base_minutes: u64) -> u64 {
        match failed_attempts {
            0..=3 => 0,
            4..=5 => base_minutes,
            6..=7 => base_minutes * 2,
            8..=10 => base_minutes * 4,
            _ => base_minutes * 8,
        }
    }

    /// Generate password reset token
    #[allow(dead_code)]
    pub fn generate_password_reset_token(&self) -> String {
        use base64::{Engine as _, engine::general_purpose};
        use rand::{RngCore, thread_rng};

        let mut token_bytes = [0u8; 32];
        thread_rng().fill_bytes(&mut token_bytes);
        format!("reset_{}", general_purpose::STANDARD.encode(&token_bytes))
    }

    /// Validate password reset token format
    #[allow(dead_code)]
    pub fn validate_password_reset_token(&self, token: &str) -> bool {
        token.starts_with("reset_") && token.len() > 50
    }

    /// Generate email verification token
    #[allow(dead_code)]
    pub fn generate_email_verification_token(&self) -> String {
        use base64::{Engine as _, engine::general_purpose};
        use rand::{RngCore, thread_rng};

        let mut token_bytes = [0u8; 32];
        thread_rng().fill_bytes(&mut token_bytes);
        format!("verify_{}", general_purpose::STANDARD.encode(&token_bytes))
    }

    /// Validate email verification token format
    #[allow(dead_code)]
    pub fn validate_email_verification_token(&self, token: &str) -> bool {
        token.starts_with("verify_") && token.len() > 50
    }

    fn ensure_active_session(&self, claims: &Claims) -> AppResult<()> {
        let now = Utc::now();
        let timeout = Duration::minutes(self.config.session_timeout_minutes as i64);
        let mut should_remove = false;

        {
            let mut session = self
                .active_sessions
                .get_mut(&claims.session_id)
                .ok_or(AppError::SessionExpired)?;

            if !session.is_active
                || now.signed_duration_since(session.last_activity) > timeout
                || session.user_id.to_string() != claims.sub
            {
                should_remove = true;
            } else {
                session.last_activity = now;
            }
        }

        if should_remove {
            self.active_sessions.remove(&claims.session_id);
            return Err(AppError::SessionExpired);
        }

        Ok(())
    }
}

// Middleware for JWT authentication
#[allow(dead_code)]
pub struct JwtMiddleware {
    auth_service: Arc<AuthService>,
}

impl JwtMiddleware {
    #[allow(dead_code)]
    pub fn new(auth_service: Arc<AuthService>) -> Self {
        Self { auth_service }
    }

    #[allow(dead_code)]
    pub async fn authenticate(&self, token: &str) -> AppResult<Claims> {
        let claims = self.auth_service.validate_token(token)?;

        // Check if session is still active
        if let Some(session) = self.auth_service.get_session(&claims.session_id) {
            if !session.is_active {
                return Err(AppError::SessionExpired);
            }

            // Update session activity
            self.auth_service.update_session_activity(&claims.session_id)?;
        } else {
            return Err(AppError::SessionExpired);
        }

        Ok(claims)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::AppConfig;
    use chrono::Utc;

    fn get_test_config() -> AppConfig {
        AppConfig {
            database_url: "test".to_string(),
            jwt_secret: "test_jwt_secret_that_is_long_enough_for_security_purposes".to_string(),
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
    fn test_jwt_token_generation_and_validation() {
        let config = Arc::new(get_test_config());
        let auth_service = AuthService::new(config);

        let user = User {
            id: Uuid::new_v4(),
            email: "test@example.com".to_string(),
            password_hash: "hash".to_string(),
            first_name: "Test".to_string(),
            last_name: "User".to_string(),
            date_of_birth: chrono::NaiveDate::from_ymd_opt(1990, 1, 1).unwrap(),
            phone: None,
            address: None,
            is_verified: true,
            is_active: true,
            role: Some("user".to_string()),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            last_login: None,
            login_count: 0,
            failed_login_attempts: 0,
            locked_until: None,
        };

        let session_id = "test_session_123";
        let token = auth_service.generate_token(&user, session_id).unwrap();

        let claims = auth_service.validate_token(&token).unwrap();
        assert_eq!(claims.sub, user.id.to_string());
        assert_eq!(claims.email, user.email);
        assert_eq!(claims.session_id, session_id);
    }

    #[test]
    fn test_session_management() {
        let config = Arc::new(get_test_config());
        let auth_service = AuthService::new(config);

        let user = User {
            id: Uuid::new_v4(),
            email: "test@example.com".to_string(),
            password_hash: "hash".to_string(),
            first_name: "Test".to_string(),
            last_name: "User".to_string(),
            date_of_birth: chrono::NaiveDate::from_ymd_opt(1990, 1, 1).unwrap(),
            phone: None,
            address: None,
            is_verified: true,
            is_active: true,
            created_at: Utc::now(),
            updated_at: Utc::now(),
            last_login: None,
            login_count: 0,
            failed_login_attempts: 0,
            locked_until: None,
        };

        let session_id = "test_session_456";
        auth_service.create_session(&user, session_id, "127.0.0.1", "Mozilla/5.0");

        let session = auth_service.get_session(session_id).unwrap();
        assert_eq!(session.user_id, user.id);
        assert_eq!(session.email, user.email);
        assert!(session.is_active);

        auth_service.invalidate_session(session_id);
        assert!(auth_service.get_session(session_id).is_none());
    }
}

/// Standalone JWT verification function for use in handlers
/// This is a convenience function that doesn't require AuthService
pub fn verify_jwt(token: &str, secret: &str) -> AppResult<Claims> {
    let key = DecodingKey::from_secret(secret.as_ref());
    let validation = Validation::default();

    let token_data = decode::<Claims>(token, &key, &validation)
        .map_err(|e| AppError::JWT(e))?;

    Ok(token_data.claims)
}
