/**
 * Admin Analytics API
 *
 * Dashboard metrics and analytics for admins
 */
use actix_web::{web, HttpRequest, HttpResponse};
use bigdecimal::BigDecimal;
use serde::Serialize;
use sqlx::PgPool;

use crate::middleware::admin_auth::get_admin_claims;

#[derive(Debug, Serialize)]
pub struct DashboardMetrics {
    pub total_users: i64,
    pub new_users_today: i64,
    pub active_users_today: i64,
    pub total_bets_today: i64,
    pub bet_volume_today: f64,
    pub revenue_today: f64,
    pub live_events: i64,
    pub upcoming_events: i64,
    pub pending_alerts: i64,
    pub critical_alerts: i64,
}

/**
 * GET /api/v1/admin/analytics/dashboard
 *
 * Get dashboard overview metrics
 */
pub async fn get_dashboard_metrics(pool: web::Data<PgPool>, req: HttpRequest) -> HttpResponse {
    if get_admin_claims(&req).is_none() {
        return HttpResponse::Unauthorized().json(serde_json::json!({
            "error": "Unauthorized"
        }));
    }

    // Select fields explicitly: the legacy view has an extra pending_bets column.
    let metrics = sqlx::query_as::<
        _,
        (
            i64,
            i64,
            i64,
            i64,
            BigDecimal,
            BigDecimal,
            i64,
            i64,
            i64,
            i64,
        ),
    >(r#"SELECT
        (SELECT COUNT(*) FROM users WHERE is_active = true),
        (SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE),
        (SELECT COUNT(DISTINCT user_id) FROM bets WHERE DATE(created_at) = CURRENT_DATE),
        (SELECT COUNT(*) FROM bets WHERE DATE(created_at) = CURRENT_DATE),
        (SELECT COALESCE(SUM(amount), 0) FROM bets WHERE DATE(created_at) = CURRENT_DATE),
        (SELECT COALESCE(SUM(amount - CASE WHEN status = 'WON' THEN potential_win ELSE 0 END), 0)
         FROM bets WHERE status IN ('WON', 'LOST') AND DATE(settled_at) = CURRENT_DATE),
        (SELECT COUNT(*) FROM events WHERE status = 'LIVE'),
        (SELECT COUNT(*) FROM events WHERE status = 'UPCOMING' AND event_date > CURRENT_TIMESTAMP),
        (SELECT COUNT(*) FROM fraud_alerts WHERE status = 'pending'),
        (SELECT COUNT(*) FROM fraud_alerts WHERE status = 'pending' AND severity IN ('high', 'critical'))
    "#)
    .fetch_one(pool.get_ref())
    .await;

    match metrics {
        Ok(m) => HttpResponse::Ok().json(DashboardMetrics {
            total_users: m.0,
            new_users_today: m.1,
            active_users_today: m.2,
            total_bets_today: m.3,
            bet_volume_today: m.4.to_string().parse().unwrap_or(0.0),
            revenue_today: m.5.to_string().parse().unwrap_or(0.0),
            live_events: m.6,
            upcoming_events: m.7,
            pending_alerts: m.8,
            critical_alerts: m.9,
        }),
        Err(e) => {
            eprintln!("Error fetching dashboard metrics: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to fetch metrics"
            }))
        }
    }
}
