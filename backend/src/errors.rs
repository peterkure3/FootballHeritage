#![allow(dead_code)]
use actix_web::{error::ResponseError, http::StatusCode, HttpResponse};
use serde_json::json;
use sqlx::postgres::PgDatabaseError;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Authentication error: {0}")]
    Authentication(String),

    #[error("Authorization error: {0}")]
    Authorization(String),

    #[error("Rate limit exceeded")]
    RateLimit,

    #[error("Rate limit exceeded: {0}")]
    RateLimitExceeded(String),

    #[error("Internal error: {0}")]
    Internal(String),

    #[error("Account locked")]
    AccountLocked,

    #[error("Insufficient funds")]
    InsufficientFunds,

    #[error("Bet limit exceeded")]
    BetLimitExceeded,

    #[error("Event not found")]
    EventNotFound,

    #[error("Bet not found")]
    BetNotFound,

    #[error("User not found")]
    UserNotFound,

    #[error("Invalid bet amount")]
    InvalidBetAmount,

    #[error("Odds have changed")]
    OddsChanged,

    #[error("Event has started or ended")]
    EventNotAvailable,

    #[error("Encryption error: {0}")]
    Encryption(String),

    #[error("JWT error: {0}")]
    JWT(#[from] jsonwebtoken::errors::Error),

    #[error("IO error: {0}")]
    IO(#[from] std::io::Error),

    #[error("Configuration error: {0}")]
    Configuration(String),

    #[error("Age verification failed - user must be 21 or older")]
    AgeVerificationFailed,

    #[error("Self-exclusion active")]
    SelfExclusionActive,

    #[error("Responsible gambling limit exceeded: {0}")]
    ResponsibleGamblingLimit(String),

    #[error("Suspicious activity detected")]
    SuspiciousActivity,

    #[error("Session expired")]
    SessionExpired,

    #[error("Invalid CSRF token")]
    InvalidCSRFToken,

    #[error("Too many login attempts")]
    TooManyLoginAttempts,

    #[error("Password too weak")]
    PasswordTooWeak,

    #[error("Email already registered")]
    EmailAlreadyRegistered,

    #[error("Invalid email format")]
    InvalidEmailFormat,

    #[error("Wallet operation failed: {0}")]
    WalletOperation(String),

    #[error("Internal server error")]
    InternalServerError,
}

impl AppError {
    pub fn is_fraud_related(&self) -> bool {
        matches!(self,
            AppError::SuspiciousActivity |
            AppError::RateLimit |
            AppError::RateLimitExceeded(_) |
            AppError::TooManyLoginAttempts
        )
    }

    pub fn requires_logging(&self) -> bool {
        matches!(self,
            AppError::Authentication(_) |
            AppError::Authorization(_) |
            AppError::SuspiciousActivity |
            AppError::InsufficientFunds |
            AppError::AccountLocked |
            AppError::TooManyLoginAttempts
        )
    }

    pub fn client_safe_message(&self) -> String {
        match self {
            AppError::Database(_) => "Database operation failed".to_string(),
            AppError::Validation(msg) => format!("Validation failed: {}", msg),
            AppError::Authentication(_) => "Authentication failed".to_string(),
            AppError::Authorization(_) => "Access denied".to_string(),
            AppError::RateLimit => "Too many requests. Please try again later".to_string(),
            AppError::RateLimitExceeded(msg) => format!("Rate limit exceeded: {}", msg),
            AppError::Internal(msg) => format!("Internal error: {}", msg),
            AppError::AccountLocked => "Account temporarily locked. Please try again later".to_string(),
            AppError::InsufficientFunds => "Insufficient funds for this operation".to_string(),
            AppError::BetLimitExceeded => "Bet amount exceeds limit".to_string(),
            AppError::EventNotFound => "Event not found".to_string(),
            AppError::BetNotFound => "Bet not found".to_string(),
            AppError::UserNotFound => "User not found".to_string(),
            AppError::InvalidBetAmount => "Invalid bet amount".to_string(),
            AppError::OddsChanged => "Odds have changed since you last viewed them".to_string(),
            AppError::EventNotAvailable => "This event is no longer available for betting".to_string(),
            AppError::Encryption(_) => "Encryption error occurred".to_string(),
            AppError::JWT(_) => "Authentication token error".to_string(),
            AppError::IO(_) => "File operation failed".to_string(),
            AppError::Configuration(_) => "Server configuration error".to_string(),
            AppError::AgeVerificationFailed => "You must be 21 or older to register".to_string(),
            AppError::SelfExclusionActive => "Account is currently self-excluded".to_string(),
            AppError::ResponsibleGamblingLimit(msg) => format!("Responsible gambling limit: {}", msg),
            AppError::SuspiciousActivity => "Suspicious activity detected. Action blocked".to_string(),
            AppError::SessionExpired => "Session has expired".to_string(),
            AppError::InvalidCSRFToken => "Invalid security token".to_string(),
            AppError::TooManyLoginAttempts => "Too many failed login attempts".to_string(),
            AppError::PasswordTooWeak => "Password does not meet security requirements".to_string(),
            AppError::EmailAlreadyRegistered => "Email is already registered".to_string(),
            AppError::InvalidEmailFormat => "Invalid email format".to_string(),
            AppError::WalletOperation(msg) => format!("Wallet operation failed: {}", msg),
            AppError::InternalServerError => "Internal server error occurred".to_string(),
        }
    }
}

impl ResponseError for AppError {
    fn error_response(&self) -> HttpResponse {
        let status_code = self.status_code();
        let error_response = json!({
            "error": {
                "code": status_code.as_u16(),
                "message": self.client_safe_message(),
                "type": self.error_type()
            }
        });

        HttpResponse::build(status_code).json(error_response)
    }

    fn status_code(&self) -> StatusCode {
        match self {
            AppError::Database(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::Validation(_) => StatusCode::BAD_REQUEST,
            AppError::Authentication(_) => StatusCode::UNAUTHORIZED,
            AppError::Authorization(_) => StatusCode::FORBIDDEN,
            AppError::RateLimit => StatusCode::TOO_MANY_REQUESTS,
            AppError::RateLimitExceeded(_) => StatusCode::TOO_MANY_REQUESTS,
            AppError::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::AccountLocked => StatusCode::LOCKED,
            AppError::InsufficientFunds => StatusCode::PAYMENT_REQUIRED,
            AppError::BetLimitExceeded => StatusCode::BAD_REQUEST,
            AppError::EventNotFound => StatusCode::NOT_FOUND,
            AppError::BetNotFound => StatusCode::NOT_FOUND,
            AppError::UserNotFound => StatusCode::NOT_FOUND,
            AppError::InvalidBetAmount => StatusCode::BAD_REQUEST,
            AppError::OddsChanged => StatusCode::CONFLICT,
            AppError::EventNotAvailable => StatusCode::GONE,
            AppError::Encryption(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::JWT(_) => StatusCode::UNAUTHORIZED,
            AppError::IO(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::Configuration(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::AgeVerificationFailed => StatusCode::BAD_REQUEST,
            AppError::SelfExclusionActive => StatusCode::FORBIDDEN,
            AppError::ResponsibleGamblingLimit(_) => StatusCode::BAD_REQUEST,
            AppError::SuspiciousActivity => StatusCode::FORBIDDEN,
            AppError::SessionExpired => StatusCode::UNAUTHORIZED,
            AppError::InvalidCSRFToken => StatusCode::FORBIDDEN,
            AppError::TooManyLoginAttempts => StatusCode::TOO_MANY_REQUESTS,
            AppError::PasswordTooWeak => StatusCode::BAD_REQUEST,
            AppError::EmailAlreadyRegistered => StatusCode::CONFLICT,
            AppError::InvalidEmailFormat => StatusCode::BAD_REQUEST,
            AppError::WalletOperation(_) => StatusCode::INTERNAL_SERVER_ERROR,
            AppError::InternalServerError => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}

impl AppError {
    fn error_type(&self) -> &'static str {
        match self {
            AppError::Database(_) => "DATABASE_ERROR",
            AppError::Validation(_) => "VALIDATION_ERROR",
            AppError::Authentication(_) => "AUTHENTICATION_ERROR",
            AppError::Authorization(_) => "AUTHORIZATION_ERROR",
            AppError::RateLimit => "RATE_LIMIT_ERROR",
            AppError::RateLimitExceeded(_) => "RATE_LIMIT_EXCEEDED",
            AppError::Internal(_) => "INTERNAL_ERROR",
            AppError::AccountLocked => "ACCOUNT_LOCKED",
            AppError::InsufficientFunds => "INSUFFICIENT_FUNDS",
            AppError::BetLimitExceeded => "BET_LIMIT_EXCEEDED",
            AppError::EventNotFound => "EVENT_NOT_FOUND",
            AppError::BetNotFound => "BET_NOT_FOUND",
            AppError::UserNotFound => "USER_NOT_FOUND",
            AppError::InvalidBetAmount => "INVALID_BET_AMOUNT",
            AppError::OddsChanged => "ODDS_CHANGED",
            AppError::EventNotAvailable => "EVENT_NOT_AVAILABLE",
            AppError::Encryption(_) => "ENCRYPTION_ERROR",
            AppError::JWT(_) => "JWT_ERROR",
            AppError::IO(_) => "IO_ERROR",
            AppError::Configuration(_) => "CONFIGURATION_ERROR",
            AppError::AgeVerificationFailed => "AGE_VERIFICATION_FAILED",
            AppError::SelfExclusionActive => "SELF_EXCLUSION_ACTIVE",
            AppError::ResponsibleGamblingLimit(_) => "RESPONSIBLE_GAMBLING_LIMIT",
            AppError::SuspiciousActivity => "SUSPICIOUS_ACTIVITY",
            AppError::SessionExpired => "SESSION_EXPIRED",
            AppError::InvalidCSRFToken => "INVALID_CSRF_TOKEN",
            AppError::TooManyLoginAttempts => "TOO_MANY_LOGIN_ATTEMPTS",
            AppError::PasswordTooWeak => "PASSWORD_TOO_WEAK",
            AppError::EmailAlreadyRegistered => "EMAIL_ALREADY_REGISTERED",
            AppError::InvalidEmailFormat => "INVALID_EMAIL_FORMAT",
            AppError::WalletOperation(_) => "WALLET_OPERATION_ERROR",
            AppError::InternalServerError => "INTERNAL_SERVER_ERROR",
        }
    }
}

// Helper function to convert PostgreSQL constraint violations to AppError
pub fn handle_postgres_error(err: sqlx::Error) -> AppError {
    if let Some(db_error) = err.as_database_error() {
        let pg_error = db_error.downcast_ref::<PgDatabaseError>();
        return match pg_error.code() {
            "23505" => AppError::EmailAlreadyRegistered, // unique_violation
            "23503" => AppError::Validation("Foreign key constraint violation".to_string()),
            "23514" => AppError::Validation("Check constraint violation".to_string()),
            "23502" => AppError::Validation("Not null constraint violation".to_string()),
            _ => AppError::Database(err),
        };
    }
    AppError::Database(err)
}

// Custom result type for the application
pub type AppResult<T> = Result<T, AppError>;

// Utility function for validation errors
pub fn validation_error(field: &str, message: &str) -> AppError {
    AppError::Validation(format!("{}: {}", field, message))
}

// API Error type for chat handler and other API endpoints
#[derive(Debug, Error)]
pub enum ApiError {
    #[error("Bad request: {0}")]
    BadRequest(String),

    #[error("Unauthorized: {0}")]
    Unauthorized(String),

    #[error("Internal server error: {0}")]
    InternalServerError(String),

    #[error("Service unavailable: {0}")]
    ServiceUnavailable(String),
}

impl ResponseError for ApiError {
    fn error_response(&self) -> HttpResponse {
        let status_code = self.status_code();
        let error_response = json!({
            "error": match self {
                ApiError::BadRequest(_) => "BAD_REQUEST",
                ApiError::Unauthorized(_) => "UNAUTHORIZED",
                ApiError::InternalServerError(_) => "INTERNAL_SERVER_ERROR",
                ApiError::ServiceUnavailable(_) => "SERVICE_UNAVAILABLE",
            },
            "message": self.to_string(),
        });

        HttpResponse::build(status_code).json(error_response)
    }

    fn status_code(&self) -> StatusCode {
        match self {
            ApiError::BadRequest(_) => StatusCode::BAD_REQUEST,
            ApiError::Unauthorized(_) => StatusCode::UNAUTHORIZED,
            ApiError::InternalServerError(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ApiError::ServiceUnavailable(_) => StatusCode::SERVICE_UNAVAILABLE,
        }
    }
}
