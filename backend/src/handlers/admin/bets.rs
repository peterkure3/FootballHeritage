/**
 * Admin Bet Management API
 * 
 * View, update, and manage user bets
 */

use actix_web::{web, HttpRequest, HttpResponse};
use serde::{Deserialize, Serialize};
use sqlx::PgPool;
use uuid::Uuid;

use crate::middleware::admin_auth::get_admin_claims;

#[derive(Debug, Serialize)]
pub struct BetListItem {
    pub id: Uuid,
    pub user_id: Uuid,
    pub user_email: String,
    pub event_id: Uuid,
    pub event_name: String,
    pub sport: String,
    pub bet_type: String,
    pub selection: String,
    pub odds: String,
    pub stake: String,
    pub potential_win: String,
    pub status: String,
    pub placed_at: String,
}

/**
 * GET /api/v1/admin/bets
 * 
 * Get all bets with pagination and filtering
 */
pub async fn get_all_bets(
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
    let status = query.get("status").and_then(|v| v.as_str());
    let sport = query.get("sport").and_then(|v| v.as_str());
    let user_id = query.get("user_id").and_then(|v| v.as_str()).and_then(|s| Uuid::parse_str(s).ok());

    let bets = if let Some(status_val) = status {
        if let Some(sport_val) = sport {
            sqlx::query_as!(
                BetListItem,
                r#"
                SELECT 
                    b.id, b.user_id, u.email as user_email,
                    b.event_id, 
                    CONCAT(e.home_team, ' vs ', e.away_team) as event_name,
                    e.sport, b.bet_type, b.selection,
                    b.odds::text as odds, b.stake::text as stake,
                    b.potential_win::text as potential_win,
                    b.status, b.created_at::text as placed_at
                FROM bets b
                JOIN users u ON b.user_id = u.id
                JOIN events e ON b.event_id = e.id
                WHERE b.status = $1 AND e.sport = $2
                ORDER BY b.created_at DESC
                LIMIT $3 OFFSET $4
                "#,
                status_val, sport_val, limit, offset
            )
            .fetch_all(pool.get_ref())
            .await
        } else {
            sqlx::query_as!(
                BetListItem,
                r#"
                SELECT 
                    b.id, b.user_id, u.email as user_email,
                    b.event_id,
                    CONCAT(e.home_team, ' vs ', e.away_team) as event_name,
                    e.sport, b.bet_type, b.selection,
                    b.odds::text as odds, b.stake::text as stake,
                    b.potential_win::text as potential_win,
                    b.status, b.created_at::text as placed_at
                FROM bets b
                JOIN users u ON b.user_id = u.id
                JOIN events e ON b.event_id = e.id
                WHERE b.status = $1
                ORDER BY b.created_at DESC
                LIMIT $2 OFFSET $3
                "#,
                status_val, limit, offset
            )
            .fetch_all(pool.get_ref())
            .await
        }
    } else if let Some(user_id_val) = user_id {
        sqlx::query_as!(
            BetListItem,
            r#"
            SELECT 
                b.id, b.user_id, u.email as user_email,
                b.event_id,
                CONCAT(e.home_team, ' vs ', e.away_team) as event_name,
                e.sport, b.bet_type, b.selection,
                b.odds::text as odds, b.stake::text as stake,
                b.potential_win::text as potential_win,
                b.status, b.created_at::text as placed_at
            FROM bets b
            JOIN users u ON b.user_id = u.id
            JOIN events e ON b.event_id = e.id
            WHERE b.user_id = $1
            ORDER BY b.created_at DESC
            LIMIT $2 OFFSET $3
            "#,
            user_id_val, limit, offset
        )
        .fetch_all(pool.get_ref())
        .await
    } else {
        sqlx::query_as!(
            BetListItem,
            r#"
            SELECT 
                b.id, b.user_id, u.email as user_email,
                b.event_id,
                CONCAT(e.home_team, ' vs ', e.away_team) as event_name,
                e.sport, b.bet_type, b.selection,
                b.odds::text as odds, b.stake::text as stake,
                b.potential_win::text as potential_win,
                b.status, b.created_at::text as placed_at
            FROM bets b
            JOIN users u ON b.user_id = u.id
            JOIN events e ON b.event_id = e.id
            ORDER BY b.created_at DESC
            LIMIT $1 OFFSET $2
            "#,
            limit, offset
        )
        .fetch_all(pool.get_ref())
        .await
    };

    match bets {
        Ok(data) => HttpResponse::Ok().json(serde_json::json!({
            "bets": data,
            "count": data.len()
        })),
        Err(e) => {
            eprintln!("Error fetching bets: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to fetch bets"}))
        }
    }
}

