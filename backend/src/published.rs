//! Read approved publications using the existing application pool, without HTTP.
use actix_web::{web, HttpResponse};
use chrono::{DateTime, Utc};
use serde_json::{json, Value};
use sqlx::PgPool;
use uuid::Uuid;

#[derive(sqlx::FromRow)]
struct PublishedRecord {
    payload: Value,
    version: i64,
    deleted: bool,
    published_at: DateTime<Utc>,
}

fn unavailable(code: &str) -> HttpResponse {
    HttpResponse::ServiceUnavailable()
        .insert_header(("Cache-Control", "no-store"))
        .json(json!({"status":"unavailable","prediction":null,
            "error":{"code":code,"message":"Published prediction data is unavailable."}}))
}

fn pending(match_id: i32, withdrawn: bool) -> HttpResponse {
    HttpResponse::NotFound()
        .insert_header(("Cache-Control", "no-store"))
        .json(
            json!({"status":if withdrawn {"unavailable"} else {"pending"},
            "match_id":match_id,"prediction":null,
            "freshness":{"state":"unavailable","generated_at":null},
            "error":{"code":if withdrawn {"PREDICTION_WITHDRAWN"} else {"PREDICTION_PENDING"},
                "message":"No published prediction is available for this fixture."}}),
        )
}

pub(crate) fn valid_probabilities(prediction: &Value) -> bool {
    let probabilities: Option<Vec<f64>> = ["home_prob", "draw_prob", "away_prob"]
        .iter()
        .map(|key| prediction[*key].as_f64())
        .collect();
    probabilities.is_some_and(|values| {
        values
            .iter()
            .all(|p| p.is_finite() && (0.0..=1.0).contains(p))
            && (values.iter().sum::<f64>() - 1.0).abs() < 0.01
    })
}

fn prediction_response(match_id: i32, record: PublishedRecord, now: DateTime<Utc>) -> HttpResponse {
    if record.deleted {
        return pending(match_id, true);
    }
    if record.payload["schema_version"] != 1
        || record.payload["local_match_id"].as_i64() != Some(i64::from(match_id))
    {
        return unavailable("PUBLICATION_SCHEMA_INVALID");
    }
    let mut prediction = record.payload["prediction"].clone();
    if prediction.is_null() {
        return pending(match_id, false);
    }
    let generated_at = prediction["created_at"]
        .as_str()
        .and_then(|value| DateTime::parse_from_rfc3339(value).ok())
        .map(|value| value.with_timezone(&Utc));
    let Some(generated_at) = generated_at else {
        return unavailable("PUBLICATION_SCHEMA_INVALID");
    };
    if !valid_probabilities(&prediction)
        || prediction["match_id"].as_i64() != Some(i64::from(match_id))
        || prediction["model_version"]
            .as_str()
            .is_none_or(str::is_empty)
    {
        return unavailable("PUBLICATION_SCHEMA_INVALID");
    }
    let age = (now - generated_at).num_seconds();
    let state = if age < 0 {
        "future"
    } else if age > 24 * 60 * 60 {
        "stale"
    } else {
        "fresh"
    };
    // Preserve existing prediction fields; publication metadata is additive.
    prediction["status"] = json!("available");
    prediction["freshness"] = json!({"state":state,"generated_at":generated_at,
        "published_at":record.published_at,"age_seconds":age,
        "publication_version":record.version});
    HttpResponse::Ok()
        .insert_header(("Cache-Control", "no-store"))
        .json(prediction)
}

/// GET /api/v1/predictions/{match_id}; explicit pending, no live inference fallback.
pub async fn prediction(pool: web::Data<PgPool>, id: web::Path<i32>) -> HttpResponse {
    let match_id = *id;
    if match_id < 1 {
        return HttpResponse::BadRequest().json(json!({"error":{"code":"INVALID_MATCH_ID"}}));
    }
    let stream = std::env::var("PUBLICATION_STREAM_ID")
        .ok()
        .and_then(|value| Uuid::parse_str(&value).ok());
    let Some(stream) = stream else {
        return unavailable("PUBLICATION_STREAM_NOT_CONFIGURED");
    };
    match sqlx::query_as::<_, PublishedRecord>(
        "SELECT r.payload,r.version,r.deleted,r.published_at FROM published.records r \
         JOIN published.sources s ON s.stream_id=r.stream_id AND s.enabled \
         WHERE r.stream_id=$1 AND r.dataset='fixture_bundle' AND r.record_key=$2",
    )
    .bind(stream)
    .bind(format!("football:legacy.matches:{match_id}"))
    .fetch_optional(pool.get_ref())
    .await
    {
        Ok(Some(record)) => prediction_response(match_id, record, Utc::now()),
        Ok(None) => pending(match_id, false),
        Err(_) => {
            tracing::warn!("Published prediction query unavailable");
            unavailable("PUBLICATION_DATABASE_UNAVAILABLE")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use actix_web::body::to_bytes;

    fn record(prediction: Value) -> PublishedRecord {
        PublishedRecord {
            payload: json!({"schema_version":1,"local_match_id":42,"prediction":prediction}),
            version: 7,
            deleted: false,
            published_at: Utc::now(),
        }
    }

    #[actix_web::test]
    async fn missing_prediction_is_pending_without_invented_probabilities() {
        let response = prediction_response(42, record(Value::Null), Utc::now());
        assert_eq!(response.status(), 404);
        let body: Value =
            serde_json::from_slice(&to_bytes(response.into_body()).await.unwrap()).unwrap();
        assert_eq!(body["status"], "pending");
        assert!(body["prediction"].is_null());
        assert!(body.get("home_prob").is_none());
    }

    #[actix_web::test]
    async fn preserves_stored_probabilities_and_generation_freshness() {
        let now = DateTime::parse_from_rfc3339("2026-10-26T12:00:00Z")
            .unwrap()
            .with_timezone(&Utc);
        let input = json!({"match_id":42,"model_version":"reviewed-model","home_prob":0.5,
            "draw_prob":0.3,"away_prob":0.2,"created_at":"2026-10-24T12:00:00Z"});
        let response = prediction_response(42, record(input.clone()), now);
        assert_eq!(response.status(), 200);
        let body: Value =
            serde_json::from_slice(&to_bytes(response.into_body()).await.unwrap()).unwrap();
        for key in [
            "home_prob",
            "draw_prob",
            "away_prob",
            "model_version",
            "created_at",
        ] {
            assert_eq!(body[key], input[key]);
        }
        assert_eq!(body["freshness"]["state"], "stale");
        assert_eq!(body["freshness"]["age_seconds"], 172800);
    }

    #[actix_web::test]
    async fn invalid_publication_is_unavailable_and_tombstones_are_not_served() {
        let response = prediction_response(42, record(json!({"home_prob":0.99})), Utc::now());
        assert_eq!(response.status(), 503);
        let mut withdrawn = record(Value::Null);
        withdrawn.deleted = true;
        let response = prediction_response(42, withdrawn, Utc::now());
        assert_eq!(response.status(), 404);
        let body: Value =
            serde_json::from_slice(&to_bytes(response.into_body()).await.unwrap()).unwrap();
        assert_eq!(body["error"]["code"], "PREDICTION_WITHDRAWN");
    }
}
