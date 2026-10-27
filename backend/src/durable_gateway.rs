//! Approved response snapshots and explicit asynchronous computation, never local HTTP.
use actix_web::{http::StatusCode, web, HttpRequest, HttpResponse};
use chrono::{DateTime, Utc};
use serde::Deserialize;
use serde_json::{json, Value};
use sqlx::PgPool;
use uuid::Uuid;

use crate::features::{self, FeatureError};

#[derive(Deserialize)]
pub struct Route {
    pub method: String,
    pub path: String,
    pub admin: bool,
    pub side_effect: bool,
    pub ttl_seconds: i64,
}

pub fn route(method: &str, path: &str) -> Option<Route> {
    let routes: Vec<Route> =
        serde_json::from_str(include_str!("../contracts/gateway_routes.json")).ok()?;
    // Exact routes take precedence over parameters, as in FastAPI's reviewed table.
    routes
        .into_iter()
        .filter(|r| r.method == method)
        .find(|r| r.path == path)
        .or_else(|| {
            let routes: Vec<Route> =
                serde_json::from_str(include_str!("../contracts/gateway_routes.json")).ok()?;
            routes.into_iter().find(|r| {
                r.method == method
                    && r.path.split('/').count() == path.split('/').count()
                    && r.path
                        .split('/')
                        .zip(path.split('/'))
                        .all(|(pattern, value)| {
                            (pattern.starts_with('{') && !value.is_empty()) || pattern == value
                        })
            })
        })
}

#[derive(sqlx::FromRow)]
struct Job {
    id: Uuid,
    state: String,
    response_status: Option<i32>,
    response: Option<Value>,
    generated_at: Option<DateTime<Utc>>,
    fresh_until: Option<DateTime<Utc>>,
}

fn unavailable(code: &str) -> HttpResponse {
    HttpResponse::ServiceUnavailable().insert_header(("Cache-Control","no-store"))
        .json(json!({"status":"unavailable","error":{"code":code,"message":"Published computation is unavailable. Try again later."}}))
}

pub async fn serve(
    req: HttpRequest,
    body: web::Bytes,
    pool: web::Data<PgPool>,
) -> Result<HttpResponse, FeatureError> {
    let tail = req.match_info().query("tail").to_string();
    serve_path(req, body, pool, &tail).await
}

