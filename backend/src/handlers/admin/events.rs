/**
 * Admin Event Management API
 * 
 * Create, update, and manage sports events
 */

use actix_web::{web, HttpRequest, HttpResponse};
use bigdecimal::BigDecimal;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use std::str::FromStr;
use uuid::Uuid;

use crate::middleware::admin_auth::get_admin_claims;

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct EventRecord {
    pub id: Uuid,
    pub sport: String,
    pub league: String,
    pub home_team: String,
    pub away_team: String,
    pub event_date: DateTime<Utc>,
    pub status: String,
    pub home_score: Option<i32>,
    pub away_score: Option<i32>,
    pub moneyline_home: Option<BigDecimal>,
    pub moneyline_away: Option<BigDecimal>,
    pub point_spread: Option<BigDecimal>,
    pub spread_home_odds: Option<BigDecimal>,
    pub spread_away_odds: Option<BigDecimal>,
    pub total_points: Option<BigDecimal>,
    pub over_odds: Option<BigDecimal>,
    pub under_odds: Option<BigDecimal>,
    pub external_id: Option<String>,
    pub external_source: Option<String>,
    pub created_by: Option<Uuid>,
    pub updated_by: Option<Uuid>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

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
 * GET /api/v1/admin/events
 * 
 * Get all events with pagination
 */
pub async fn get_all_events(
    pool: web::Data<PgPool>,
    query: web::Query<serde_json::Value>,
    req: HttpRequest,
) -> HttpResponse {
    let _admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let limit: i64 = query.get("limit").and_then(|v| v.as_i64()).unwrap_or(50);
    let offset: i64 = query.get("offset").and_then(|v| v.as_i64()).unwrap_or(0);
    let sport = query.get("sport").and_then(|v| v.as_str());
    let status = query.get("status").and_then(|v| v.as_str());

    let events = if let (Some(sport_val), Some(status_val)) = (sport, status) {
        sqlx::query_as::<_, EventRecord>(
            r#"SELECT * FROM events WHERE sport = $1 AND status = $2 ORDER BY event_date DESC LIMIT $3 OFFSET $4"#
        )
        .bind(sport_val)
        .bind(status_val)
        .bind(limit)
        .bind(offset)
        .fetch_all(pool.get_ref())
        .await
    } else if let Some(sport_val) = sport {
        sqlx::query_as::<_, EventRecord>(
            r#"SELECT * FROM events WHERE sport = $1 ORDER BY event_date DESC LIMIT $2 OFFSET $3"#
        )
        .bind(sport_val)
        .bind(limit)
        .bind(offset)
        .fetch_all(pool.get_ref())
        .await
    } else if let Some(status_val) = status {
        sqlx::query_as::<_, EventRecord>(
            r#"SELECT * FROM events WHERE status = $1 ORDER BY event_date DESC LIMIT $2 OFFSET $3"#
        )
        .bind(status_val)
        .bind(limit)
        .bind(offset)
        .fetch_all(pool.get_ref())
        .await
    } else {
        sqlx::query_as::<_, EventRecord>(
            r#"SELECT * FROM events ORDER BY event_date DESC LIMIT $1 OFFSET $2"#
        )
        .bind(limit)
        .bind(offset)
        .fetch_all(pool.get_ref())
        .await
    };

    match events {
        Ok(data) => HttpResponse::Ok().json(serde_json::json!({
            "events": data,
            "count": data.len()
        })),
        Err(e) => {
            eprintln!("Error fetching events: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to fetch events"}))
        }
    }
}

/**
 * GET /api/v1/admin/events/:id
 * 
 * Get single event by ID
 */
pub async fn get_event(
    pool: web::Data<PgPool>,
    event_id: web::Path<Uuid>,
    req: HttpRequest,
) -> HttpResponse {
    let _admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let result = sqlx::query_as::<_, EventRecord>(
        r#"SELECT * FROM events WHERE id = $1"#
    )
    .bind(event_id.into_inner())
    .fetch_one(pool.get_ref())
    .await;

    match result {
        Ok(event) => HttpResponse::Ok().json(event),
        Err(e) => {
            eprintln!("Error fetching event: {}", e);
            HttpResponse::NotFound().json(serde_json::json!({"error": "Event not found"}))
        }
    }
}

/**
 * PUT /api/v1/admin/events/:id
 * 
 * Update an event
 */
