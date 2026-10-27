//! Database-backed feature policy. No role, including superadmin, bypasses it.
use actix_web::{
    body::BoxBody,
    dev::{forward_ready, Service, ServiceResponse, Transform},
    Error,
};
use actix_web::{dev::ServiceRequest, web, HttpRequest, HttpResponse, ResponseError};
use futures_util::future::LocalBoxFuture;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sqlx::{FromRow, PgPool};
use std::{
    future::{ready, Ready},
    rc::Rc,
};
use uuid::Uuid;

pub struct FeatureGate;
pub struct FeatureGateService<S> {
    service: Rc<S>,
}
impl<S, B> Transform<S, ServiceRequest> for FeatureGate
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    S::Future: 'static,
    B: actix_web::body::MessageBody + 'static,
{
    type Response = ServiceResponse<BoxBody>;
    type Error = Error;
    type InitError = ();
    type Transform = FeatureGateService<S>;
    type Future = Ready<Result<Self::Transform, ()>>;
    fn new_transform(&self, service: S) -> Self::Future {
        ready(Ok(FeatureGateService {
            service: Rc::new(service),
        }))
    }
}
impl<S, B> Service<ServiceRequest> for FeatureGateService<S>
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    S::Future: 'static,
    B: actix_web::body::MessageBody + 'static,
{
    type Response = ServiceResponse<BoxBody>;
    type Error = Error;
    type Future = LocalBoxFuture<'static, Result<Self::Response, Error>>;
    forward_ready!(service);
    fn call(&self, req: ServiceRequest) -> Self::Future {
        let service = self.service.clone();
        Box::pin(async move {
            match check_request(&req).await {
                Ok(()) => service.call(req).await.map(|r| r.map_into_boxed_body()),
                Err(err) => Ok(req.into_response(err.error_response())),
            }
        })
    }
}

