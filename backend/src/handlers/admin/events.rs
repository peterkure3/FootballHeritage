/**
 * Admin Event Management API
 * 
 * Create, update, and manage sports events
 */

use actix_web::{web, HttpRequest, HttpResponse};
use bigdecimal::BigDecimal;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use std::str::FromStr;
use uuid::Uuid;

use crate::middleware::admin_auth::get_admin_claims;

#[derive(Debug, Deserialize)]
pub struct CreateEventRequest {
    pub sport: String,
    pub league: String,
    pub home_team: String,
    pub away_team: String,
    pub event_date: String,  // ISO 8601 format
    pub moneyline_home: Option<f64>,
    pub moneyline_away: Option<f64>,
    pub point_spread: Option<f64>,
    pub spread_home_odds: Option<f64>,
    pub spread_away_odds: Option<f64>,
    pub total_points: Option<f64>,
    pub over_odds: Option<f64>,
    pub under_odds: Option<f64>,
}

#[derive(Debug, Serialize)]
pub struct EventResponse {
    pub id: Uuid,
    pub sport: String,
    pub league: String,
    pub home_team: String,
    pub away_team: String,
    pub event_date: String,
    pub status: String,
}

/**
 * POST /api/v1/admin/events
 * 
 * Create a new sports event
 */
pub async fn create_event(
    pool: web::Data<PgPool>,
    body: web::Json<CreateEventRequest>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let admin_id: Uuid = admin_claims.sub.parse().unwrap();

    // Parse event date
    let event_date = match chrono::DateTime::parse_from_rfc3339(&body.event_date) {
        Ok(dt) => dt.with_timezone(&chrono::Utc),
        Err(_) => {
            return HttpResponse::BadRequest().json(serde_json::json!({
                "error": "Invalid event_date format. Use ISO 8601 (e.g., 2024-10-25T18:00:00Z)"
            }));
        }
    };

    // Insert event
    let result = sqlx::query!(
        r#"
        INSERT INTO events (
            sport, league, home_team, away_team, event_date,
            moneyline_home, moneyline_away,
            point_spread, spread_home_odds, spread_away_odds,
            total_points, over_odds, under_odds,
            created_by, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 'UPCOMING')
        RETURNING id, sport, league, home_team, away_team, event_date, status
        "#,
        body.sport,
        body.league,
        body.home_team,
        body.away_team,
        event_date,
        body.moneyline_home.map(|v| BigDecimal::from_str(&v.to_string()).ok()).flatten(),
        body.moneyline_away.map(|v| BigDecimal::from_str(&v.to_string()).ok()).flatten(),
        body.point_spread.map(|v| BigDecimal::from_str(&v.to_string()).ok()).flatten(),
        body.spread_home_odds.map(|v| BigDecimal::from_str(&v.to_string()).ok()).flatten(),
        body.spread_away_odds.map(|v| BigDecimal::from_str(&v.to_string()).ok()).flatten(),
        body.total_points.map(|v| BigDecimal::from_str(&v.to_string()).ok()).flatten(),
        body.over_odds.map(|v| BigDecimal::from_str(&v.to_string()).ok()).flatten(),
        body.under_odds.map(|v| BigDecimal::from_str(&v.to_string()).ok()).flatten(),
        admin_id
    )
    .fetch_one(pool.get_ref())
    .await;

    match result {
        Ok(event) => {
            // Log admin action
            let _ = sqlx::query!(
                "INSERT INTO admin_logs (admin_id, action, target_type, target_id) VALUES ($1, 'create_event', 'event', $2)",
                admin_id,
                event.id
            )
            .execute(pool.get_ref())
            .await;

            HttpResponse::Created().json(EventResponse {
                id: event.id,
                sport: event.sport,
                league: event.league,
                home_team: event.home_team,
                away_team: event.away_team,
                event_date: event.event_date.to_rfc3339(),
                status: event.status.unwrap_or_else(|| "UPCOMING".to_string()),
            })
        }
        Err(e) => {
            eprintln!("Error creating event: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to create event"
            }))
        }
    }
}

/**
 * PUT /api/v1/admin/events/:id/status
 * 
 * Update event status (UPCOMING, LIVE, FINISHED)
 */
pub async fn update_event_status(
    pool: web::Data<PgPool>,
    event_id: web::Path<Uuid>,
    body: web::Json<serde_json::Value>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let status = match body.get("status").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return HttpResponse::BadRequest().json(serde_json::json!({"error": "Missing status field"})),
    };

    let result = sqlx::query!(
        "UPDATE events SET status = $1, updated_by = $2, updated_at = NOW() WHERE id = $3",
        status,
        admin_claims.sub.parse::<Uuid>().unwrap(),
        event_id.into_inner()
    )
    .execute(pool.get_ref())
    .await;

    match result {
        Ok(_) => HttpResponse::Ok().json(serde_json::json!({"success": true, "message": "Event status updated"})),
        Err(e) => {
            eprintln!("Error updating event status: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to update event"}))
        }
    }
}
