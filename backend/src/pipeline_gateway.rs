//! Browser-facing gateway. Python is private and accepts only this service.
use crate::features::{self, FeatureError};
use actix_web::{web, HttpRequest, HttpResponse};
use sqlx::PgPool;

pub async fn proxy(
    req: HttpRequest,
    body: web::Bytes,
    pool: web::Data<PgPool>,
) -> Result<HttpResponse, FeatureError> {
    let tail = req.match_info().query("tail");
    if tail.split('/').any(|v| v == ".." || v == ".") || tail.contains('\\') {
        return Err(FeatureError::Invalid);
    }
    // Refresh/training/collection endpoints are administrative even when a UI
    // previously exposed a button. POST previews/evaluation remain read-only.
    let read_only_post = [
        "sport-models/preview",
        "fpl/team/evaluate",
        "parlay/enrich",
        "smart-assistant",
        "intelligence/devig",
        "intelligence/ev",
        "intelligence/ev/batch",
        "intelligence/arbitrage/scan",
    ];
    let refresh = reqwest::Url::parse(&format!("http://gateway.invalid/?{}", req.query_string()))
        .map_err(|_| FeatureError::Invalid)?
        .query_pairs()
        .any(|(k, v)| k == "refresh" && !matches!(v.as_ref(), "false" | "0" | ""));
    if refresh
        || tail == "predictions/backtest"
        || tail == "predictions/validate-data"
        || (req.method() != actix_web::http::Method::GET
            && !(req.method() == actix_web::http::Method::POST && read_only_post.contains(&tail)))
    {
        features::administrator(&req, &pool).await?;
    }
    if tail == "predictions/run-pipeline" && std::env::var("APP_ENV").as_deref() == Ok("production")
    {
        return Err(FeatureError::Forbidden);
    }
    let base = std::env::var("PIPELINE_API_URL").map_err(|_| FeatureError::Invalid)?;
    let secret = std::env::var("PIPELINE_INTERNAL_TOKEN").map_err(|_| FeatureError::Invalid)?;
    if secret.len() < 32 {
        return Err(FeatureError::Invalid);
    }
    let url = format!(
        "{}/{}{}{}",
        base.trim_end_matches('/'),
        tail,
        if req.query_string().is_empty() {
            ""
        } else {
            "?"
        },
        req.query_string()
    );
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(45))
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .map_err(|_| FeatureError::Invalid)?;
    let method = reqwest::Method::from_bytes(req.method().as_str().as_bytes())
        .map_err(|_| FeatureError::Invalid)?;
    let response = client
        .request(method, url)
        .header("X-Internal-Token", secret)
        .header("Content-Type", "application/json")
        .body(body.to_vec())
        .send()
        .await;
    let Ok(response) = response else {
        return Ok(HttpResponse::ServiceUnavailable().json(serde_json::json!({"error":{"code":"UPSTREAM_UNAVAILABLE","message":"Prediction service is unavailable."}})));
    };
    let status = actix_web::http::StatusCode::from_u16(response.status().as_u16())
        .map_err(|_| FeatureError::Invalid)?;
    if status.is_server_error() {
        return Ok(HttpResponse::build(status).json(serde_json::json!({"error":{"code":"UPSTREAM_UNAVAILABLE","message":"Prediction service is unavailable."}})));
    }
    let content_type = response
        .headers()
        .get("content-type")
        .and_then(|s| s.to_str().ok())
        .unwrap_or("application/json")
        .to_owned();
    let bytes = response.bytes().await.map_err(|_| FeatureError::Invalid)?;
    Ok(HttpResponse::build(status)
        .insert_header(("Content-Type", content_type))
        .insert_header(("Cache-Control", "no-store"))
        .body(bytes))
}
