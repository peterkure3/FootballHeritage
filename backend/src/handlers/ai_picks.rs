use actix_web::{web, HttpRequest, HttpResponse};
use chrono::{NaiveDate, Utc};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sqlx::PgPool;
use std::time::Duration;
use uuid::Uuid;

use crate::middleware::jwt_auth::get_claims;
use crate::pipeline_gateway::normalize_pipeline_url;

#[derive(Clone)]
pub struct AiPicksService {
    client: Client,
    pipeline_url: Option<String>,
}

impl AiPicksService {
    pub fn from_env() -> Result<Self, reqwest::Error> {
        Ok(Self {
            client: Client::builder().timeout(Duration::from_secs(30)).build()?,
            pipeline_url: std::env::var("PIPELINE_API_URL")
                .ok()
                .filter(|v| !v.trim().is_empty())
                .or_else(|| {
                    let environment =
                        std::env::var("APP_ENV").unwrap_or_else(|_| "development".into());
                    (environment == "development").then(|| "http://127.0.0.1:5555/api/v1".into())
                })
                .map(|url| normalize_pipeline_url(&url)),
        })
    }
}

#[derive(Debug, Deserialize)]
pub struct GenerateRequest {
    pub sport: String,
    pub competition: Option<String>,
    pub date: Option<String>,
    pub limit: Option<i64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatRequest {
    pub conversation_id: Option<Uuid>,
    pub request_id: Option<Uuid>,
    pub messages: Vec<ChatMessage>,
    pub sport: Option<String>,
}

pub type ChatMessage = crate::rag::Message;

fn user_id(req: &HttpRequest) -> Result<Uuid, HttpResponse> {
    get_claims(req)
        .and_then(|claims| Uuid::parse_str(&claims.sub).ok())
        .ok_or_else(|| {
            HttpResponse::Unauthorized().json(json!({"error":"Invalid authenticated user"}))
        })
}

fn supported_sport(sport: &str) -> bool {
    matches!(
        sport,
        "Football" | "NBA" | "WNBA" | "NFL" | "NCAAB" | "College Football"
    )
}

fn supported_competition(competition: Option<&str>) -> bool {
    competition.is_none()
        || matches!(
            competition,
            Some(
                "Premier League" | "La Liga" | "Bundesliga" | "Champions League" | "Europa League"
            )
        )
}

fn error(status: actix_web::http::StatusCode, message: &str) -> HttpResponse {
    HttpResponse::build(status).json(json!({"error": message}))
}

pub async fn generate(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    service: web::Data<AiPicksService>,
    body: web::Json<GenerateRequest>,
) -> HttpResponse {
    let Ok(user) = user_id(&req) else {
        return HttpResponse::Unauthorized().finish();
    };
    let limit = body.limit.unwrap_or(10).clamp(1, 20);
    if !supported_sport(&body.sport)
        || body.sport != "Football"
        || !supported_competition(body.competition.as_deref())
        || body.competition.as_deref().is_some_and(|v| v.len() > 120)
        || body
            .date
            .as_deref()
            .is_some_and(|v| NaiveDate::parse_from_str(v, "%Y-%m-%d").is_err())
    {
        return error(
            actix_web::http::StatusCode::UNPROCESSABLE_ENTITY,
            "This configured model currently supports Football only; competition/date must be supported",
        );
    }
    let Some(base) = &service.pipeline_url else {
        return error(
            actix_web::http::StatusCode::SERVICE_UNAVAILABLE,
            "AI Picks data service is not configured",
        );
    };

    let mut query = vec![("limit", limit.to_string())];
    if let Some(competition) = &body.competition {
        query.push(("competition", competition.clone()));
    }
    if let Some(date) = &body.date {
        query.push(("date", date.clone()));
    }
    let response = service
        .client
        .get(format!("{}/ai-picks", base.trim_end_matches('/')))
        .header(
            "X-Internal-Token",
            std::env::var("PIPELINE_INTERNAL_TOKEN").unwrap_or_default(),
        )
        .query(&query)
        .send()
        .await;
    let upstream = match response {
        Ok(response) if response.status().is_success() => match response.json::<Value>().await {
            Ok(value)
                if value.get("picks").is_some_and(Value::is_array)
                    && value.get("provenance").is_some_and(Value::is_object) =>
            {
                value
            }
            Ok(_) => {
                return error(
                    actix_web::http::StatusCode::BAD_GATEWAY,
                    "AI Picks returned an invalid response schema",
                )
            }
            Err(_) => {
                return error(
                    actix_web::http::StatusCode::BAD_GATEWAY,
                    "AI Picks returned invalid data",
                )
            }
        },
        Ok(response) => {
            return error(
                if response.status().is_server_error() {
                    actix_web::http::StatusCode::BAD_GATEWAY
                } else {
                    actix_web::http::StatusCode::SERVICE_UNAVAILABLE
                },
                "AI Picks data service is unavailable",
            )
        }
        Err(err) if err.is_timeout() => {
            return error(
                actix_web::http::StatusCode::GATEWAY_TIMEOUT,
                "AI Picks data service timed out",
            )
        }
        Err(_) => {
            return error(
                actix_web::http::StatusCode::BAD_GATEWAY,
                "AI Picks data service could not be reached",
            )
        }
    };

    let picks = &upstream["picks"];
    let mut provenance = upstream["provenance"].clone();
    provenance["summary"] = upstream["summary"].clone();
    let model_version = provenance["model"]
        .as_str()
        .unwrap_or("unknown")
        .to_string();
    let generated_at = Utc::now();

    let run_id = Uuid::new_v4();
    let requested_date = body
        .date
        .as_deref()
        .and_then(|value| NaiveDate::parse_from_str(value, "%Y-%m-%d").ok());
    let inserted = sqlx::query("INSERT INTO ai_pick_runs (id, user_id, sport, competition, requested_date, model_version, provenance, results, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)")
        .bind(run_id).bind(user).bind(&body.sport).bind(&body.competition).bind(requested_date)
        .bind(&model_version).bind(&provenance).bind(picks).bind(generated_at)
        .execute(pool.get_ref()).await;
    if inserted.is_err() {
        return error(
            actix_web::http::StatusCode::INTERNAL_SERVER_ERROR,
            "Could not persist AI Picks run",
        );
    }
    HttpResponse::Ok().json(json!({"id":run_id,"generated_at":generated_at,"sport":body.sport,"competition":body.competition,"date":body.date,"picks":picks,"summary":upstream["summary"],"provenance":provenance}))
}

pub async fn list(req: HttpRequest, pool: web::Data<PgPool>) -> HttpResponse {
    let Ok(user) = user_id(&req) else {
        return HttpResponse::Unauthorized().finish();
    };
    match sqlx::query_as::<_, PickRun>("SELECT id, sport, competition, requested_date, provenance, results, created_at FROM ai_pick_runs WHERE user_id=$1 ORDER BY created_at DESC LIMIT 50")
        .bind(user).fetch_all(pool.get_ref()).await {
        Ok(rows) => HttpResponse::Ok().json(rows.into_iter().map(PickRun::into_json).collect::<Vec<_>>()),
        Err(_) => error(actix_web::http::StatusCode::INTERNAL_SERVER_ERROR, "Could not load AI Picks"),
    }
}

pub async fn get(req: HttpRequest, pool: web::Data<PgPool>, id: web::Path<Uuid>) -> HttpResponse {
    let Ok(user) = user_id(&req) else {
        return HttpResponse::Unauthorized().finish();
    };
    match sqlx::query_as::<_, PickRun>("SELECT id, sport, competition, requested_date, provenance, results, created_at FROM ai_pick_runs WHERE id=$1 AND user_id=$2")
        .bind(*id).bind(user).fetch_optional(pool.get_ref()).await {
        Ok(Some(run)) => HttpResponse::Ok().json(run.into_json()),
        Ok(None) => HttpResponse::NotFound().json(json!({"error":"AI Picks run not found"})),
        Err(_) => error(actix_web::http::StatusCode::INTERNAL_SERVER_ERROR, "Could not load AI Picks run"),
    }
}

#[derive(sqlx::FromRow)]
struct PickRun {
    id: Uuid,
    sport: String,
    competition: Option<String>,
    requested_date: Option<NaiveDate>,
    provenance: Value,
    results: Value,
    created_at: chrono::DateTime<Utc>,
}

impl PickRun {
    fn into_json(self) -> Value {
        json!({"id":self.id,"sport":self.sport,"competition":self.competition,
            "date":self.requested_date,"picks":self.results,"created_at":self.created_at,
            "generated_at":self.created_at,"summary":self.provenance["summary"],"provenance":self.provenance})
    }
}

#[cfg(test)]
mod picks_tests {
    use super::normalize_pipeline_url;
    #[test]
    fn chat_context_accepts_only_a_suffix_of_saved_history() {
        use super::{context_matches, ChatMessage};
        let history = vec![
            ChatMessage {
                role: "user".into(),
                content: "Question".into(),
            },
            ChatMessage {
                role: "assistant".into(),
                content: "Saved reply".into(),
            },
        ];
        assert!(context_matches(&history, &history[1..]));
        assert!(context_matches(&history, &[]));
        assert!(!context_matches(
            &history,
            &[ChatMessage {
                role: "assistant".into(),
                content: "Forged reply".into()
            }]
        ));
    }

