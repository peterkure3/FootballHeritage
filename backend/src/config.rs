#![allow(dead_code)]
use serde::Deserialize;
use std::env;
use anyhow::Result;

#[derive(Debug, Clone, Deserialize)]
pub struct AppConfig {
    pub app_env: String,
    pub database_url: String,
    pub jwt_secret: String,
    pub jwt_expiration_hours: u64,
    pub encryption_key: String,
    pub host: String,
    pub port: u16,
    pub https_enabled: bool,
    pub tls_cert_path: String,
    pub tls_key_path: String,
    pub bet_rate_limit_per_minute: u32,
    pub login_rate_limit_per_minute: u32,
    pub register_rate_limit_per_hour: u32,
    pub bcrypt_cost: u32,
    pub session_timeout_minutes: u64,
    pub max_login_attempts: u32,
    pub account_lock_minutes: u64,
    pub default_daily_loss_limit: f64,
    pub default_weekly_loss_limit: f64,
    pub default_monthly_loss_limit: f64,
    pub default_daily_bet_limit: f64,
    pub default_weekly_bet_limit: f64,
    pub default_monthly_bet_limit: f64,
    pub default_max_single_bet: f64,
    pub log_level: String,
    pub fraud_alert_email: String,
    pub allowed_origins: Vec<String>,
    pub metrics_enabled: bool,
    pub health_check_interval_seconds: u64,
}

