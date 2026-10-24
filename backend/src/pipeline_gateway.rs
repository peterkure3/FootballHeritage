//! Browser-facing gateway. Python is private and accepts only this service.
use crate::features::{self, FeatureError};
use actix_web::{web, HttpRequest, HttpResponse};
use sqlx::PgPool;

struct GatewayConfig {
    base: String,
    token: String,
}

impl GatewayConfig {
    fn from_values(base: Option<&str>, token: Option<&str>) -> Option<Self> {
        let base = base.filter(|value| !value.trim().is_empty())?;
        let token = token.filter(|value| value.len() >= 32)?;
        let parsed = reqwest::Url::parse(base.trim()).ok()?;
        if !matches!(parsed.scheme(), "http" | "https")
            || parsed.host_str().is_none()
            || !parsed.username().is_empty()
            || parsed.password().is_some()
            || parsed.query().is_some()
            || parsed.fragment().is_some()
        {
            return None;
        }
        Some(Self {
            base: normalize_pipeline_url(base),
            token: token.to_owned(),
        })
    }
}

pub(crate) fn normalize_pipeline_url(url: &str) -> String {
    let url = url.trim().trim_end_matches('/');
    if url.ends_with("/api/v1") {
        url.to_string()
    } else if url.ends_with("/api") {
        format!("{url}/v1")
    } else {
        format!("{url}/api/v1")
    }
}

fn unavailable(code: &str) -> HttpResponse {
    HttpResponse::ServiceUnavailable().json(serde_json::json!({
        "error": {"code": code, "message": "Prediction service is unavailable."}
    }))
}

pub async fn proxy(
    req: HttpRequest,
    body: web::Bytes,
    pool: web::Data<PgPool>,
) -> Result<HttpResponse, FeatureError> {
    let base = std::env::var("PIPELINE_API_URL").ok();
    let token = std::env::var("PIPELINE_INTERNAL_TOKEN").ok();
    proxy_with_config(
        req,
        body,
        pool,
        GatewayConfig::from_values(base.as_deref(), token.as_deref()),
    )
    .await
}

async fn proxy_with_config(
    req: HttpRequest,
    body: web::Bytes,
    pool: web::Data<PgPool>,
    config: Option<GatewayConfig>,
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
    let Some(config) = config else {
        tracing::error!("Prediction gateway configuration is missing or invalid; check PIPELINE_API_URL and PIPELINE_INTERNAL_TOKEN");
        return Ok(unavailable("UPSTREAM_NOT_CONFIGURED"));
    };
    let url = format!(
        "{}/{}{}{}",
        config.base.trim_end_matches('/'),
        tail,
        if req.query_string().is_empty() {
            ""
        } else {
            "?"
        },
        req.query_string()
    );
    let Ok(client) = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(45))
        .redirect(reqwest::redirect::Policy::none())
        .build()
    else {
        return Ok(unavailable("UPSTREAM_UNAVAILABLE"));
    };
    let method = reqwest::Method::from_bytes(req.method().as_str().as_bytes())
        .map_err(|_| FeatureError::Invalid)?;
    let response = client
        .request(method, url)
        .header("X-Internal-Token", config.token)
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

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::{test as aw_test, App, HttpServer};
    use std::net::TcpListener;

    const TOKEN: &str = "pipeline-gateway-test-token-at-least-32-bytes";

    #[test]
    fn validates_server_configuration_without_exposing_secrets() {
        for (url, token) in [
            (None, Some(TOKEN)),
            (Some("http://127.0.0.1:5555"), None),
            (Some("http://127.0.0.1:5555"), Some("short")),
        ] {
            assert!(GatewayConfig::from_values(url, token).is_none());
        }
        for url in [
            "file:///tmp/pipeline",
            "not-a-url",
            "http://user:password@localhost:5555",
            "http://localhost:5555?token=private",
            "http://localhost:5555/#fragment",
        ] {
            assert!(GatewayConfig::from_values(Some(url), Some(TOKEN)).is_none());
        }
        for url in [
            "http://127.0.0.1:5555",
            "http://127.0.0.1:5555/api",
            "http://127.0.0.1:5555/api/v1/",
        ] {
            assert_eq!(
                GatewayConfig::from_values(Some(url), Some(TOKEN))
                    .unwrap()
                    .base,
                "http://127.0.0.1:5555/api/v1"
            );
        }
    }

    fn unused_pool() -> web::Data<PgPool> {
        web::Data::new(
            sqlx::postgres::PgPoolOptions::new()
                .connect_lazy("postgresql://unused@127.0.0.1/unused")
                .unwrap(),
        )
    }

    #[actix_web::test]
    async fn missing_server_settings_are_503_not_a_client_400() {
        let request = aw_test::TestRequest::get()
            .uri("/api/v1/pipeline/matches?limit=100")
            .param("tail", "matches")
            .to_http_request();
        let response = proxy_with_config(request, web::Bytes::new(), unused_pool(), None)
            .await
            .unwrap();
        assert_eq!(response.status(), 503);
        let bytes = actix_web::body::to_bytes(response.into_body())
            .await
            .unwrap();
        let body: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(body["error"]["code"], "UPSTREAM_NOT_CONFIGURED");
        assert!(!String::from_utf8_lossy(&bytes).contains(TOKEN));
    }

    #[actix_web::test]
    async fn forwards_both_reported_paths_queries_and_the_private_token() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        let server = HttpServer::new(|| App::new().default_service(web::to(|req: HttpRequest| async move {
            HttpResponse::Ok().json(serde_json::json!({"path":req.path(),"query":req.query_string(),"private_token_valid":req.headers().get("X-Internal-Token").and_then(|value| value.to_str().ok())==Some(TOKEN)}))
        }))).workers(1).listen(listener).unwrap().run();
        let handle = server.handle();
        actix_web::rt::spawn(server);
        for (tail, query) in [
            ("matches", "limit=100"),
            ("prediction-dashboard/fixtures", "page=1&page_size=6"),
        ] {
            let request = aw_test::TestRequest::get()
                .uri(&format!("/api/v1/pipeline/{tail}?{query}"))
                .param("tail", tail)
                .to_http_request();
            let config =
                GatewayConfig::from_values(Some(&format!("http://{address}")), Some(TOKEN));
            let response = proxy_with_config(request, web::Bytes::new(), unused_pool(), config)
                .await
                .unwrap();
            assert_eq!(response.status(), 200);
            let bytes = actix_web::body::to_bytes(response.into_body())
                .await
                .unwrap();
            let body: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
            assert_eq!(body["path"], format!("/api/v1/{tail}"));
            assert_eq!(body["query"], query);
            assert_eq!(body["private_token_valid"], true);
        }
        handle.stop(true).await;
    }
}