pub async fn serve_path(
    req: HttpRequest,
    body: web::Bytes,
    pool: web::Data<PgPool>,
    tail: &str,
) -> Result<HttpResponse, FeatureError> {
    let Some(contract) = route(req.method().as_str(), tail) else {
        return Ok(
            HttpResponse::NotFound().json(json!({"error":{"code":"UNKNOWN_PIPELINE_ROUTE"}}))
        );
    };
    if body.len() > 262144
        || req.query_string().len() > 8192
        || tail.len() > 512
        || tail
            .chars()
            .any(|c| !(c.is_alphanumeric() || "-_/.".contains(c)))
        || tail.split('/').any(|s| s == "." || s == "..")
    {
        return Err(FeatureError::Invalid);
    }
    let parsed = reqwest::Url::parse(&format!("http://gateway.invalid/?{}", req.query_string()))
        .map_err(|_| FeatureError::Invalid)?;
    let mut pairs: Vec<(String, String)> = parsed
        .query_pairs()
        .map(|(k, v)| (k.into_owned(), v.into_owned()))
        .collect();
    // Stable key sorting preserves repeated-value order (FastAPI uses the last scalar).
    pairs.sort_by(|a, b| a.0.cmp(&b.0));
    let refresh = pairs
        .iter()
        .any(|(k, v)| k == "refresh" && !matches!(v.as_str(), "false" | "0" | ""));
    let admin = contract.admin || refresh;
    let side_effect = contract.side_effect || refresh;
    let private = req.method() != actix_web::http::Method::GET || admin;
    let owner = if admin {
        Some(features::administrator(&req, &pool).await?)
    } else if private {
        Some(
            features::identity(&req, &pool)
                .await?
                .0
                .ok_or(FeatureError::Unauthorized)?,
        )
    } else {
        None
    };
    let nonce = if private || side_effect {
        let Some(value) = req
            .headers()
            .get("Idempotency-Key")
            .and_then(|v| v.to_str().ok())
            .and_then(|v| Uuid::parse_str(v).ok())
        else {
            return Ok(HttpResponse::PreconditionRequired().json(json!({"error":{"code":"IDEMPOTENCY_KEY_REQUIRED","message":"Send a UUID Idempotency-Key and reuse it while polling this operation."}})));
        };
        Some(value)
    } else {
        None
    };
    let body: Value = if body.is_empty() {
        Value::Null
    } else {
        serde_json::from_slice(&body).map_err(|_| FeatureError::Invalid)?
    };
    let envelope = json!({"schema_version":1,"method":req.method().as_str(),"path":tail,"query":pairs,"body":body,
        "ttl_seconds":contract.ttl_seconds,"side_effect":side_effect,"admin":admin});
    let key = hex::encode(ring::digest::digest(
        &ring::digest::SHA256,
        serde_json::to_vec(&json!([owner, nonce, envelope]))
            .map_err(|_| FeatureError::Invalid)?
            .as_slice(),
    ));
    let Some(stream) = std::env::var("PUBLICATION_STREAM_ID")
        .ok()
        .and_then(|v| v.parse::<Uuid>().ok())
    else {
        return Ok(unavailable("PUBLICATION_STREAM_NOT_CONFIGURED"));
    };
    let result = tokio::time::timeout(
        std::time::Duration::from_secs(8),
        resolve(&pool, stream, owner, nonce, &key, &envelope, side_effect),
    )
    .await;
    match result {
        Ok(Ok(response)) => Ok(response),
        Ok(Err(error)) => {
            if let Some(database_error) = error.as_database_error() {
                tracing::warn!(code=?database_error.code(), message=database_error.message(), "Durable gateway database query failed");
            } else {
                tracing::warn!("Durable gateway storage or decoding unavailable");
            }
            Ok(unavailable("PUBLICATION_DATABASE_UNAVAILABLE"))
        }
        _ => Ok(unavailable("PUBLICATION_DATABASE_UNAVAILABLE")),
    }
}