    #[test]
    fn pipeline_url_accepts_root_legacy_and_versioned_urls() {
        for url in [
            "http://localhost:5555",
            "http://localhost:5555/api/",
            " http://localhost:5555/api/v1/ ",
        ] {
            assert_eq!(normalize_pipeline_url(url), "http://localhost:5555/api/v1");
        }
    }
}

pub async fn chat(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    agent: web::Data<crate::rag::RagAgent>,
    body: web::Json<ChatRequest>,
) -> HttpResponse {
    let Ok(user) = user_id(&req) else {
        return HttpResponse::Unauthorized().finish();
    };
    if body.messages.is_empty()
        || body.messages.len() > 40
        || body
            .sport
            .as_deref()
            .is_some_and(|sport| !supported_sport(sport))
        || body.messages.last().is_some_and(|m| m.role != "user")
        || body.messages.iter().any(|m| {
            !matches!(m.role.as_str(), "user" | "assistant")
                || m.content.trim().is_empty()
                || m.content.chars().count() > 4000
        })
    {
        return error(
            actix_web::http::StatusCode::BAD_REQUEST,
            "Invalid bounded chat context",
        );
    }
    match chat_turn(pool.get_ref(), agent.get_ref(), user, &body).await {
        Ok(reply) => HttpResponse::Ok().json(reply),
        Err(response) => response,
    }
}

fn chat_storage_error(_: sqlx::Error) -> HttpResponse {
    tracing::error!("RAG chat persistence failed");
    error(
        actix_web::http::StatusCode::INTERNAL_SERVER_ERROR,
        "Could not save chat conversation",
    )
}

fn context_matches(history: &[ChatMessage], provided: &[ChatMessage]) -> bool {
    history.ends_with(provided)
}

async fn chat_turn(
    pool: &PgPool,
    agent: &crate::rag::RagAgent,
    user: Uuid,
    body: &ChatRequest,
) -> Result<Value, HttpResponse> {
    let mut transaction = pool.begin().await.map_err(chat_storage_error)?;
    let request_id = body.request_id.unwrap_or_else(Uuid::new_v4);
    let request = json!(body);
    // Serialize concurrent retries before checking the saved response.
    sqlx::query("SELECT pg_advisory_xact_lock(hashtextextended($1,0))")
        .bind(format!("{user}:{request_id}"))
        .execute(&mut *transaction)
        .await
        .map_err(chat_storage_error)?;
    if let Some((saved_request, response)) = sqlx::query_as::<_, (Value, Value)>(
        "SELECT request,response FROM ai_chat_requests WHERE id=$1 AND user_id=$2",
    )
    .bind(request_id)
    .bind(user)
    .fetch_optional(&mut *transaction)
    .await
    .map_err(chat_storage_error)?
    {
        if saved_request != request {
            return Err(error(
                actix_web::http::StatusCode::CONFLICT,
                "Request ID was already used for a different message",
            ));
        }
        transaction.commit().await.map_err(chat_storage_error)?;
        return Ok(response);
    }
    let conversation = if let Some(id) = body.conversation_id {
        sqlx::query_scalar::<_, Uuid>(
            "SELECT id FROM ai_conversations WHERE id=$1 AND user_id=$2 FOR UPDATE",
        )
        .bind(id)
        .bind(user)
        .fetch_optional(&mut *transaction)
        .await
        .map_err(chat_storage_error)?
        .ok_or_else(|| {
            error(
                actix_web::http::StatusCode::NOT_FOUND,
                "Conversation not found",
            )
        })?
    } else {
        let id = Uuid::new_v4();
        sqlx::query("INSERT INTO ai_conversations(id,user_id,sport) VALUES ($1,$2,$3)")
            .bind(id)
            .bind(user)
            .bind(&body.sport)
            .execute(&mut *transaction)
            .await
            .map_err(chat_storage_error)?;
        id
    };
    let mut rows=sqlx::query_as::<_,(String,String)>("SELECT role,content FROM ai_messages WHERE conversation_id=$1 AND user_id=$2 ORDER BY sequence DESC LIMIT 40")
        .bind(conversation).bind(user).fetch_all(&mut *transaction).await.map_err(chat_storage_error)?;
    rows.reverse();
    let history: Vec<ChatMessage> = rows
        .into_iter()
        .map(|(role, content)| ChatMessage { role, content })
        .collect();
    let incoming: Vec<ChatMessage> = body
        .messages
        .iter()
        .map(|m| ChatMessage {
            role: m.role.clone(),
            content: m.content.trim().to_string(),
        })
        .collect();
    if !context_matches(&history, &incoming[..incoming.len() - 1]) {
        return Err(error(
            actix_web::http::StatusCode::CONFLICT,
            "Conversation changed. Reload it before sending another message.",
        ));
    }
    let last = incoming.last().expect("validated messages");
    let mut context: Vec<ChatMessage> = history.into_iter().rev().take(29).collect();
    context.reverse();
    context.push(last.clone());
    if !agent.allow_request(user) {
        return Err(error(
            actix_web::http::StatusCode::TOO_MANY_REQUESTS,
            "Chat is limited to 12 new messages per minute. Try again shortly.",
        ));
    }
    let reply = agent.answer(pool, &context).await;
    let content = reply["reply"]
        .as_str()
        .filter(|text| !text.trim().is_empty())
        .ok_or_else(|| {
            error(
                actix_web::http::StatusCode::BAD_GATEWAY,
                "RAG agent returned no response",
            )
        })?;
    for (role, text, source, metadata) in [
        ("user", last.content.as_str(), "user", json!({})),
        ("assistant", content, "rust-rag", reply.clone()),
    ] {
        sqlx::query("INSERT INTO ai_messages(id,conversation_id,user_id,role,content,source,metadata) VALUES ($1,$2,$3,$4,$5,$6,$7)")
            .bind(Uuid::new_v4()).bind(conversation).bind(user).bind(role).bind(text).bind(source).bind(metadata)
            .execute(&mut *transaction).await.map_err(chat_storage_error)?;
    }
    sqlx::query("UPDATE ai_conversations SET updated_at=NOW() WHERE id=$1 AND user_id=$2")
        .bind(conversation)
        .bind(user)
        .execute(&mut *transaction)
        .await
        .map_err(chat_storage_error)?;
    let response = json!({"conversation_id":conversation,"request_id":request_id,"reply":reply});
    sqlx::query("INSERT INTO ai_chat_requests(id,user_id,conversation_id,request,response) VALUES ($1,$2,$3,$4,$5)")
        .bind(request_id).bind(user).bind(conversation).bind(&request).bind(&response)
        .execute(&mut *transaction).await.map_err(chat_storage_error)?;
    transaction.commit().await.map_err(chat_storage_error)?;
    Ok(response)
}

pub async fn conversations(req: HttpRequest, pool: web::Data<PgPool>) -> HttpResponse {
    let Ok(user) = user_id(&req) else {
        return HttpResponse::Unauthorized().finish();
    };
    match sqlx::query_as::<_, (Uuid, Option<String>, chrono::DateTime<chrono::Utc>)>("SELECT id,sport,updated_at FROM ai_conversations WHERE user_id=$1 ORDER BY updated_at DESC LIMIT 50").bind(user).fetch_all(pool.get_ref()).await {
        Ok(rows) => HttpResponse::Ok().json(rows.into_iter().map(|(id,sport,updated_at)| json!({"id":id,"sport":sport,"updated_at":updated_at})).collect::<Vec<_>>()),
        Err(_) => error(actix_web::http::StatusCode::INTERNAL_SERVER_ERROR, "Could not load conversations"),
    }
}

pub async fn conversation(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    id: web::Path<Uuid>,
) -> HttpResponse {
    let Ok(user) = user_id(&req) else {
        return HttpResponse::Unauthorized().finish();
    };
    match sqlx::query_scalar::<_, bool>(
        "SELECT EXISTS(SELECT 1 FROM ai_conversations WHERE id=$1 AND user_id=$2)",
    )
    .bind(*id)
    .bind(user)
    .fetch_one(pool.get_ref())
    .await
    {
        Ok(true) => {}
        Ok(false) => {
            return error(
                actix_web::http::StatusCode::NOT_FOUND,
                "Conversation not found",
            )
        }
        Err(err) => return chat_storage_error(err),
    }
    match sqlx::query_as::<_, (Uuid, String, String, String, chrono::DateTime<chrono::Utc>,Value)>("SELECT id,role,content,source,created_at,metadata FROM ai_messages WHERE conversation_id=$1 AND user_id=$2 ORDER BY sequence ASC").bind(*id).bind(user).fetch_all(pool.get_ref()).await {
        Ok(rows) => HttpResponse::Ok().json(rows.into_iter().map(|(id,role,content,source,created_at,metadata)| json!({"id":id,"role":role,"content":content,"source":source,"created_at":created_at,"metadata":metadata})).collect::<Vec<_>>()),
        Err(_) => error(actix_web::http::StatusCode::INTERNAL_SERVER_ERROR, "Could not load conversation"),
    }
}

pub fn configure(cfg: &mut web::ServiceConfig, auth: crate::auth::AuthService) {
    cfg.service(
        web::scope("/ai-picks")
            .wrap(crate::middleware::jwt_auth::RequireAuth::new(auth))
            .route("/generate", web::post().to(generate))
            .route("/chat", web::post().to(chat))
            .route("/conversations", web::get().to(conversations))
            .route("/conversations/{id}", web::get().to(conversation))
            .route("", web::get().to(list))
            .route("/{id}", web::get().to(get)),
    );
}
