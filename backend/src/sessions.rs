//! Neon-owned durable sessions. No cache can grant access after revocation.
use crate::errors::{AppError, AppResult};
use crate::models::{Claims, User};
use sqlx::PgPool;

pub async fn create<'e, E: sqlx::Executor<'e, Database = sqlx::Postgres>>(
    executor: E,
    user: &User,
    session_id: &str,
    ip_address: &str,
    user_agent: &str,
    lifetime_hours: u64,
) -> AppResult<()> {
    let hours = i64::try_from(lifetime_hours)
        .map_err(|_| AppError::Configuration("Invalid session lifetime".into()))?;
    sqlx::query(
        "INSERT INTO auth_sessions(session_id,user_id,expires_at,ip_address,user_agent) \
         VALUES($1,$2,NOW()+($3 * INTERVAL '1 hour'),$4,$5)",
    )
    .bind(session_id)
    .bind(user.id)
    .bind(hours)
    .bind(ip_address)
    .bind(user_agent)
    .execute(executor)
    .await?;
    Ok(())
}

pub async fn validate(pool: &PgPool, claims: &Claims, idle_minutes: u64) -> AppResult<()> {
    let user_id = claims
        .sub
        .parse::<uuid::Uuid>()
        .map_err(|_| AppError::SessionExpired)?;
    let minutes = i64::try_from(idle_minutes)
        .map_err(|_| AppError::Configuration("Invalid session timeout".into()))?;
    let session = sqlx::query_scalar::<_, String>(
        "UPDATE auth_sessions s SET last_activity_at=NOW() FROM users u \
         WHERE s.session_id=$1 AND s.user_id=$2 AND u.id=s.user_id \
         AND u.is_active AND (u.locked_until IS NULL OR u.locked_until<=NOW()) \
         AND s.revoked_at IS NULL AND s.expires_at>NOW() \
         AND s.last_activity_at>=NOW()-($3 * INTERVAL '1 minute') RETURNING s.session_id",
    )
    .bind(&claims.session_id)
    .bind(user_id)
    .bind(minutes)
    .fetch_optional(pool)
    .await?;
    session.ok_or(AppError::SessionExpired)?;
    Ok(())
}

pub async fn revoke(pool: &PgPool, claims: &Claims) -> AppResult<()> {
    let user_id = claims
        .sub
        .parse::<uuid::Uuid>()
        .map_err(|_| AppError::SessionExpired)?;
    sqlx::query("UPDATE auth_sessions SET revoked_at=COALESCE(revoked_at,NOW()) WHERE session_id=$1 AND user_id=$2")
        .bind(&claims.session_id).bind(user_id).execute(pool).await?;
    Ok(())
}