/**
 * GET /api/v1/admin/bets/:id
 * 
 * Get single bet by ID
 */
pub async fn get_bet(
    pool: web::Data<PgPool>,
    bet_id: web::Path<Uuid>,
    req: HttpRequest,
) -> HttpResponse {
    let _admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let result = sqlx::query!(
        r#"
        SELECT 
            b.*, u.email as user_email, u.username,
            e.sport, e.league, e.home_team, e.away_team, e.event_date, e.status as event_status
        FROM bets b
        JOIN users u ON b.user_id = u.id
        JOIN events e ON b.event_id = e.id
        WHERE b.id = $1
        "#,
        bet_id.into_inner()
    )
    .fetch_one(pool.get_ref())
    .await;

    match result {
        Ok(bet) => HttpResponse::Ok().json(bet),
        Err(e) => {
            eprintln!("Error fetching bet: {}", e);
            HttpResponse::NotFound().json(serde_json::json!({"error": "Bet not found"}))
        }
    }
}

/**
 * PUT /api/v1/admin/bets/:id/settle
 * 
 * Settle a bet (mark as won or lost)
 */
#[derive(Debug, Deserialize)]
pub struct SettleBetRequest {
    pub status: String,  // "WON" or "LOST"
}

pub async fn settle_bet(
    pool: web::Data<PgPool>,
    bet_id: web::Path<Uuid>,
    body: web::Json<SettleBetRequest>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let admin_id: Uuid = admin_claims.sub.parse().unwrap();
    let bet_id = bet_id.into_inner();

    // Validate status
    if body.status != "WON" && body.status != "LOST" {
        return HttpResponse::BadRequest().json(serde_json::json!({
            "error": "Invalid status. Must be 'WON' or 'LOST'"
        }));
    }

    // Get bet details
    let bet = sqlx::query!(
        "SELECT user_id, stake, potential_win, status FROM bets WHERE id = $1",
        bet_id
    )
    .fetch_one(pool.get_ref())
    .await;

    let bet = match bet {
        Ok(b) => b,
        Err(_) => return HttpResponse::NotFound().json(serde_json::json!({"error": "Bet not found"})),
    };

    if bet.status != "PENDING" {
        return HttpResponse::BadRequest().json(serde_json::json!({
            "error": "Can only settle pending bets"
        }));
    }

    // Start transaction
    let mut tx = match pool.begin().await {
        Ok(tx) => tx,
        Err(e) => {
            eprintln!("Error starting transaction: {}", e);
            return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to settle bet"}));
        }
    };

    // Update bet status
    let update_result = sqlx::query!(
        "UPDATE bets SET status = $1, settled_at = NOW(), settled_by = $2 WHERE id = $3",
        body.status,
        admin_id,
        bet_id
    )
    .execute(&mut *tx)
    .await;

    if update_result.is_err() {
        let _ = tx.rollback().await;
        return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to update bet"}));
    }

    // If bet won, credit user's wallet
    if body.status == "WON" {
        let credit_result = sqlx::query!(
            "UPDATE users SET balance = balance + $1 WHERE id = $2",
            bet.potential_win.unwrap(),
            bet.user_id
        )
        .execute(&mut *tx)
        .await;

        if credit_result.is_err() {
            let _ = tx.rollback().await;
            return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to credit winnings"}));
        }

        // Record transaction
        let _ = sqlx::query!(
            r#"
            INSERT INTO transactions (user_id, transaction_type, amount, status, reference)
            VALUES ($1, 'BET_WIN', $2, 'COMPLETED', $3)
            "#,
            bet.user_id,
            bet.potential_win.unwrap(),
            format!("Bet #{} winnings", bet_id)
        )
        .execute(&mut *tx)
        .await;
    }

    // Log admin action
    let _ = sqlx::query!(
        "INSERT INTO admin_logs (admin_id, action, target_type, target_id, details) VALUES ($1, 'settle_bet', 'bet', $2, $3)",
        admin_id,
        bet_id,
        serde_json::json!({"status": body.status}).to_string()
    )
    .execute(&mut *tx)
    .await;

    // Commit transaction
    if tx.commit().await.is_err() {
        return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to commit transaction"}));
    }

    HttpResponse::Ok().json(serde_json::json!({
        "success": true,
        "message": format!("Bet settled as {}", body.status)
    }))
}

/**
 * PUT /api/v1/admin/bets/:id/void
 * 
 * Void a bet and refund the stake
 */
