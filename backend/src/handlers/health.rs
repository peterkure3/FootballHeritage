#![allow(dead_code)]
use crate::errors::AppResult;
use crate::monitoring::MonitoringService;
use actix_web::{web, HttpResponse};
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct HealthCheckResponse {
    pub status: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub version: String,
}

pub async fn health_check(monitoring: web::Data<MonitoringService>) -> AppResult<HttpResponse> {
    let health = monitoring.get_health_status();

    Ok(HttpResponse::Ok().json(health))
}

pub async fn readiness(pool: web::Data<sqlx::PgPool>) -> HttpResponse {
    match sqlx::query_scalar::<_, i32>("SELECT 1")
        .fetch_one(pool.get_ref())
        .await
    {
        Ok(_) => HttpResponse::Ok().json(serde_json::json!({"status":"ready"})),
        Err(_) => {
            HttpResponse::ServiceUnavailable().json(serde_json::json!({"status":"unavailable"}))
        }
    }
}
