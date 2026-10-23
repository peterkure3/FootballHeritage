/**
 * Admin User Management API
 *
 * Endpoints for admins to manage users:
 * - List users with pagination and filters
 * - View user details
 * - Suspend/activate users
 * - Verify users
 * - Update user limits
 * - Delete users (superadmin only)
 */
use actix_web::{web, HttpRequest, HttpResponse};
use bigdecimal::BigDecimal;
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use uuid::Uuid;

use crate::middleware::admin_auth::get_admin_claims;

// ============================================================================
// REQUEST/RESPONSE TYPES
// ============================================================================

#[derive(Debug, Deserialize)]
pub struct ListUsersQuery {
    pub page: Option<i64>,
    pub limit: Option<i64>,
    pub status: Option<String>, // active, suspended, locked
    pub role: Option<String>,   // user, admin, superadmin
    pub verified: Option<bool>,
    pub search: Option<String>,     // Search by email or name
    pub sort_by: Option<String>,    // created_at, last_login, total_bets
    pub sort_order: Option<String>, // asc, desc
}

#[derive(Debug, Serialize)]
pub struct UserListItem {
    pub id: Uuid,
    pub email: String,
    pub first_name: String,
    pub last_name: String,
    pub role: String,
    pub is_verified: bool,
    pub is_active: bool,
    pub created_at: String,
    pub last_login: Option<String>,
    pub login_count: i32,
    pub total_bets: i64,
    pub total_bet_amount: f64,
}

#[derive(Debug, Serialize)]
pub struct UsersListResponse {
    pub users: Vec<UserListItem>,
    pub total: i64,
    pub page: i64,
    pub limit: i64,
    pub total_pages: i64,
}

#[derive(Debug, Serialize)]
pub struct UserDetailsResponse {
    pub id: Uuid,
    pub email: String,
    pub first_name: String,
    pub last_name: String,
    pub date_of_birth: String,
    pub phone: Option<String>,
    pub address: Option<String>,
    pub role: String,
    pub is_verified: bool,
    pub is_active: bool,
    pub created_at: String,
    pub updated_at: String,
    pub last_login: Option<String>,
    pub login_count: i32,
    pub failed_login_attempts: i32,
    pub locked_until: Option<String>,
    pub wallet_balance: f64,
    pub total_deposits: f64,
    pub total_withdrawals: f64,
    pub total_bets: i64,
    pub total_bet_amount: f64,
    pub total_winnings: f64,
    pub total_losses: f64,
    pub win_rate: f64,
}

#[derive(Debug, Deserialize)]
pub struct UpdateUserStatusRequest {
    pub is_active: bool,
    pub reason: Option<String>,
}

// ============================================================================
// HANDLERS
// ============================================================================

/**
 * GET /api/v1/admin/users
 *
 * List all users with pagination and filters
 * Requires: admin or superadmin role
 */
