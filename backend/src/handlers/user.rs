use crate::errors::{AppError, AppResult};
use actix_web::{web, HttpRequest, HttpResponse};
use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use tracing::error;
use uuid::Uuid;

#[derive(Debug, Serialize)]
pub struct UserProfile {
    pub id: Uuid,
    pub email: String,
    pub first_name: String,
    pub last_name: String,
    pub date_of_birth: NaiveDate,
    pub phone: Option<String>,
    pub address: Option<String>,
    pub is_verified: bool,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateProfileRequest {
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub phone: Option<String>,
    pub address: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct UserActivity {
    pub total_bets: i64,
    pub total_wagered: bigdecimal::BigDecimal,
    pub total_won: bigdecimal::BigDecimal,
    pub win_rate: f64,
}

pub async fn get_profile(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    let user: (Uuid, String, String, String, NaiveDate, Option<String>, Option<String>, bool, DateTime<Utc>) = sqlx::query_as(
        r#"
        SELECT id, email, first_name, last_name, date_of_birth, phone, address, is_verified, created_at
        FROM users
        WHERE id = $1
        "#
    )
    .bind(user_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch user profile: {}", e);
        AppError::Database(e)
    })?;

    Ok(HttpResponse::Ok().json(UserProfile {
        id: user.0,
        email: user.1,
        first_name: user.2,
        last_name: user.3,
        date_of_birth: user.4,
        phone: user.5,
        address: user.6,
        is_verified: user.7,
        created_at: user.8,
    }))
}

pub async fn update_profile(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
    body: web::Json<UpdateProfileRequest>,
) -> AppResult<HttpResponse> {
    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    sqlx::query(
        r#"
        UPDATE users
        SET first_name = COALESCE($1, first_name),
            last_name = COALESCE($2, last_name),
            phone = COALESCE($3, phone),
            address = COALESCE($4, address),
            updated_at = NOW()
        WHERE id = $5
        "#
    )
    .bind(&body.first_name)
    .bind(&body.last_name)
    .bind(&body.phone)
    .bind(&body.address)
    .bind(user_id)
    .execute(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to update user profile: {}", e);
        AppError::Database(e)
    })?;

    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "Profile updated successfully"
    })))
}

pub async fn get_activity(
    _req: HttpRequest,
    pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    // TODO: Extract user_id from JWT token
    let user_id = Uuid::new_v4();

    let activity: (i64, Option<bigdecimal::BigDecimal>) = sqlx::query_as(
        r#"
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM bets
        WHERE user_id = $1
        "#
    )
    .bind(user_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch user activity: {}", e);
        AppError::Database(e)
    })?;

    let total_won: Option<bigdecimal::BigDecimal> = sqlx::query_scalar(
        r#"
        SELECT COALESCE(SUM(potential_win), 0)
        FROM bets
        WHERE user_id = $1 AND status = 'won'
        "#
    )
    .bind(user_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch user winnings: {}", e);
        AppError::Database(e)
    })?;

    let win_count: i64 = sqlx::query_scalar(
        r#"
        SELECT COUNT(*)
        FROM bets
        WHERE user_id = $1 AND status = 'won'
        "#
    )
    .bind(user_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch win count: {}", e);
        AppError::Database(e)
    })?;

    let win_rate = if activity.0 > 0 {
        (win_count as f64 / activity.0 as f64) * 100.0
    } else {
        0.0
    };

    Ok(HttpResponse::Ok().json(UserActivity {
        total_bets: activity.0,
        total_wagered: activity.1.unwrap_or_else(|| bigdecimal::BigDecimal::from(0)),
        total_won: total_won.unwrap_or_else(|| bigdecimal::BigDecimal::from(0)),
        win_rate,
    }))
}
