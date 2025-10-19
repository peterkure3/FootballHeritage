use crate::errors::{AppError, AppResult};
use actix_web::{web, HttpRequest, HttpResponse};
use bigdecimal::BigDecimal;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use tracing::error;
use uuid::Uuid;

#[derive(Debug, Serialize)]
pub struct GamblingLimitsResponse {
    pub daily_bet_limit: Option<BigDecimal>,
    pub weekly_bet_limit: Option<BigDecimal>,
    pub monthly_bet_limit: Option<BigDecimal>,
    pub daily_loss_limit: Option<BigDecimal>,
    pub weekly_loss_limit: Option<BigDecimal>,
    pub monthly_loss_limit: Option<BigDecimal>,
    pub max_single_bet: Option<BigDecimal>,
    pub self_excluded_until: Option<DateTime<Utc>>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateLimitsRequest {
    pub daily_bet_limit: Option<BigDecimal>,
    pub weekly_bet_limit: Option<BigDecimal>,
    pub monthly_bet_limit: Option<BigDecimal>,
    pub daily_loss_limit: Option<BigDecimal>,
    pub weekly_loss_limit: Option<BigDecimal>,
    pub monthly_loss_limit: Option<BigDecimal>,
    pub max_single_bet: Option<BigDecimal>,
}

#[derive(Debug, Deserialize)]
pub struct SelfExcludeRequest {
    pub duration_days: i64,
}

pub async fn get_limits(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    let limits: (
        Option<BigDecimal>,
        Option<BigDecimal>,
        Option<BigDecimal>,
        Option<BigDecimal>,
        Option<BigDecimal>,
        Option<BigDecimal>,
        Option<BigDecimal>,
        Option<DateTime<Utc>>,
    ) = sqlx::query_as(
        r#"
        SELECT daily_bet_limit, weekly_bet_limit, monthly_bet_limit,
               daily_loss_limit, weekly_loss_limit, monthly_loss_limit,
               max_single_bet, self_excluded_until
        FROM gambling_limits
        WHERE user_id = $1
        "#
    )
    .bind(user_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch gambling limits: {}", e);
        AppError::Database(e)
    })?;

    Ok(HttpResponse::Ok().json(GamblingLimitsResponse {
        daily_bet_limit: limits.0,
        weekly_bet_limit: limits.1,
        monthly_bet_limit: limits.2,
        daily_loss_limit: limits.3,
        weekly_loss_limit: limits.4,
        monthly_loss_limit: limits.5,
        max_single_bet: limits.6,
        self_excluded_until: limits.7,
    }))
}

pub async fn update_limits(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
    body: web::Json<UpdateLimitsRequest>,
) -> AppResult<HttpResponse> {
    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    sqlx::query(
        r#"
        UPDATE gambling_limits
        SET daily_bet_limit = COALESCE($1, daily_bet_limit),
            weekly_bet_limit = COALESCE($2, weekly_bet_limit),
            monthly_bet_limit = COALESCE($3, monthly_bet_limit),
            daily_loss_limit = COALESCE($4, daily_loss_limit),
            weekly_loss_limit = COALESCE($5, weekly_loss_limit),
            monthly_loss_limit = COALESCE($6, monthly_loss_limit),
            max_single_bet = COALESCE($7, max_single_bet),
            updated_at = NOW()
        WHERE user_id = $8
        "#
    )
    .bind(&body.daily_bet_limit)
    .bind(&body.weekly_bet_limit)
    .bind(&body.monthly_bet_limit)
    .bind(&body.daily_loss_limit)
    .bind(&body.weekly_loss_limit)
    .bind(&body.monthly_loss_limit)
    .bind(&body.max_single_bet)
    .bind(user_id)
    .execute(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to update gambling limits: {}", e);
        AppError::Database(e)
    })?;

    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "Limits updated successfully"
    })))
}

pub async fn self_exclude(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
    body: web::Json<SelfExcludeRequest>,
) -> AppResult<HttpResponse> {
    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    let excluded_until = Utc::now() + chrono::Duration::days(body.duration_days);

    sqlx::query(
        r#"
        UPDATE gambling_limits
        SET self_excluded_until = $1, updated_at = NOW()
        WHERE user_id = $2
        "#
    )
    .bind(excluded_until)
    .bind(user_id)
    .execute(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to set self-exclusion: {}", e);
        AppError::Database(e)
    })?;

    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "Self-exclusion set successfully",
        "excluded_until": excluded_until
    })))
}