pub async fn list_users(
    pool: web::Data<PgPool>,
    query: web::Query<ListUsersQuery>,
    req: HttpRequest,
) -> HttpResponse {
    // Get admin claims (already verified by middleware)
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => {
            return HttpResponse::Unauthorized().json(serde_json::json!({
                "error": "Unauthorized"
            }));
        }
    };

    let page = query.page.unwrap_or(1).max(1);
    let limit = query.limit.unwrap_or(20).clamp(1, 100);
    let offset = (page - 1).saturating_mul(limit);

    // Build dynamic query
    let mut sql = String::from(
        r#"
        SELECT 
            u.id,
            u.email,
            u.first_name,
            u.last_name,
            u.role,
            u.is_verified,
            u.is_active,
            u.created_at,
            u.last_login,
            u.login_count,
            COUNT(b.id) as total_bets,
            COALESCE(SUM(b.amount), 0) as total_bet_amount
        FROM users u
        LEFT JOIN bets b ON u.id = b.user_id
        WHERE 1=1
        "#,
    );

    let filters = r#"
        AND ($1::text IS NULL OR CASE $1
            WHEN 'active' THEN u.is_active = true AND (u.locked_until IS NULL OR u.locked_until <= NOW())
            WHEN 'suspended' THEN u.is_active = false
            WHEN 'locked' THEN u.locked_until > NOW()
            ELSE true END)
        AND ($2::text IS NULL OR u.role = $2)
        AND ($3::boolean IS NULL OR u.is_verified = $3)
        AND ($4::text IS NULL OR u.email ILIKE $4 OR u.first_name ILIKE $4 OR u.last_name ILIKE $4)
    "#;
    let role = query.role.as_deref().filter(|value| !value.is_empty());
    let search = query
        .search
        .as_ref()
        .filter(|value| !value.is_empty())
        .map(|value| format!("%{}%", value));
    sql.push_str(filters);

    sql.push_str(" GROUP BY u.id");

    // Add sorting
    let sort_by = match query.sort_by.as_deref() {
        Some("last_login") => "u.last_login",
        Some("total_bets") => "total_bets",
        _ => "u.created_at",
    };
    let sort_order = if query.sort_order.as_deref() == Some("asc") {
        "ASC"
    } else {
        "DESC"
    };
    sql.push_str(&format!(" ORDER BY {} {}", sort_by, sort_order));

    // Add pagination
    sql.push_str(" LIMIT $5 OFFSET $6");

    // Execute query
    let users_result = sqlx::query_as::<
        _,
        (
            Uuid,
            String,
            String,
            String,
            String,
            bool,
            bool,
            chrono::DateTime<chrono::Utc>,
            Option<chrono::DateTime<chrono::Utc>>,
            i32,
            i64,
            BigDecimal,
        ),
    >(&sql)
    .bind(query.status.as_deref())
    .bind(role)
    .bind(query.verified)
    .bind(&search)
    .bind(limit)
    .bind(offset)
    .fetch_all(pool.get_ref())
    .await;

    let users = match users_result {
        Ok(rows) => rows
            .into_iter()
            .map(|row| UserListItem {
                id: row.0,
                email: row.1,
                first_name: row.2,
                last_name: row.3,
                role: row.4,
                is_verified: row.5,
                is_active: row.6,
                created_at: row.7.to_rfc3339(),
                last_login: row.8.map(|dt| dt.to_rfc3339()),
                login_count: row.9,
                total_bets: row.10,
                total_bet_amount: row.11.to_string().parse().unwrap_or(0.0),
            })
            .collect(),
        Err(e) => {
            eprintln!("Error fetching users: {}", e);
            return HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to fetch users"
            }));
        }
    };

    // Get total count
    let count_sql = format!("SELECT COUNT(*) FROM users u WHERE 1=1 {}", filters);
    let count_result = sqlx::query_scalar::<_, i64>(&count_sql)
        .bind(query.status.as_deref())
        .bind(role)
        .bind(query.verified)
        .bind(&search)
        .fetch_one(pool.get_ref())
        .await;

    let total = match count_result {
        Ok(total) => total,
        Err(error) => {
            eprintln!("Error counting users: {}", error);
            return HttpResponse::InternalServerError()
                .json(serde_json::json!({"error": "Failed to count users"}));
        }
    };
    let total_pages = (total as f64 / limit as f64).ceil() as i64;

    // Log admin action
    log_admin_action(
        pool.get_ref(),
        admin_claims.sub.parse().unwrap(),
        "list_users",
        None,
        None,
        None,
    )
    .await;

    HttpResponse::Ok().json(UsersListResponse {
        users,
        total,
        page,
        limit,
        total_pages,
    })
}

/**
 * GET /api/v1/admin/users/:id
 *
 * Get detailed information about a specific user
 * Requires: admin or superadmin role
 */
pub async fn get_user_details(
    pool: web::Data<PgPool>,
    user_id: web::Path<Uuid>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => {
            return HttpResponse::Unauthorized().json(serde_json::json!({
                "error": "Unauthorized"
            }));
        }
    };

    let user_id = user_id.into_inner();

    // Fetch user details with wallet and betting stats
    let user_result = sqlx::query!(
        r#"
        SELECT 
            u.id, u.email, u.first_name, u.last_name, u.date_of_birth,
            u.phone, u.address, u.role, u.is_verified, u.is_active,
            u.created_at, u.updated_at, u.last_login, u.login_count,
            u.failed_login_attempts, u.locked_until,
            w.total_deposits, w.total_withdrawals, w.total_winnings, w.total_losses,
            COUNT(b.id) as "total_bets!",
            COALESCE(SUM(b.amount), 0) as "total_bet_amount!"
        FROM users u
        LEFT JOIN wallets w ON u.id = w.user_id
        LEFT JOIN bets b ON u.id = b.user_id
        WHERE u.id = $1
        GROUP BY u.id, w.total_deposits, w.total_withdrawals, w.total_winnings, w.total_losses
        "#,
        user_id
    )
    .fetch_one(pool.get_ref())
    .await;

    let user = match user_result {
        Ok(user) => user,
        Err(e) => {
            eprintln!("Error fetching user: {}", e);
            return HttpResponse::NotFound().json(serde_json::json!({
                "error": "User not found"
            }));
        }
    };

    // Get wallet balance (would need decryption in real implementation)
    let wallet_balance = 0.0; // Placeholder - implement decryption

    let total_bets = user.total_bets;
    let wins = sqlx::query_scalar::<_, i64>(
        "SELECT COUNT(*) FROM bets WHERE user_id = $1 AND status = 'WON'",
    )
    .bind(user_id)
    .fetch_one(pool.get_ref())
    .await
    .unwrap_or(0);

    let win_rate = if total_bets > 0 {
        (wins as f64 / total_bets as f64) * 100.0
    } else {
        0.0
    };

    // Log admin action
    log_admin_action(
        pool.get_ref(),
        admin_claims.sub.parse().unwrap(),
        "view_user_details",
        Some("user"),
        Some(user_id),
        None,
    )
    .await;

    HttpResponse::Ok().json(UserDetailsResponse {
        id: user.id,
        email: user.email,
        first_name: user.first_name,
        last_name: user.last_name,
        date_of_birth: user.date_of_birth.to_string(),
        phone: user.phone,
        address: user.address,
        role: user.role.unwrap_or_else(|| "user".to_string()),
        is_verified: user.is_verified.unwrap_or(false),
        is_active: user.is_active.unwrap_or(false),
        created_at: user
            .created_at
            .map(|dt: chrono::DateTime<chrono::Utc>| dt.to_rfc3339())
            .unwrap_or_default(),
        updated_at: user
            .updated_at
            .map(|dt: chrono::DateTime<chrono::Utc>| dt.to_rfc3339())
            .unwrap_or_default(),
        last_login: user
            .last_login
            .map(|dt: chrono::DateTime<chrono::Utc>| dt.to_rfc3339()),
        login_count: user.login_count.unwrap_or(0),
        failed_login_attempts: user.failed_login_attempts.unwrap_or(0),
        locked_until: user
            .locked_until
            .map(|dt: chrono::DateTime<chrono::Utc>| dt.to_rfc3339()),
        wallet_balance,
        total_deposits: user
            .total_deposits
            .map(|d: sqlx::types::BigDecimal| d.to_string().parse::<f64>().unwrap_or(0.0))
            .unwrap_or(0.0),
        total_withdrawals: user
            .total_withdrawals
            .map(|d: sqlx::types::BigDecimal| d.to_string().parse::<f64>().unwrap_or(0.0))
            .unwrap_or(0.0),
        total_bets,
        total_bet_amount: user.total_bet_amount.to_string().parse().unwrap_or(0.0),
        total_winnings: user
            .total_winnings
            .map(|d: sqlx::types::BigDecimal| d.to_string().parse::<f64>().unwrap_or(0.0))
            .unwrap_or(0.0),
        total_losses: user
            .total_losses
            .map(|d: sqlx::types::BigDecimal| d.to_string().parse::<f64>().unwrap_or(0.0))
            .unwrap_or(0.0),
        win_rate,
    })
}

