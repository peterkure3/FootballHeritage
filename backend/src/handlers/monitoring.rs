use crate::monitoring::MonitoringService;
use actix_web::{web, HttpRequest, HttpResponse};

pub async fn metrics(
    req: HttpRequest,
    pool: web::Data<sqlx::PgPool>,
    monitoring: web::Data<MonitoringService>,
) -> Result<HttpResponse, crate::features::FeatureError> {
    crate::features::administrator(&req, &pool).await?;
    let metrics = monitoring.get_metrics().await;

    Ok(HttpResponse::Ok().json(metrics))
}
