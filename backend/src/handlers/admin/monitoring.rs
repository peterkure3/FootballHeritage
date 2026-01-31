/**
 * Admin Monitoring API
 * 
 * Fraud alerts, audit logs, and system monitoring
 */

use actix_web::{web, HttpRequest, HttpResponse};
use serde::Serialize;
use sqlx::PgPool;

use crate::middleware::admin_auth::get_admin_claims;

#[derive(Debug, Serialize)]
pub struct FraudAlert {
    pub id: String,
    pub user_id: Option<String>,
    pub alert_type: String,
    pub severity: String,
    pub description: String,
    pub status: String,
    pub created_at: String,
}

#[derive(Debug, Serialize)]
pub struct AdminLog {
    pub id: String,
    pub admin_email: String,
    pub action: String,
    pub target_type: Option<String>,
    pub target_id: Option<String>,
    pub created_at: String,
}

/**
 * GET /api/v1/admin/monitoring/fraud-alerts
 * 
 * Get fraud alerts
 */
pub async fn get_fraud_alerts(
    pool: web::Data<PgPool>,
    req: HttpRequest,
) -> HttpResponse {
    if get_admin_claims(&req).is_none() {
        return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"}));
    }

    let alerts: Result<Vec<_>, sqlx::Error> = sqlx::query!(
        r#"
        SELECT id, user_id, alert_type, severity, description, status, created_at
        FROM fraud_alerts
        WHERE status = 'pending'
        ORDER BY severity DESC, created_at DESC
        LIMIT 50
        "#
    )
    .fetch_all(pool.get_ref())
    .await;

    match alerts {
        Ok(rows) => {
            let alerts: Vec<FraudAlert> = rows
                .into_iter()
                .map(|r| FraudAlert {
                    id: r.id.to_string(),
                    user_id: r.user_id.map(|id: uuid::Uuid| id.to_string()),
                    alert_type: r.alert_type,
                    severity: r.severity,
                    description: r.description,
                    status: r.status.unwrap_or_else(|| "pending".to_string()),
                    created_at: r.created_at.map(|dt: chrono::DateTime<chrono::Utc>| dt.to_rfc3339()).unwrap_or_default(),
                })
                .collect();

            HttpResponse::Ok().json(serde_json::json!({ "alerts": alerts }))
        }
        Err(e) => {
            eprintln!("Error fetching fraud alerts: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to fetch alerts"}))
        }
    }
}

/**
 * GET /api/v1/admin/monitoring/audit-logs
 * 
 * Get admin activity logs
 */
pub async fn get_audit_logs(
    pool: web::Data<PgPool>,
    req: HttpRequest,
) -> HttpResponse {
    if get_admin_claims(&req).is_none() {
        return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"}));
    }

    let logs: Result<Vec<_>, sqlx::Error> = sqlx::query!(
        r#"
        SELECT 
            l.id, l.action, l.target_type, l.target_id, l.created_at,
            u.email as admin_email
        FROM admin_logs l
        JOIN users u ON l.admin_id = u.id
        ORDER BY l.created_at DESC
        LIMIT 100
        "#
    )
    .fetch_all(pool.get_ref())
    .await;

    match logs {
        Ok(rows) => {
            let logs: Vec<AdminLog> = rows
                .into_iter()
                .map(|r| AdminLog {
                    id: r.id.to_string(),
                    admin_email: r.admin_email,
                    action: r.action,
                    target_type: r.target_type,
                    target_id: r.target_id.map(|id: uuid::Uuid| id.to_string()),
                    created_at: r.created_at.map(|dt: chrono::DateTime<chrono::Utc>| dt.to_rfc3339()).unwrap_or_default(),
                })
                .collect();

            HttpResponse::Ok().json(serde_json::json!({ "logs": logs }))
        }
        Err(e) => {
            eprintln!("Error fetching audit logs: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to fetch logs"}))
        }
    }
}
