use crate::errors::AppResult;
use crate::monitoring::MonitoringService;
use actix_web::{web, HttpResponse};

pub async fn metrics(
    monitoring: web::Data<MonitoringService>,
) -> AppResult<HttpResponse> {
    let metrics = monitoring.get_metrics().await;
    
    Ok(HttpResponse::Ok().json(metrics))
}