/**
 * PUT /api/v1/admin/users/:id/status
 *
 * Suspend or activate a user account
 * Requires: admin or superadmin role
 */
pub async fn update_user_status(
    pool: web::Data<PgPool>,
    user_id: web::Path<Uuid>,
    body: web::Json<UpdateUserStatusRequest>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => {
            return HttpResponse::Unauthorized().json(serde_json::json!({
                "error": "Unauthorized"
            }));
        }
    };

    let user_id = user_id.into_inner();

    // Update user status
    let result = sqlx::query!(
        "UPDATE users SET is_active = $1, updated_at = NOW() WHERE id = $2",
        body.is_active,
        user_id
    )
    .execute(pool.get_ref())
    .await;

    match result {
        Ok(_) => {
            // Log admin action
            let action = if body.is_active {
                "activate_user"
            } else {
                "suspend_user"
            };

            log_admin_action(
                pool.get_ref(),
                admin_claims.sub.parse().unwrap(),
                action,
                Some("user"),
                Some(user_id),
                Some(serde_json::json!({
                    "reason": body.reason
                })),
            )
            .await;

            HttpResponse::Ok().json(serde_json::json!({
                "success": true,
                "message": format!("User {} successfully", if body.is_active { "activated" } else { "suspended" })
            }))
        }
        Err(e) => {
            eprintln!("Error updating user status: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to update user status"
            }))
        }
    }
}

/**
 * PUT /api/v1/admin/users/:id/verify
 *
 * Verify a user account
 * Requires: admin or superadmin role
 */
pub async fn verify_user(
    pool: web::Data<PgPool>,
    user_id: web::Path<Uuid>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => {
            return HttpResponse::Unauthorized().json(serde_json::json!({
                "error": "Unauthorized"
            }));
        }
    };

    let user_id = user_id.into_inner();

    let result = sqlx::query!(
        "UPDATE users SET is_verified = true, updated_at = NOW() WHERE id = $1",
        user_id
    )
    .execute(pool.get_ref())
    .await;

    match result {
        Ok(_) => {
            log_admin_action(
                pool.get_ref(),
                admin_claims.sub.parse().unwrap(),
                "verify_user",
                Some("user"),
                Some(user_id),
                None,
            )
            .await;

            HttpResponse::Ok().json(serde_json::json!({
                "success": true,
                "message": "User verified successfully"
            }))
        }
        Err(e) => {
            eprintln!("Error verifying user: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to verify user"
            }))
        }
    }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

async fn log_admin_action(
    pool: &PgPool,
    admin_id: Uuid,
    action: &str,
    target_type: Option<&str>,
    target_id: Option<Uuid>,
    _details: Option<serde_json::Value>,
) {
    let _ = sqlx::query!(
        r#"
        INSERT INTO admin_logs (admin_id, action, target_type, target_id)
        VALUES ($1, $2, $3, $4)
        "#,
        admin_id,
        action,
        target_type,
        target_id
    )
    .execute(pool)
    .await;
}