#[derive(Debug, thiserror::Error)]
pub enum FeatureError {
    #[error("This feature is currently unavailable.")]
    Disabled,
    #[error("Authentication required.")]
    Unauthorized,
    #[error("Administrative access required.")]
    Forbidden,
    #[error("Unknown feature or target.")]
    NotFound,
    #[error("Invalid feature configuration.")]
    Invalid,
    #[error("Feature availability could not be verified.")]
    Storage(#[from] sqlx::Error),
}
impl ResponseError for FeatureError {
    fn status_code(&self) -> actix_web::http::StatusCode {
        use actix_web::http::StatusCode as S;
        match self {
            Self::Disabled | Self::Forbidden => S::FORBIDDEN,
            Self::Unauthorized => S::UNAUTHORIZED,
            Self::NotFound => S::NOT_FOUND,
            Self::Invalid => S::BAD_REQUEST,
            Self::Storage(_) => S::SERVICE_UNAVAILABLE,
        }
    }
    fn error_response(&self) -> HttpResponse {
        let code = match self {
            Self::Disabled => "FEATURE_DISABLED",
            Self::Unauthorized => "UNAUTHORIZED",
            Self::Forbidden => "FORBIDDEN",
            Self::NotFound => "UNKNOWN_FEATURE_OR_TARGET",
            Self::Invalid => "INVALID_FEATURE_CONFIGURATION",
            Self::Storage(err) => {
                tracing::error!(error = %err, "Feature policy database failure");
                "FEATURE_SERVICE_UNAVAILABLE"
            }
        };
        HttpResponse::build(self.status_code())
            .insert_header(("Cache-Control", "no-store"))
            .json(json!({"error":{"code":code,"message":self.to_string()}}))
    }
}

#[derive(Debug, FromRow, Serialize)]
pub struct Feature {
    pub key: String,
    pub description: String,
    pub category: String,
    pub enabled: bool,
    pub emergency_disabled: bool,
    pub maintenance_allowed: bool,
    pub default_enabled: bool,
}
#[derive(FromRow)]
struct Policy {
    enabled: bool,
    emergency_disabled: bool,
    maintenance_allowed: bool,
    default_enabled: bool,
    user_enabled: Option<bool>,
    role_enabled: Option<bool>,
    maintenance: bool,
}
fn evaluate(p: &Policy) -> bool {
    p.enabled
        && !p.emergency_disabled
        && (!p.maintenance || p.maintenance_allowed)
        && p.user_enabled != Some(false)
        && p.role_enabled != Some(false)
        && p.user_enabled
            .or(p.role_enabled)
            .unwrap_or(p.default_enabled)
}

pub async fn identity(
    req: &HttpRequest,
    pool: &PgPool,
) -> Result<(Option<Uuid>, String), FeatureError> {
    let Some(header) = req.headers().get("Authorization") else {
        return Ok((None, "guest".into()));
    };
    let token = header
        .to_str()
        .ok()
        .and_then(|v| v.strip_prefix("Bearer "))
        .ok_or(FeatureError::Unauthorized)?;
    let auth = req
        .app_data::<web::Data<crate::auth::AuthService>>()
        .ok_or(FeatureError::Unauthorized)?;
    let claims = auth
        .validate_request_token(token)
        .await
        .map_err(|error| match error {
            crate::errors::AppError::Database(error) => FeatureError::Storage(error),
            _ => FeatureError::Unauthorized,
        })?;
    let id = claims
        .sub
        .parse::<Uuid>()
        .map_err(|_| FeatureError::Unauthorized)?;
    let role = sqlx::query_scalar::<_, String>("SELECT COALESCE(role,'user') FROM users WHERE id=$1 AND is_active AND (locked_until IS NULL OR locked_until<=NOW())")
        .bind(id).fetch_optional(pool).await?.ok_or(FeatureError::Unauthorized)?;
    Ok((Some(id), role))
}
pub async fn administrator(req: &HttpRequest, pool: &PgPool) -> Result<Uuid, FeatureError> {
    let (id, role) = identity(req, pool).await?;
    if id.is_none() {
        return Err(FeatureError::Unauthorized);
    }
    if !matches!(role.as_str(), "admin" | "superadmin") {
        return Err(FeatureError::Forbidden);
    }
    id.ok_or(FeatureError::Unauthorized)
}
async fn available(
    pool: &PgPool,
    key: &str,
    user: Option<Uuid>,
    role: &str,
) -> Result<bool, FeatureError> {
    if key == "wallet_funding"
        && std::env::var("APP_ENV").is_ok_and(|value| value.eq_ignore_ascii_case("production"))
    {
        return Ok(false);
    }
    let policy = sqlx::query_as::<_, Policy>(
        "SELECT f.enabled,f.emergency_disabled,f.maintenance_allowed,f.default_enabled,
        u.enabled user_enabled,r.enabled role_enabled,
        COALESCE((SELECT enabled OR emergency_disabled FROM feature_flags WHERE key='maintenance'),TRUE) maintenance
        FROM feature_flags f LEFT JOIN user_feature_overrides u ON u.feature_key=f.key AND u.user_id=$2
        LEFT JOIN role_feature_rules r ON r.feature_key=f.key AND r.role=$3 WHERE f.key=$1 AND f.key<>'maintenance'")
        .bind(key).bind(user).bind(role).fetch_optional(pool).await?;
    Ok(policy.as_ref().is_some_and(evaluate))
}

/// Every exposed product route maps here, including the private Python gateway.
pub fn route_features(path: &str) -> Vec<&'static str> {
    let p = path.strip_prefix("/api/v1").unwrap_or(path);
    let p = p.strip_prefix("/pipeline").unwrap_or(p);
    if p == "/auth/register" {
        return vec!["registration"];
    }
    if p.starts_with("/ai-picks/chat")
        || p.starts_with("/ai-picks/conversations")
        || p == "/chat"
        || p.starts_with("/smart-assistant")
    {
        return vec!["ai_chat"];
    }
    if p.starts_with("/ai-picks") {
        return vec!["ai_picks"];
    }
    if p.starts_with("/wallet/deposit") || p.starts_with("/wallet/withdraw") {
        return vec!["wallet", "wallet_funding"];
    }
    for (prefix, key) in [
        ("/wallet", "wallet"),
        ("/betting", "betting"),
        ("/player-props", "player_props"),
        ("/parlay", "parlays"),
        ("/suggested-parlays", "parlays"),
        ("/best-value-bets", "best_picks"),
        ("/betting-intel", "intelligence"),
        ("/intelligence", "intelligence"),
        ("/fpl", "fpl"),
        ("/ncaab", "college"),
        ("/sports", "sports"),
        ("/predictions", "predictions"),
        ("/prediction-dashboard", "predictions"),
        ("/sport-models", "predictions"),
        ("/matches", "predictions"),
        ("/matchup", "predictions"),
        ("/model", "predictions"),
    ] {
        if p == prefix || p.strip_prefix(prefix).is_some_and(|s| s.starts_with('/')) {
            return vec![key];
        }
    }
    // Unknown upstream routes must never become an unguarded gateway.
    if path.starts_with("/api/v1/pipeline") {
        return vec!["predictions"];
    }
    vec![]
}
pub async fn check_request(req: &ServiceRequest) -> Result<(), FeatureError> {
    if req.method() == actix_web::http::Method::OPTIONS {
        return Ok(());
    }
    // Policy and router must agree on static segments. Product paths use ASCII
    // keys/UUIDs; sport names are the only supported encoded path parameters.
    if req.path().contains('%') && !req.path().starts_with("/api/v1/sports/") {
        return Err(FeatureError::Invalid);
    }
    let keys = route_features(req.path());
    if keys.is_empty() {
        return Ok(());
    }
    let production = req
        .app_data::<web::Data<crate::config::AppConfig>>()
        .is_some_and(|c| c.app_env.eq_ignore_ascii_case("production"));
    let placement = req.method() == actix_web::http::Method::POST
        && matches!(req.path(), "/api/v1/betting/bets" | "/api/v1/parlay/place");
    if production && (keys.contains(&"wallet_funding") || placement) {
        return Err(FeatureError::Disabled);
    }
    let pool = req
        .app_data::<web::Data<PgPool>>()
        .ok_or(FeatureError::Invalid)?;
    let (user, role) = identity(req.request(), pool).await?;
    if req.path() == "/api/v1/intelligence/refresh" {
        administrator(req.request(), pool).await?;
    }
    for key in keys {
        if !available(pool, key, user, &role).await? {
            return Err(FeatureError::Disabled);
        }
    }
    Ok(())
}

pub async fn effective(
    req: HttpRequest,
    pool: web::Data<PgPool>,
) -> Result<HttpResponse, FeatureError> {
    let (user, role) = identity(&req, &pool).await?;
    effective_for(&pool, user, &role).await
}
async fn effective_for(
    pool: &PgPool,
    user: Option<Uuid>,
    role: &str,
) -> Result<HttpResponse, FeatureError> {
    let keys = sqlx::query_scalar::<_, String>(
        "SELECT key FROM feature_flags WHERE key<>'maintenance' ORDER BY key",
    )
    .fetch_all(pool)
    .await?;
    let mut result = serde_json::Map::new();
    for key in keys {
        result.insert(key.clone(), json!(available(pool, &key, user, role).await?));
    }
    Ok(HttpResponse::Ok()
        .insert_header(("Cache-Control", "no-store"))
        .json(json!({"features":result})))
}
pub async fn list(req: HttpRequest, pool: web::Data<PgPool>) -> Result<HttpResponse, FeatureError> {
    administrator(&req, &pool).await?;
    let flags = sqlx::query_as::<_, Feature>("SELECT key,description,category,enabled,emergency_disabled,maintenance_allowed,default_enabled FROM feature_flags ORDER BY category,key").fetch_all(pool.get_ref()).await?;
    let roles = sqlx::query_as::<_, (String, String, bool)>(
        "SELECT feature_key,role,enabled FROM role_feature_rules ORDER BY feature_key,role",
    )
    .fetch_all(pool.get_ref())
    .await?;
    Ok(HttpResponse::Ok().insert_header(("Cache-Control","no-store")).json(json!({"features":flags,"roles":roles.into_iter().map(|(key,role,enabled)|json!({"key":key,"role":role,"enabled":enabled})).collect::<Vec<_>>()})))
}
pub async fn user_features(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    id: web::Path<Uuid>,
) -> Result<HttpResponse, FeatureError> {
    administrator(&req, &pool).await?;
    let role =
        sqlx::query_scalar::<_, String>("SELECT COALESCE(role,'user') FROM users WHERE id=$1")
            .bind(*id)
            .fetch_optional(pool.get_ref())
            .await?
            .ok_or(FeatureError::NotFound)?;
    let overrides = sqlx::query_as::<_, (String, bool)>(
        "SELECT feature_key,enabled FROM user_feature_overrides WHERE user_id=$1",
    )
    .bind(*id)
    .fetch_all(pool.get_ref())
    .await?;
    // Keep the response directly consumable without exposing internal policy.
    let mut flags = serde_json::Map::new();
    for (key, enabled) in overrides {
        flags.insert(key, json!(enabled));
    }
    let keys =
        sqlx::query_scalar::<_, String>("SELECT key FROM feature_flags WHERE key<>'maintenance'")
            .fetch_all(pool.get_ref())
            .await?;
    let mut access = serde_json::Map::new();
    for key in keys {
        access.insert(
            key.clone(),
            json!(available(&pool, &key, Some(*id), &role).await?),
        );
    }
    Ok(HttpResponse::Ok()
        .insert_header(("Cache-Control", "no-store"))
        .json(json!({"features":access,"overrides":flags,"role":role})))
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Change {
    pub enabled: Option<bool>,
    pub emergency_disabled: Option<bool>,
    pub maintenance_allowed: Option<bool>,
}
pub async fn patch_flag(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    key: web::Path<String>,
    body: web::Json<Change>,
) -> Result<HttpResponse, FeatureError> {
    mutate(&req, &pool, &key, "global", &body).await
}
pub async fn patch_user(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    path: web::Path<(Uuid, String)>,
    body: web::Json<Change>,
) -> Result<HttpResponse, FeatureError> {
    mutate(&req, &pool, &path.1, &format!("user:{}", path.0), &body).await
}
pub async fn patch_role(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    path: web::Path<(String, String)>,
    body: web::Json<Change>,
) -> Result<HttpResponse, FeatureError> {
    if !matches!(path.1.as_str(), "guest" | "user" | "admin" | "superadmin") {
        return Err(FeatureError::Invalid);
    }
    mutate(&req, &pool, &path.0, &format!("role:{}", path.1), &body).await
}
async fn mutate(
    req: &HttpRequest,
    pool: &PgPool,
    key: &str,
    target: &str,
    body: &Change,
) -> Result<HttpResponse, FeatureError> {
    let admin = administrator(req, pool).await?;
    let mut tx = pool.begin().await?;
    // Recheck and lock the administrator so concurrent suspension/demotion cannot
    // race an audited mutation.
    let authorized = sqlx::query_scalar::<_, Uuid>("SELECT id FROM users WHERE id=$1 AND role IN ('admin','superadmin') AND is_active FOR SHARE")
        .bind(admin).fetch_optional(&mut *tx).await?;
    if authorized.is_none() {
        return Err(FeatureError::Forbidden);
    }
    let before = sqlx::query_scalar::<_, Value>(
        "SELECT to_jsonb(f) FROM feature_flags f WHERE key=$1 FOR UPDATE",
    )
    .bind(key)
    .fetch_optional(&mut *tx)
    .await?
    .ok_or(FeatureError::NotFound)?;
    let (old, new) = if target == "global" {
        if body.enabled.is_none()
            && body.emergency_disabled.is_none()
            && body.maintenance_allowed.is_none()
        {
            return Err(FeatureError::Invalid);
        }
        let new = sqlx::query_scalar::<_, Value>("UPDATE feature_flags SET enabled=COALESCE($2,enabled),emergency_disabled=COALESCE($3,emergency_disabled),maintenance_allowed=COALESCE($4,maintenance_allowed),updated_at=NOW() WHERE key=$1 RETURNING to_jsonb(feature_flags)")
            .bind(key).bind(body.enabled).bind(body.emergency_disabled).bind(body.maintenance_allowed).fetch_one(&mut *tx).await?;
        (before, new)
    } else {
        if key == "maintenance"
            || body.emergency_disabled.is_some()
            || body.maintenance_allowed.is_some()
        {
            return Err(FeatureError::Invalid);
        }
        let old;
        if let Some(id) = target.strip_prefix("user:") {
            let id = id.parse::<Uuid>().map_err(|_| FeatureError::Invalid)?;
            if sqlx::query_scalar::<_, Uuid>("SELECT id FROM users WHERE id=$1")
                .bind(id)
                .fetch_optional(&mut *tx)
                .await?
                .is_none()
            {
                return Err(FeatureError::NotFound);
            }
            old = sqlx::query_scalar::<_, bool>(
                "SELECT enabled FROM user_feature_overrides WHERE user_id=$1 AND feature_key=$2",
            )
            .bind(id)
            .bind(key)
            .fetch_optional(&mut *tx)
            .await?;
            if let Some(enabled) = body.enabled {
                sqlx::query("INSERT INTO user_feature_overrides(user_id,feature_key,enabled) VALUES($1,$2,$3) ON CONFLICT(user_id,feature_key) DO UPDATE SET enabled=EXCLUDED.enabled").bind(id).bind(key).bind(enabled).execute(&mut *tx).await?;
            } else {
                sqlx::query(
                    "DELETE FROM user_feature_overrides WHERE user_id=$1 AND feature_key=$2",
                )
                .bind(id)
                .bind(key)
                .execute(&mut *tx)
                .await?;
            }
        } else if let Some(role) = target.strip_prefix("role:") {
            old = sqlx::query_scalar::<_, bool>(
                "SELECT enabled FROM role_feature_rules WHERE role=$1 AND feature_key=$2",
            )
            .bind(role)
            .bind(key)
            .fetch_optional(&mut *tx)
            .await?;
            if let Some(enabled) = body.enabled {
                sqlx::query("INSERT INTO role_feature_rules(role,feature_key,enabled) VALUES($1,$2,$3) ON CONFLICT(role,feature_key) DO UPDATE SET enabled=EXCLUDED.enabled").bind(role).bind(key).bind(enabled).execute(&mut *tx).await?;
            } else {
                return Err(FeatureError::Invalid);
            }
        } else {
            return Err(FeatureError::Invalid);
        }
        (json!(old), json!(body.enabled))
    };
    sqlx::query("INSERT INTO feature_audit_logs(administrator_id,action,feature_key,target,before_value,after_value) VALUES($1,'update',$2,$3,$4,$5)")
        .bind(admin).bind(key).bind(target).bind(old).bind(new).execute(&mut *tx).await?;
    tx.commit().await?;
    Ok(HttpResponse::Ok().json(json!({"success":true})))
}
#[derive(Deserialize)]
pub struct AuditQuery {
    pub before_id: Option<i64>,
}
pub async fn audit(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    query: web::Query<AuditQuery>,
) -> Result<HttpResponse, FeatureError> {
    administrator(&req, &pool).await?;
    let rows = sqlx::query_scalar::<_,Value>("SELECT to_jsonb(a) FROM feature_audit_logs a WHERE ($1::bigint IS NULL OR id<$1) ORDER BY id DESC LIMIT 100").bind(query.before_id).fetch_all(pool.get_ref()).await?;
    Ok(HttpResponse::Ok()
        .insert_header(("Cache-Control", "no-store"))
        .json(rows))
}
pub fn configure_admin(cfg: &mut web::ServiceConfig) {
    cfg.route("/features", web::get().to(list))
        .route("/features/audit", web::get().to(audit))
        .route("/features/{key}", web::patch().to(patch_flag))
        .route("/features/{key}/roles/{role}", web::patch().to(patch_role))
        .route("/users/{id}/features", web::get().to(user_features))
        .route("/users/{id}/features/{key}", web::patch().to(patch_user));
}

#[cfg(test)]
mod tests {
    use super::*;
    fn policy() -> Policy {
        Policy {
            enabled: true,
            emergency_disabled: false,
            maintenance_allowed: false,
            default_enabled: true,
            user_enabled: None,
            role_enabled: Some(true),
            maintenance: false,
        }
    }
    #[test]
    fn precedence() {
        let mut p = policy();
        assert!(evaluate(&p));
        p.emergency_disabled = true;
        p.user_enabled = Some(true);
        assert!(!evaluate(&p));
        p.emergency_disabled = false;
        p.enabled = false;
        assert!(!evaluate(&p));
        p.enabled = true;
        p.user_enabled = Some(false);
        assert!(!evaluate(&p));
        p.user_enabled = Some(true);
        p.role_enabled = Some(false);
        assert!(!evaluate(&p));
        p.role_enabled = Some(true);
        p.maintenance = true;
        assert!(!evaluate(&p));
        p.maintenance_allowed = true;
        assert!(evaluate(&p));
        p.user_enabled = None;
        p.role_enabled = None;
        p.default_enabled = false;
        assert!(!evaluate(&p));
    }
    #[test]
    fn sensitive_route_coverage() {
        assert_eq!(
            route_features("/api/v1/wallet/deposit"),
            vec!["wallet", "wallet_funding"]
        );
        assert_eq!(route_features("/api/v1/betting/bets"), vec!["betting"]);
        assert_eq!(route_features("/api/v1/ai-picks/chat"), vec!["ai_chat"]);
        assert_eq!(
            route_features("/api/v1/pipeline/unknown"),
            vec!["predictions"]
        );
        for path in [
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",
            "/api/v1/limits/self-exclude",
            "/api/v1/admin/features",
        ] {
            assert!(route_features(path).is_empty());
        }
    }
}

#[cfg(test)]
#[path = "feature_tests.rs"]
mod integration_tests;

#[cfg(test)]
#[path = "financial_tests.rs"]
mod financial_tests;
