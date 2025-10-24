use crate::auth::AuthService;
use crate::config::AppConfig;
use crate::crypto::CryptoService;
use crate::errors::{AppError, AppResult};
use crate::models::{LoginRequest, User};
use crate::rates::RateLimiters;
use crate::utils::{extract_ip_address, extract_user_agent, generate_session_id, validate_age};
use actix_web::{web, HttpRequest, HttpResponse};
use argon2::{Argon2, PasswordHash, PasswordHasher, PasswordVerifier};
use argon2::password_hash::{rand_core::OsRng, SaltString};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use tracing::{error, info};
use uuid::Uuid;
use validator::Validate;

#[derive(Debug, Deserialize, Validate)]
pub struct RegisterRequestHandler {
    #[validate(email)]
    pub email: String,
    #[validate(length(min = 8))]
    pub password: String,
    pub first_name: String,
    pub last_name: String,
    pub date_of_birth: chrono::NaiveDate,
    pub phone: Option<String>,
    pub address: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct AuthResponse {
    pub token: String,
    pub user: UserResponse,
}

#[derive(Debug, Serialize)]
pub struct UserResponse {
    pub id: Uuid,
    pub email: String,
    pub first_name: String,
    pub last_name: String,
    pub is_verified: bool,
}

pub async fn register(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
    auth_service: web::Data<AuthService>,
    rate_limiters: web::Data<RateLimiters>,
    body: web::Json<RegisterRequestHandler>,
) -> AppResult<HttpResponse> {
    // Validate input
    body.validate().map_err(|e| AppError::Validation(e.to_string()))?;

    // Check rate limit
    let ip_address = extract_ip_address(&req);
    rate_limiters.check_register_limit(&ip_address)?;

    // Validate age (21+)
    validate_age(&body.date_of_birth)?;

    // Check if user already exists
    let existing_user = sqlx::query_as::<_, User>(
        "SELECT * FROM users WHERE email = $1"
    )
    .bind(&body.email)
    .fetch_optional(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Database error checking existing user: {}", e);
        AppError::Database(e)
    })?;

    if existing_user.is_some() {
        return Err(AppError::Validation("Email already registered".to_string()));
    }

    // Hash password with Argon2
    let salt = SaltString::generate(&mut OsRng);
    let argon2 = Argon2::default();
    let password_hash = argon2
        .hash_password(body.password.as_bytes(), &salt)
        .map_err(|e| {
            error!("Failed to hash password: {}", e);
            AppError::Internal("Password hashing failed".to_string())
        })?
        .to_string();

    // Create user
    let user_id = Uuid::new_v4();
    let user = sqlx::query_as::<_, User>(
        r#"
        INSERT INTO users (id, email, password_hash, first_name, last_name, date_of_birth, phone, address, is_verified, is_active, created_at, updated_at, login_count, failed_login_attempts)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, false, true, NOW(), NOW(), 0, 0)
        RETURNING *
        "#
    )
    .bind(user_id)
    .bind(&body.email)
    .bind(&password_hash)
    .bind(&body.first_name)
    .bind(&body.last_name)
    .bind(&body.date_of_birth)
    .bind(&body.phone)
    .bind(&body.address)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to create user: {}", e);
        AppError::Database(e)
    })?;

    // Create wallet with zero balance
    let crypto_service = CryptoService::from_string(&config.encryption_key);
    let zero_balance = bigdecimal::BigDecimal::from(0);
    let (encrypted_balance, iv) = crypto_service.encrypt_balance(&zero_balance)?;

    sqlx::query(
        r#"
        INSERT INTO wallets (id, user_id, encrypted_balance, encryption_iv, created_at, updated_at)
        VALUES ($1, $2, $3, $4, NOW(), NOW())
        "#
    )
    .bind(Uuid::new_v4())
    .bind(user_id)
    .bind(&encrypted_balance)
    .bind(&iv)
    .execute(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to create wallet: {}", e);
        AppError::Database(e)
    })?;

    // Create default gambling limits
    sqlx::query(
        r#"
        INSERT INTO gambling_limits (id, user_id, daily_bet_limit, weekly_bet_limit, monthly_bet_limit, daily_loss_limit, weekly_loss_limit, monthly_loss_limit, max_single_bet, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
        "#
    )
    .bind(Uuid::new_v4())
    .bind(user_id)
    .bind(config.default_daily_bet_limit)
    .bind(config.default_weekly_bet_limit)
    .bind(config.default_monthly_bet_limit)
    .bind(config.default_daily_loss_limit)
    .bind(config.default_weekly_loss_limit)
    .bind(config.default_monthly_loss_limit)
    .bind(config.default_max_single_bet)
    .execute(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to create gambling limits: {}", e);
        AppError::Database(e)
    })?;

    info!("User registered successfully: {}", user.email);

    // Generate JWT token
    let session_id = generate_session_id();
    let user_agent = extract_user_agent(&req);

    auth_service.create_session(&user, &session_id, &ip_address, &user_agent);
    let token = auth_service.generate_token(&user, &session_id)?;

    Ok(HttpResponse::Created().json(AuthResponse {
        token,
        user: UserResponse {
            id: user.id,
            email: user.email,
            first_name: user.first_name,
            last_name: user.last_name,
            is_verified: user.is_verified,
        },
    }))
}

