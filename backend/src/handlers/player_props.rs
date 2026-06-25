use actix_web::{web, HttpResponse};
use bigdecimal::BigDecimal;
use serde::Deserialize;
use sqlx::PgPool;
use tracing::error;
use uuid::Uuid;

#[derive(Debug, serde::Serialize, sqlx::FromRow)]
pub struct PlayerProp {
    pub id: Uuid,
    pub event_id: Uuid,
    pub sport: String,
    pub league: String,
    pub player_name: String,
    pub team: Option<String>,
    pub market: String,
    pub line: BigDecimal,
    pub over_odds: Option<BigDecimal>,
    pub under_odds: Option<BigDecimal>,
    pub source: Option<String>,
    pub source_updated_at: Option<chrono::DateTime<chrono::Utc>>,
    pub is_active: bool,
}

#[derive(Debug, Deserialize)]
pub struct PlayerPropsQuery {
    pub sport: Option<String>,
    pub event_id: Option<Uuid>,
    pub player: Option<String>,
    pub market: Option<String>,
}

pub async fn get_player_props(
    pool: web::Data<PgPool>,
    query: web::Query<PlayerPropsQuery>,
) -> HttpResponse {
    let props = sqlx::query_as::<_, PlayerProp>(
        r#"
        SELECT id, event_id, sport, league, player_name, team, market, line,
               over_odds, under_odds, source, source_updated_at, is_active
        FROM player_props
        WHERE is_active = true
          AND ($1::text IS NULL OR sport = $1)
          AND ($2::uuid IS NULL OR event_id = $2)
          AND ($3::text IS NULL OR player_name ILIKE '%' || $3 || '%')
          AND ($4::text IS NULL OR market = $4)
        ORDER BY sport, league, player_name
        LIMIT 200
        "#,
    )
    .bind(&query.sport)
    .bind(query.event_id)
    .bind(&query.player)
    .bind(&query.market)
    .fetch_all(pool.get_ref())
    .await;

    match props {
        Ok(props) => HttpResponse::Ok().json(props),
        Err(e) => {
            error!("Failed to fetch player props: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to fetch player props"
            }))
        }
    }
}

pub async fn get_player_props_by_event(
    pool: web::Data<PgPool>,
    path: web::Path<Uuid>,
) -> HttpResponse {
    let event_id = path.into_inner();
    let props = sqlx::query_as::<_, PlayerProp>(
        r#"
        SELECT id, event_id, sport, league, player_name, team, market, line,
               over_odds, under_odds, source, source_updated_at, is_active
        FROM player_props
        WHERE event_id = $1 AND is_active = true
        ORDER BY player_name, market
        "#,
    )
    .bind(event_id)
    .fetch_all(pool.get_ref())
    .await;

    match props {
        Ok(props) => HttpResponse::Ok().json(props),
        Err(e) => {
            error!("Failed to fetch player props for event: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to fetch player props"
            }))
        }
    }
}
