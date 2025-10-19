use crate::config::AppConfig;
use crate::crypto::CryptoService;
use crate::errors::{AppError, AppResult};
use crate::rates::RateLimiters;
use actix_web::{web, HttpRequest, HttpResponse};
use bigdecimal::BigDecimal;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use std::str::FromStr;
use tracing::{error, info};
use uuid::Uuid;
use validator::Validate;

#[derive(Debug, Deserialize, Validate)]
pub struct DepositRequest {
    #[validate(range(min = 10.0, max = 10000.0))]
    pub amount: f64,
}

#[derive(Debug, Deserialize, Validate)]
pub struct WithdrawRequest {
    #[validate(range(min = 10.0, max = 10000.0))]
    pub amount: f64,
}

#[derive(Debug, Serialize)]
pub struct BalanceResponse {
    pub balance: BigDecimal,
    pub currency: String,
}

#[derive(Debug, Serialize)]
pub struct TransactionResponse {
    pub id: Uuid,
    pub transaction_type: String,
    pub amount: BigDecimal,
    pub status: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

pub async fn get_balance(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
) -> AppResult<HttpResponse> {
    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    let crypto_service = CryptoService::from_string(&config.encryption_key);

    let wallet: (String, String) = sqlx::query_as(
        "SELECT encrypted_balance, encryption_iv FROM wallets WHERE user_id = $1"
    )
    .bind(user_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch wallet: {}", e);
        AppError::Database(e)
    })?;

    let balance = crypto_service.decrypt_balance(&wallet.0, &wallet.1)?;

    Ok(HttpResponse::Ok().json(BalanceResponse {
        balance,
        currency: "USD".to_string(),
    }))
}

pub async fn deposit(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
    rate_limiters: web::Data<RateLimiters>,
    body: web::Json<DepositRequest>,
) -> AppResult<HttpResponse> {
    body.validate().map_err(|e| AppError::Validation(e.to_string()))?;

    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    // Check rate limit
    rate_limiters.check_deposit_limit(user_id)?;

    let crypto_service = CryptoService::from_string(&config.encryption_key);
    let amount = BigDecimal::from_str(&body.amount.to_string()).unwrap();

    // Start transaction
    let mut tx = pool.begin().await.map_err(|e| {
        error!("Failed to start transaction: {}", e);
        AppError::Database(e)
    })?;

    // Get current balance
    let wallet: (String, String) = sqlx::query_as(
        "SELECT encrypted_balance, encryption_iv FROM wallets WHERE user_id = $1"
    )
    .bind(user_id)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| {
        error!("Failed to fetch wallet: {}", e);
        AppError::Database(e)
    })?;

    let current_balance = crypto_service.decrypt_balance(&wallet.0, &wallet.1)?;
    let new_balance = current_balance + &amount;
    let (encrypted_balance, iv) = crypto_service.encrypt_balance(&new_balance)?;

    // Update wallet
    sqlx::query(
        "UPDATE wallets SET encrypted_balance = $1, encryption_iv = $2, updated_at = NOW() WHERE user_id = $3"
    )
    .bind(&encrypted_balance)
    .bind(&iv)
    .bind(user_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| {
        error!("Failed to update wallet: {}", e);
        AppError::Database(e)
    })?;

    // Create transaction record
    let transaction_id = Uuid::new_v4();
    sqlx::query(
        r#"
        INSERT INTO transactions (id, user_id, transaction_type, amount, status, created_at)
        VALUES ($1, $2, 'deposit', $3, 'completed', NOW())
        "#
    )
    .bind(transaction_id)
    .bind(user_id)
    .bind(&amount)
    .execute(&mut *tx)
    .await
    .map_err(|e| {
        error!("Failed to create transaction: {}", e);
        AppError::Database(e)
    })?;

    tx.commit().await.map_err(|e| {
        error!("Failed to commit transaction: {}", e);
        AppError::Database(e)
    })?;

    info!("Deposit successful: user_id={}, amount={}", user_id, amount);

    Ok(HttpResponse::Ok().json(BalanceResponse {
        balance: new_balance,
        currency: "USD".to_string(),
    }))
}

pub async fn withdraw(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
    rate_limiters: web::Data<RateLimiters>,
    body: web::Json<WithdrawRequest>,
) -> AppResult<HttpResponse> {
    body.validate().map_err(|e| AppError::Validation(e.to_string()))?;

    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    // Check rate limit
    rate_limiters.check_withdraw_limit(user_id)?;

    let crypto_service = CryptoService::from_string(&config.encryption_key);
    let amount = BigDecimal::from_str(&body.amount.to_string()).unwrap();

    // Start transaction
    let mut tx = pool.begin().await.map_err(|e| {
        error!("Failed to start transaction: {}", e);
        AppError::Database(e)
    })?;

    // Get current balance
    let wallet: (String, String) = sqlx::query_as(
        "SELECT encrypted_balance, encryption_iv FROM wallets WHERE user_id = $1"
    )
    .bind(user_id)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| {
        error!("Failed to fetch wallet: {}", e);
        AppError::Database(e)
    })?;

    let current_balance = crypto_service.decrypt_balance(&wallet.0, &wallet.1)?;

    if current_balance < amount {
        return Err(AppError::InsufficientFunds);
    }

    let new_balance = current_balance - &amount;
    let (encrypted_balance, iv) = crypto_service.encrypt_balance(&new_balance)?;

    // Update wallet
    sqlx::query(
        "UPDATE wallets SET encrypted_balance = $1, encryption_iv = $2, updated_at = NOW() WHERE user_id = $3"
    )
    .bind(&encrypted_balance)
    .bind(&iv)
    .bind(user_id)
    .execute(&mut *tx)
    .await
    .map_err(|e| {
        error!("Failed to update wallet: {}", e);
        AppError::Database(e)
    })?;

    // Create transaction record
    let transaction_id = Uuid::new_v4();
    sqlx::query(
        r#"
        INSERT INTO transactions (id, user_id, transaction_type, amount, status, created_at)
        VALUES ($1, $2, 'withdrawal', $3, 'completed', NOW())
        "#
    )
    .bind(transaction_id)
    .bind(user_id)
    .bind(&amount)
    .execute(&mut *tx)
    .await
    .map_err(|e| {
        error!("Failed to create transaction: {}", e);
        AppError::Database(e)
    })?;

    tx.commit().await.map_err(|e| {
        error!("Failed to commit transaction: {}", e);
        AppError::Database(e)
    })?;

    info!("Withdrawal successful: user_id={}, amount={}", user_id, amount);

    Ok(HttpResponse::Ok().json(BalanceResponse {
        balance: new_balance,
        currency: "USD".to_string(),
    }))
}

pub async fn get_transactions(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    let transactions: Vec<(Uuid, String, BigDecimal, String, chrono::DateTime<chrono::Utc>)> = sqlx::query_as(
        r#"
        SELECT id, transaction_type, amount, status, created_at
        FROM transactions
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT 50
        "#
    )
    .bind(user_id)
    .fetch_all(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch transactions: {}", e);
        AppError::Database(e)
    })?;

    let transaction_responses: Vec<TransactionResponse> = transactions
        .into_iter()
        .map(|(id, transaction_type, amount, status, created_at)| TransactionResponse {
            id,
            transaction_type,
            amount,
            status,
            created_at,
        })
        .collect();

    Ok(HttpResponse::Ok().json(transaction_responses))
}