pub async fn login(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
    auth_service: web::Data<AuthService>,
    rate_limiters: web::Data<RateLimiters>,
    body: web::Json<LoginRequest>,
) -> AppResult<HttpResponse> {
    // Check rate limit
    let ip_address = extract_ip_address(&req);
    rate_limiters.check_login_limit(&ip_address)?;

    // Fetch user
    let user = sqlx::query_as::<_, User>(
        "SELECT * FROM users WHERE email = $1"
    )
    .bind(&body.email)
    .fetch_optional(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Database error fetching user: {}", e);
        AppError::Database(e)
    })?
    .ok_or_else(|| AppError::Authentication("Invalid credentials".to_string()))?;

    // Check if account is locked
    if let Some(locked_until) = user.locked_until {
        if locked_until > Utc::now() {
            return Err(AppError::AccountLocked);
        }
    }

    // Verify password
    let parsed_hash = PasswordHash::new(&user.password_hash)
        .map_err(|e| {
            error!("Failed to parse password hash: {}", e);
            AppError::Internal("Authentication error".to_string())
        })?;

    let argon2 = Argon2::default();
    if argon2.verify_password(body.password.as_bytes(), &parsed_hash).is_err() {
        // Increment failed login attempts
        sqlx::query(
            "UPDATE users SET failed_login_attempts = failed_login_attempts + 1, updated_at = NOW() WHERE id = $1"
        )
        .bind(user.id)
        .execute(pool.as_ref())
        .await
        .ok();

        // Lock account if max attempts exceeded
        if user.failed_login_attempts + 1 >= config.max_login_attempts as i32 {
            let lock_duration = chrono::Duration::minutes(config.account_lock_minutes as i64);
            sqlx::query(
                "UPDATE users SET locked_until = $1, updated_at = NOW() WHERE id = $2"
            )
            .bind(Utc::now() + lock_duration)
            .bind(user.id)
            .execute(pool.as_ref())
            .await
            .ok();
        }

        return Err(AppError::Authentication("Invalid credentials".to_string()));
    }

    // Reset failed login attempts and update last login
    sqlx::query(
        "UPDATE users SET failed_login_attempts = 0, login_count = login_count + 1, last_login = NOW(), updated_at = NOW() WHERE id = $1"
    )
    .bind(user.id)
    .execute(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to update user login info: {}", e);
        AppError::Database(e)
    })?;

    info!("User logged in successfully: {}", user.email);

    // Generate JWT token
    let session_id = generate_session_id();
    let user_agent = extract_user_agent(&req);

    auth_service.create_session(&user, &session_id, &ip_address, &user_agent);
    let token = auth_service.generate_token(&user, &session_id)?;

    Ok(HttpResponse::Ok().json(AuthResponse {
        token,
        user: UserResponse {
            id: user.id,
            email: user.email,
            first_name: user.first_name,
            last_name: user.last_name,
            is_verified: user.is_verified,
        },
    }))
}

pub async fn logout(
    _req: HttpRequest,
    _pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    // In a real implementation, invalidate the session
    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "Logged out successfully"
    })))
}

pub async fn refresh(
    _req: HttpRequest,
    _pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    // Implement token refresh logic
    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "Token refreshed"
    })))
}

pub async fn verify_email(
    _req: HttpRequest,
    _pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    // Implement email verification logic
    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "Email verified"
    })))
}
