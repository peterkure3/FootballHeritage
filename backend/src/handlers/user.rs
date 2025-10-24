use crate::errors::{AppError, AppResult};
use crate::models::Claims;
use actix_web::{web, HttpMessage, HttpRequest, HttpResponse};
use argon2::{Argon2, PasswordHash, PasswordHasher, PasswordVerifier};
use argon2::password_hash::{rand_core::OsRng, SaltString};
use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use tracing::{debug, error};
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
    pub is_admin: bool,
    pub is_super_admin: bool,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct UpdateProfileRequest {
    pub first_name: Option<String>,
    pub last_name: Option<String>,
    pub phone: Option<String>,
    pub address: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ChangePasswordRequest {
    pub current_password: String,
    pub new_password: String,
}

#[derive(Debug, Serialize)]
pub struct UserActivity {
    pub total_bets: i64,
    pub total_wagered: bigdecimal::BigDecimal,
    pub total_won: bigdecimal::BigDecimal,
    pub win_rate: f64,
}

pub async fn get_profile(
    req: HttpRequest,
    pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    let claims = get_user_claims(&req)
        .ok_or_else(|| AppError::Authentication("Unauthorized".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID".to_string()))?;

    let user: (Uuid, String, String, String, NaiveDate, Option<String>, Option<String>, bool, Option<String>, DateTime<Utc>) = sqlx::query_as(
        r#"
        SELECT id, email, first_name, last_name, date_of_birth, phone, address, is_verified, role, created_at
        FROM users
        WHERE id = $1
        "#
    )
    .bind(user_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| {
        debug!("User profile fetch failed (likely logged out or invalid token): {}", e);
        AppError::Database(e)
    })?;

    let role = user.8.as_deref();
    let is_admin = matches!(role, Some("admin") | Some("superadmin"));
    let is_super_admin = matches!(role, Some("superadmin"));

    Ok(HttpResponse::Ok().json(UserProfile {
        id: user.0,
        email: user.1,
        first_name: user.2,
        last_name: user.3,
        date_of_birth: user.4,
        phone: user.5,
        address: user.6,
        is_verified: user.7,
        is_admin,
        is_super_admin,
        created_at: user.9,
    }))
}

pub async fn update_profile(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    body: web::Json<UpdateProfileRequest>,
) -> AppResult<HttpResponse> {
    let claims = get_user_claims(&req)
        .ok_or_else(|| AppError::Authentication("Unauthorized".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID".to_string()))?;

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
    req: HttpRequest,
    pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    let claims = get_user_claims(&req)
        .ok_or_else(|| AppError::Authentication("Unauthorized".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID".to_string()))?;

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

pub async fn change_password(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    body: web::Json<ChangePasswordRequest>,
) -> AppResult<HttpResponse> {
    let claims = get_user_claims(&req)
        .ok_or_else(|| AppError::Authentication("Unauthorized".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID".to_string()))?;

    // Validate password strength
    if body.new_password.len() < 8 {
        return Err(AppError::Validation("Password must be at least 8 characters".to_string()));
    }

    // Get current password hash
    let current_hash: String = sqlx::query_scalar(
        "SELECT password_hash FROM users WHERE id = $1"
    )
    .bind(user_id)
    .fetch_one(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch user password: {}", e);
        AppError::Database(e)
    })?;

    // Verify current password
    let parsed_hash = PasswordHash::new(&current_hash)
        .map_err(|e| {
            error!("Failed to parse password hash: {}", e);
            AppError::Internal("Authentication error".to_string())
        })?;

    let argon2 = Argon2::default();
    if argon2.verify_password(body.current_password.as_bytes(), &parsed_hash).is_err() {
        return Err(AppError::Authentication("Current password is incorrect".to_string()));
    }

    // Hash new password
    let salt = SaltString::generate(&mut OsRng);
    let new_hash = argon2
        .hash_password(body.new_password.as_bytes(), &salt)
        .map_err(|e| {
            error!("Failed to hash password: {}", e);
            AppError::Internal("Failed to update password".to_string())
        })?
        .to_string();

    // Update password
    sqlx::query(
        "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2"
    )
    .bind(&new_hash)
    .bind(user_id)
    .execute(pool.as_ref())
    .await
    .map_err(|e| {
        error!("Failed to update password: {}", e);
        AppError::Database(e)
    })?;

    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "Password changed successfully"
    })))
}

// Helper function to extract user claims from request
fn get_user_claims(req: &HttpRequest) -> Option<Claims> {
    req.extensions().get::<Claims>().cloned()
}