#[derive(Debug, Deserialize)]
pub struct UpdateEventRequest {
    pub sport: Option<String>,
    pub league: Option<String>,
    pub home_team: Option<String>,
    pub away_team: Option<String>,
    pub event_date: Option<String>,
    pub status: Option<String>,
    pub home_score: Option<i32>,
    pub away_score: Option<i32>,
    pub moneyline_home: Option<f64>,
    pub moneyline_away: Option<f64>,
    pub point_spread: Option<f64>,
    pub spread_home_odds: Option<f64>,
    pub spread_away_odds: Option<f64>,
    pub total_points: Option<f64>,
    pub over_odds: Option<f64>,
    pub under_odds: Option<f64>,
}

pub async fn update_event(
    pool: web::Data<PgPool>,
    event_id: web::Path<Uuid>,
    body: web::Json<UpdateEventRequest>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let admin_id: Uuid = admin_claims.sub.parse().unwrap();
    let event_id = event_id.into_inner();

    // Build dynamic update query
    let mut query_parts = vec![];
    let mut param_count = 1;

    if body.sport.is_some() {
        query_parts.push(format!("sport = ${}", param_count));
        param_count += 1;
    }
    if body.league.is_some() {
        query_parts.push(format!("league = ${}", param_count));
        param_count += 1;
    }
    if body.home_team.is_some() {
        query_parts.push(format!("home_team = ${}", param_count));
        param_count += 1;
    }
    if body.away_team.is_some() {
        query_parts.push(format!("away_team = ${}", param_count));
        param_count += 1;
    }
    if body.status.is_some() {
        query_parts.push(format!("status = ${}", param_count));
        param_count += 1;
    }
    if body.home_score.is_some() {
        query_parts.push(format!("home_score = ${}", param_count));
        param_count += 1;
    }
    if body.away_score.is_some() {
        query_parts.push(format!("away_score = ${}", param_count));
        param_count += 1;
    }

    if query_parts.is_empty() {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "No fields to update"}));
    }

    query_parts.push(format!("updated_by = ${}", param_count));
    param_count += 1;
    query_parts.push("updated_at = NOW()".to_string());

    let query_str = format!(
        "UPDATE events SET {} WHERE id = ${}",
        query_parts.join(", "),
        param_count
    );

    let mut query = sqlx::query(&query_str);

    if let Some(ref sport) = body.sport {
        query = query.bind(sport);
    }
    if let Some(ref league) = body.league {
        query = query.bind(league);
    }
    if let Some(ref home_team) = body.home_team {
        query = query.bind(home_team);
    }
    if let Some(ref away_team) = body.away_team {
        query = query.bind(away_team);
    }
    if let Some(ref status) = body.status {
        query = query.bind(status);
    }
    if let Some(home_score) = body.home_score {
        query = query.bind(home_score);
    }
    if let Some(away_score) = body.away_score {
        query = query.bind(away_score);
    }

    query = query.bind(admin_id).bind(event_id);

    let result = query.execute(pool.get_ref()).await;

    match result {
        Ok(_) => {
            // Log admin action
            let _ = sqlx::query!(
                "INSERT INTO admin_logs (admin_id, action, target_type, target_id) VALUES ($1, 'update_event', 'event', $2)",
                admin_id,
                event_id
            )
            .execute(pool.get_ref())
            .await;

            HttpResponse::Ok().json(serde_json::json!({"success": true, "message": "Event updated"}))
        }
        Err(e) => {
            eprintln!("Error updating event: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to update event"}))
        }
    }
}

/**
 * DELETE /api/v1/admin/events/:id
 * 
 * Delete an event
 */
pub async fn delete_event(
    pool: web::Data<PgPool>,
    event_id: web::Path<Uuid>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let admin_id: Uuid = admin_claims.sub.parse().unwrap();
    let event_id = event_id.into_inner();

    // Check if there are any bets on this event
    let bet_count = sqlx::query!(
        "SELECT COUNT(*) as count FROM bets WHERE event_id = $1",
        event_id
    )
    .fetch_one(pool.get_ref())
    .await;

    if let Ok(count) = bet_count {
        if count.count.unwrap_or(0) > 0 {
            return HttpResponse::BadRequest().json(serde_json::json!({
                "error": "Cannot delete event with existing bets"
            }));
        }
    }

    let result = sqlx::query!("DELETE FROM events WHERE id = $1", event_id)
        .execute(pool.get_ref())
        .await;

    match result {
        Ok(_) => {
            // Log admin action
            let _ = sqlx::query!(
                "INSERT INTO admin_logs (admin_id, action, target_type, target_id) VALUES ($1, 'delete_event', 'event', $2)",
                admin_id,
                event_id
            )
            .execute(pool.get_ref())
            .await;

            HttpResponse::Ok().json(serde_json::json!({"success": true, "message": "Event deleted"}))
        }
        Err(e) => {
            eprintln!("Error deleting event: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to delete event"}))
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