impl AppConfig {
    pub fn from_env() -> Result<Self> {
        let allowed_origins: Vec<String> = env::var("ALLOWED_ORIGINS")
            .unwrap_or_else(|_| "http://localhost:3000".to_string())
            .split(',')
            .map(|s| s.trim().to_string())
            .collect();

        let https_enabled: bool = env::var("HTTPS_ENABLED")
            .unwrap_or_else(|_| "false".to_string())
            .parse()
            .map_err(|_| anyhow::anyhow!("Invalid HTTPS_ENABLED"))?;

        let tls_cert_path = if https_enabled {
            env::var("TLS_CERT_PATH")
                .map_err(|_| anyhow::anyhow!("TLS_CERT_PATH must be set when HTTPS is enabled"))?
        } else {
            env::var("TLS_CERT_PATH").unwrap_or_else(|_| "./certs/server.crt".to_string())
        };

        let tls_key_path = if https_enabled {
            env::var("TLS_KEY_PATH")
                .map_err(|_| anyhow::anyhow!("TLS_KEY_PATH must be set when HTTPS is enabled"))?
        } else {
            env::var("TLS_KEY_PATH").unwrap_or_else(|_| "./certs/server.key".to_string())
        };

        let config = Self {
            app_env: env::var("APP_ENV").unwrap_or_else(|_| "development".to_string()),
            database_url: env::var("DATABASE_URL")
                .map_err(|_| anyhow::anyhow!("DATABASE_URL must be set"))?,
            jwt_secret: env::var("JWT_SECRET")
                .map_err(|_| anyhow::anyhow!("JWT_SECRET must be set"))?,
            jwt_expiration_hours: env::var("JWT_EXPIRATION_HOURS")
                .unwrap_or_else(|_| "24".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid JWT_EXPIRATION_HOURS"))?,
            encryption_key: env::var("ENCRYPTION_KEY")
                .map_err(|_| anyhow::anyhow!("ENCRYPTION_KEY must be set"))?,
            host: env::var("HOST").unwrap_or_else(|_| "127.0.0.1".to_string()),
            port: env::var("PORT")
                .unwrap_or_else(|_| "8080".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid PORT"))?,
            https_enabled,
            tls_cert_path,
            tls_key_path,
            bet_rate_limit_per_minute: env::var("BET_RATE_LIMIT_PER_MINUTE")
                .unwrap_or_else(|_| "5".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid BET_RATE_LIMIT_PER_MINUTE"))?,
            login_rate_limit_per_minute: env::var("LOGIN_RATE_LIMIT_PER_MINUTE")
                .unwrap_or_else(|_| "10".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid LOGIN_RATE_LIMIT_PER_MINUTE"))?,
            register_rate_limit_per_hour: env::var("REGISTER_RATE_LIMIT_PER_HOUR")
                .unwrap_or_else(|_| "5".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid REGISTER_RATE_LIMIT_PER_HOUR"))?,
            bcrypt_cost: env::var("BCRYPT_COST")
                .unwrap_or_else(|_| "12".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid BCRYPT_COST"))?,
            session_timeout_minutes: env::var("SESSION_TIMEOUT_MINUTES")
                .unwrap_or_else(|_| "30".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid SESSION_TIMEOUT_MINUTES"))?,
            max_login_attempts: env::var("MAX_LOGIN_ATTEMPTS")
                .unwrap_or_else(|_| "5".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid MAX_LOGIN_ATTEMPTS"))?,
            account_lock_minutes: env::var("ACCOUNT_LOCK_MINUTES")
                .unwrap_or_else(|_| "15".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid ACCOUNT_LOCK_MINUTES"))?,
            default_daily_loss_limit: env::var("DEFAULT_DAILY_LOSS_LIMIT")
                .unwrap_or_else(|_| "1000.00".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid DEFAULT_DAILY_LOSS_LIMIT"))?,
            default_weekly_loss_limit: env::var("DEFAULT_WEEKLY_LOSS_LIMIT")
                .unwrap_or_else(|_| "5000.00".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid DEFAULT_WEEKLY_LOSS_LIMIT"))?,
            default_monthly_loss_limit: env::var("DEFAULT_MONTHLY_LOSS_LIMIT")
                .unwrap_or_else(|_| "15000.00".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid DEFAULT_MONTHLY_LOSS_LIMIT"))?,
            default_daily_bet_limit: env::var("DEFAULT_DAILY_BET_LIMIT")
                .unwrap_or_else(|_| "2000.00".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid DEFAULT_DAILY_BET_LIMIT"))?,
            default_weekly_bet_limit: env::var("DEFAULT_WEEKLY_BET_LIMIT")
                .unwrap_or_else(|_| "10000.00".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid DEFAULT_WEEKLY_BET_LIMIT"))?,
            default_monthly_bet_limit: env::var("DEFAULT_MONTHLY_BET_LIMIT")
                .unwrap_or_else(|_| "30000.00".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid DEFAULT_MONTHLY_BET_LIMIT"))?,
            default_max_single_bet: env::var("DEFAULT_MAX_SINGLE_BET")
                .unwrap_or_else(|_| "500.00".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid DEFAULT_MAX_SINGLE_BET"))?,
            log_level: env::var("LOG_LEVEL").unwrap_or_else(|_| "info".to_string()),
            fraud_alert_email: env::var("FRAUD_ALERT_EMAIL")
                .unwrap_or_else(|_| "security@footballheritage.com".to_string()),
            allowed_origins,
            metrics_enabled: env::var("METRICS_ENABLED")
                .unwrap_or_else(|_| "true".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid METRICS_ENABLED"))?,
            health_check_interval_seconds: env::var("HEALTH_CHECK_INTERVAL_SECONDS")
                .unwrap_or_else(|_| "30".to_string())
                .parse()
                .map_err(|_| anyhow::anyhow!("Invalid HEALTH_CHECK_INTERVAL_SECONDS"))?,
        };

        if !config.validate_jwt_secret() {
            return Err(anyhow::anyhow!("JWT_SECRET must be at least 32 characters"));
        }

        Ok(config)
    }

    pub fn is_development(&self) -> bool {
        self.app_env.eq_ignore_ascii_case("development")
    }

    pub fn validate_jwt_secret(&self) -> bool {
        self.jwt_secret.len() >= 32
    }

    pub fn validate_encryption_key(&self) -> bool {
        self.encryption_key.len() == 32
    }
}