async fn resolve(
    pool: &PgPool,
    stream: Uuid,
    owner: Option<Uuid>,
    nonce: Option<Uuid>,
    key: &str,
    envelope: &Value,
    side_effect: bool,
) -> Result<HttpResponse, sqlx::Error> {
    // A completed response needs one approved-source read, not a queue lock or
    // enqueue transaction. Keep cache hits independent across API instances.
    let cached: Option<Job> = sqlx::query_as("SELECT j.id,j.state,j.response_status,j.response,j.generated_at,j.fresh_until FROM published.gateway_jobs j JOIN published.sources s USING(stream_id) WHERE j.stream_id=$1 AND j.request_key=$2 AND s.enabled AND j.state='completed' AND ($3 OR j.fresh_until>NOW())")
        .bind(stream).bind(key).bind(nonce.is_some()).fetch_optional(pool).await?;
    if let Some(job) = cached {
        return Ok(completed_response(job));
    }
    let mut tx = pool.begin().await?;
    sqlx::query("SET LOCAL statement_timeout='3s'")
        .execute(&mut *tx)
        .await?;
    sqlx::query("SELECT pg_advisory_xact_lock(hashtextextended($1,0))")
        .bind(format!("gateway-queue:{stream}"))
        .execute(&mut *tx)
        .await?;
    let source: Option<Uuid> = sqlx::query_scalar(
        "SELECT stream_id FROM published.sources WHERE stream_id=$1 AND enabled",
    )
    .bind(stream)
    .fetch_optional(&mut *tx)
    .await?;
    if source.is_none() {
        return Ok(unavailable("PUBLICATION_SOURCE_UNAVAILABLE"));
    }
    if let Some(nonce) = nonce {
        let existing: Option<String> = sqlx::query_scalar("SELECT request_key FROM published.gateway_jobs WHERE stream_id=$1 AND owner_id=$2 AND request_nonce=$3")
            .bind(stream).bind(owner).bind(nonce).fetch_optional(&mut *tx).await?;
        if existing.is_some_and(|existing| existing != key) {
            return Ok(
                HttpResponse::Conflict().json(json!({"error":{"code":"IDEMPOTENCY_KEY_CONFLICT"}}))
            );
        }
    }
    let active: i64 = sqlx::query_scalar("SELECT count(*) FROM published.gateway_jobs WHERE stream_id=$1 AND state IN ('queued','running')")
        .bind(stream).fetch_one(&mut *tx).await?;
    let existing: bool = sqlx::query_scalar(
        "SELECT EXISTS(SELECT 1 FROM published.gateway_jobs WHERE stream_id=$1 AND request_key=$2)",
    )
    .bind(stream)
    .bind(key)
    .fetch_one(&mut *tx)
    .await?;
    if !existing && active >= 128 {
        return Ok(HttpResponse::TooManyRequests()
            .insert_header(("Retry-After", "5"))
            .json(json!({"error":{"code":"COMPUTATION_QUEUE_FULL"}})));
    }
    if !existing && owner.is_some() {
        let count: i64 = sqlx::query_scalar("SELECT count(*) FROM published.gateway_jobs WHERE stream_id=$1 AND owner_id=$2 AND state IN ('queued','running')")
            .bind(stream).bind(owner).fetch_one(&mut *tx).await?;
        if count >= 16 {
            return Ok(HttpResponse::TooManyRequests()
                .json(json!({"error":{"code":"USER_COMPUTATION_QUEUE_FULL"}})));
        }
    }
    sqlx::query("INSERT INTO published.gateway_jobs(stream_id,request_key,id,owner_id,request_nonce,request,side_effect) VALUES($1,$2,$3,$4,$5,$6,$7) ON CONFLICT DO NOTHING")
        .bind(stream).bind(key).bind(Uuid::new_v4()).bind(owner).bind(nonce).bind(envelope).bind(side_effect).execute(&mut *tx).await?;
    // Reuse public GET snapshots until their explicit freshness deadline. Private
    // idempotency responses are immutable; a new operation must use a new UUID.
    if nonce.is_none() {
        sqlx::query("UPDATE published.gateway_jobs SET state='queued',attempts=0,response=NULL,response_status=NULL,generated_at=NULL,fresh_until=NULL,created_at=NOW() WHERE stream_id=$1 AND request_key=$2 AND ((state='completed' AND fresh_until<NOW()) OR (state='failed' AND created_at<NOW()-INTERVAL '5 minutes'))")
            .bind(stream).bind(key).execute(&mut *tx).await?;
    }
    let job: Job = sqlx::query_as("SELECT id,state,response_status,response,generated_at,fresh_until FROM published.gateway_jobs WHERE stream_id=$1 AND request_key=$2")
        .bind(stream).bind(key).fetch_one(&mut *tx).await?;
    tx.commit().await?;
    if job.state == "completed" {
        return Ok(completed_response(job));
    }
    if matches!(job.state.as_str(), "failed" | "indeterminate") {
        return Ok(unavailable(if job.state == "indeterminate" {
            "COMPUTATION_OUTCOME_UNKNOWN"
        } else {
            "COMPUTATION_FAILED"
        }));
    }
    Ok(HttpResponse::Accepted().insert_header(("Retry-After","2")).insert_header(("Cache-Control","no-store"))
        .insert_header(("X-Gateway-Pending","1"))
        .json(json!({"status":"pending","job_id":job.id,"state":job.state,"message":"The requested output is awaiting publication."})))
}

fn completed_response(job: Job) -> HttpResponse {
    let status = StatusCode::from_u16(job.response_status.unwrap_or(503) as u16)
        .unwrap_or(StatusCode::SERVICE_UNAVAILABLE);
    HttpResponse::build(status)
        .insert_header(("Cache-Control", "no-store"))
        .insert_header(("X-Data-Source", "published-postgresql"))
        .insert_header((
            "X-Generated-At",
            job.generated_at.map(|v| v.to_rfc3339()).unwrap_or_default(),
        ))
        .insert_header((
            "X-Fresh-Until",
            job.fresh_until.map(|v| v.to_rfc3339()).unwrap_or_default(),
        ))
        .json(job.response.unwrap_or(Value::Null))
}