pub async fn void_bet(
    pool: web::Data<PgPool>,
    bet_id: web::Path<Uuid>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let admin_id: Uuid = admin_claims.sub.parse().unwrap();
    let bet_id = bet_id.into_inner();

    // Get bet details
    let bet = sqlx::query!(
        "SELECT user_id, stake, status FROM bets WHERE id = $1",
        bet_id
    )
    .fetch_one(pool.get_ref())
    .await;

    let bet = match bet {
        Ok(b) => b,
        Err(_) => return HttpResponse::NotFound().json(serde_json::json!({"error": "Bet not found"})),
    };

    if bet.status != "PENDING" {
        return HttpResponse::BadRequest().json(serde_json::json!({
            "error": "Can only void pending bets"
        }));
    }

    // Start transaction
    let mut tx = match pool.begin().await {
        Ok(tx) => tx,
        Err(e) => {
            eprintln!("Error starting transaction: {}", e);
            return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to void bet"}));
        }
    };

    // Update bet status
    let update_result = sqlx::query!(
        "UPDATE bets SET status = 'VOID', settled_at = NOW(), settled_by = $1 WHERE id = $2",
        admin_id,
        bet_id
    )
    .execute(&mut *tx)
    .await;

    if update_result.is_err() {
        let _ = tx.rollback().await;
        return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to void bet"}));
    }

    // Refund stake to user's wallet
    let refund_result = sqlx::query!(
        "UPDATE users SET balance = balance + $1 WHERE id = $2",
        bet.stake.unwrap(),
        bet.user_id
    )
    .execute(&mut *tx)
    .await;

    if refund_result.is_err() {
        let _ = tx.rollback().await;
        return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to refund stake"}));
    }

    // Record transaction
    let _ = sqlx::query!(
        r#"
        INSERT INTO transactions (user_id, transaction_type, amount, status, reference)
        VALUES ($1, 'BET_REFUND', $2, 'COMPLETED', $3)
        "#,
        bet.user_id,
        bet.stake.unwrap(),
        format!("Bet #{} voided - refund", bet_id)
    )
    .execute(&mut *tx)
    .await;

    // Log admin action
    let _ = sqlx::query!(
        "INSERT INTO admin_logs (admin_id, action, target_type, target_id) VALUES ($1, 'void_bet', 'bet', $2)",
        admin_id,
        bet_id
    )
    .execute(&mut *tx)
    .await;

    // Commit transaction
    if tx.commit().await.is_err() {
        return HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to commit transaction"}));
    }

    HttpResponse::Ok().json(serde_json::json!({
        "success": true,
        "message": "Bet voided and stake refunded"
    }))
}

/**
 * DELETE /api/v1/admin/bets/:id
 * 
 * Delete a bet (only if not settled)
 */
pub async fn delete_bet(
    pool: web::Data<PgPool>,
    bet_id: web::Path<Uuid>,
    req: HttpRequest,
) -> HttpResponse {
    let admin_claims = match get_admin_claims(&req) {
        Some(claims) => claims,
        None => return HttpResponse::Unauthorized().json(serde_json::json!({"error": "Unauthorized"})),
    };

    let admin_id: Uuid = admin_claims.sub.parse().unwrap();
    let bet_id = bet_id.into_inner();

    // Check bet status
    let bet = sqlx::query!(
        "SELECT status FROM bets WHERE id = $1",
        bet_id
    )
    .fetch_one(pool.get_ref())
    .await;

    match bet {
        Ok(b) => {
            let status = b.status.as_deref().unwrap_or("");
            if status != "PENDING" && status != "VOID" {
                return HttpResponse::BadRequest().json(serde_json::json!({
                    "error": "Cannot delete settled bets"
                }));
            }
        }
        Err(_) => return HttpResponse::NotFound().json(serde_json::json!({"error": "Bet not found"})),
    }

    let result = sqlx::query!("DELETE FROM bets WHERE id = $1", bet_id)
        .execute(pool.get_ref())
        .await;

    match result {
        Ok(_) => {
            // Log admin action
            let _ = sqlx::query!(
                "INSERT INTO admin_logs (admin_id, action, target_type, target_id) VALUES ($1, 'delete_bet', 'bet', $2)",
                admin_id,
                bet_id
            )
            .execute(pool.get_ref())
            .await;

            HttpResponse::Ok().json(serde_json::json!({"success": true, "message": "Bet deleted"}))
        }
        Err(e) => {
            eprintln!("Error deleting bet: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({"error": "Failed to delete bet"}))
        }
    }
}
