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

pub async fn health_check(
    monitoring: web::Data<MonitoringService>,
) -> AppResult<HttpResponse> {
    let health = monitoring.get_health_status();
    
    Ok(HttpResponse::Ok().json(health))
}
