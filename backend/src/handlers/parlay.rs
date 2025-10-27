use actix_web::{web, HttpRequest, HttpResponse};
use bigdecimal::{BigDecimal, FromPrimitive};
use serde_json;
use sqlx::PgPool;
use tracing::{info, error};
use uuid::Uuid;
use validator::Validate;

use crate::{
    errors::AppError,
    models::{CalculateParlayRequest, Parlay, ParlayCalculation, ParlayLeg, ParlayWithLegs, SaveParlayRequest, Claims, ParlayBet, ParlayCalculationResponse},
    middleware::jwt_auth::get_claims,
};

type AppResult<T> = Result<T, AppError>;

// ============================================================================
// PARLAY CALCULATION LOGIC
// ============================================================================

/// Calculate implied probability from American odds
fn implied_probability(american_odds: f64) -> f64 {
    if american_odds > 0.0 {
        100.0 / (american_odds + 100.0)
    } else {
        american_odds.abs() / (american_odds.abs() + 100.0)
    }
}

/// Assess risk level based on number of legs, probability, and EV
fn assess_risk(num_legs: usize, prob: f64, ev: f64) -> String {
    match (num_legs, prob, ev) {
        (n, _, _) if n >= 6 => "VERY_HIGH",
        (_, p, _) if p < 0.10 => "VERY_HIGH",
        (_, p, e) if p < 0.25 || e < -0.10 => "HIGH",
        (_, p, e) if p < 0.50 || e < 0.0 => "MEDIUM",
        _ => "LOW",
    }.to_string()
}

/// Generate recommendation based on EV, risk, and Kelly Criterion
fn generate_recommendation(ev: f64, risk_level: &str, kelly: f64) -> String {
    if ev < -0.05 {
        format!(
            "❌ NOT RECOMMENDED - Negative expected value ({:.1}%). This bet is likely to lose money over time.",
            ev * 100.0
        )
    } else if ev < 0.0 {
        format!(
            "⚠️ MARGINAL - Slightly negative EV ({:.1}%). Consider skipping this parlay.",
            ev * 100.0
        )
    } else if ev < 0.05 {
        format!(
            "⚡ NEUTRAL - Low positive EV ({:.1}%). Risk level: {}. Proceed with caution.",
            ev * 100.0, risk_level
        )
    } else if ev < 0.15 {
        format!(
            "✅ GOOD VALUE - Positive EV ({:.1}%). Risk level: {}. Kelly suggests {:.1}% of bankroll.",
            ev * 100.0, risk_level, kelly * 100.0
        )
    } else {
        format!(
            "🔥 EXCELLENT VALUE - High EV ({:.1}%). Risk level: {}. Kelly suggests {:.1}% of bankroll. Strong opportunity!",
            ev * 100.0, risk_level, kelly * 100.0
        )
    }
}

/// Core parlay calculation function
fn calculate_parlay_metrics(bets: &[ParlayBet], stake: f64) -> ParlayCalculationResponse {
    // 1. Combined odds = odds1 × odds2 × odds3 × ...
    let combined_odds: f64 = bets.iter().map(|b| b.odds).product();
    
    // 2. Combined probability = prob1 × prob2 × prob3 × ...
    let combined_prob: f64 = bets.iter()
        .map(|b| b.win_prob.unwrap_or_else(|| implied_probability(b.odds)))
        .product();
    
    // 3. Projected payout = stake × combined_odds
    let payout = stake * combined_odds;
    
    // 4. Expected profit = (combined_prob × payout) - stake
    let expected_profit = (combined_prob * payout) - stake;
    
    // 5. Expected value = expected_profit / stake
    let ev = expected_profit / stake;
    
    // 6. Break-even probability = 1 / combined_odds
    let break_even_prob = 1.0 / combined_odds;
    
    // 7. Kelly Criterion = (prob × odds - 1) / (odds - 1)
    // Capped at 25% to prevent over-betting
    let kelly_raw = ((combined_prob * combined_odds) - 1.0) / (combined_odds - 1.0);
    let kelly = kelly_raw.max(0.0).min(0.25);
    
    // 8. Risk assessment
    let risk_level = assess_risk(bets.len(), combined_prob, ev);
    
    // 9. Recommendation
    let recommendation = generate_recommendation(ev, &risk_level, kelly);
    
    ParlayCalculationResponse {
        combined_odds,
        combined_probability: combined_prob,
        expected_profit: BigDecimal::from_f64(expected_profit).unwrap_or_default(),
        projected_payout: BigDecimal::from_f64(payout).unwrap_or_default(),
        break_even_probability: break_even_prob,
        recommendation,
        risk_level,
        expected_value: ev,
        kelly_criterion: kelly,
    }
}

// ============================================================================
// API HANDLERS
// ============================================================================

/// POST /api/v1/parlay/calculate
/// Calculate parlay expected value without saving
pub async fn calculate_parlay(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    body: web::Json<CalculateParlayRequest>,
) -> AppResult<HttpResponse> {
    // Extract user_id from JWT claims
    let claims = get_claims(&req)
        .ok_or_else(|| AppError::Authentication("User not authenticated".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID in token".to_string()))?;

    // Validate request
    body.validate()
        .map_err(|e| AppError::Validation(e.to_string()))?;

    info!("Calculating parlay for user {} with {} legs", user_id, body.bets.len());

    // Validate that all events exist
    for bet in &body.bets {
        let event_exists = sqlx::query_scalar::<_, bool>(
            "SELECT EXISTS(SELECT 1 FROM events WHERE id = $1)"
        )
        .bind(bet.event_id)
        .fetch_one(pool.get_ref())
        .await
        .map_err(|e| {
            error!("Database error checking event: {}", e);
            AppError::Database(e)
        })?;

        if !event_exists {
            return Err(AppError::EventNotFound);
        }
    }

    // Calculate parlay metrics
    let result = calculate_parlay_metrics(&body.bets, body.stake);

    // Save to calculation history (skip if user_id is invalid)
    // TODO: Remove this check once proper JWT extraction is implemented
    let user_exists = sqlx::query_scalar::<_, bool>(
        "SELECT EXISTS(SELECT 1 FROM users WHERE id = $1)"
    )
    .bind(user_id)
    .fetch_one(pool.get_ref())
    .await
    .unwrap_or(false);

    if user_exists {
        let calculation_data = serde_json::to_value(&body.bets)
            .map_err(|e| AppError::Internal(format!("JSON serialization error: {}", e)))?;

        let _ = sqlx::query(
            r#"
            INSERT INTO parlay_calculations (
                user_id, num_legs, total_stake, combined_odds, combined_probability,
                expected_value, expected_profit, potential_payout, break_even_probability,
                kelly_criterion, risk_level, recommendation, calculation_data
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            "#
        )
        .bind(user_id)
        .bind(body.bets.len() as i32)
        .bind(&result.projected_payout)
        .bind(result.combined_odds)
        .bind(result.combined_probability)
        .bind(result.expected_value)
        .bind(&result.expected_profit)
        .bind(&result.projected_payout)
        .bind(result.break_even_probability)
        .bind(result.kelly_criterion)
        .bind(&result.risk_level)
        .bind(&result.recommendation)
        .bind(calculation_data)
        .execute(pool.get_ref())
        .await;
        // Ignore errors in history saving - it's not critical
    }

    info!("Parlay calculation completed: EV={:.2}%, Risk={}", result.expected_value * 100.0, result.risk_level);

    Ok(HttpResponse::Ok().json(result))
}

/// POST /api/v1/parlay/save
/// Save a parlay for later
pub async fn save_parlay(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    body: web::Json<SaveParlayRequest>,
) -> AppResult<HttpResponse> {
    // Extract user_id from JWT claims
    let claims = get_claims(&req)
        .ok_or_else(|| AppError::Authentication("User not authenticated".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID in token".to_string()))?;

    body.validate()
        .map_err(|e| AppError::Validation(e.to_string()))?;

    info!("Saving parlay for user {}", user_id);

    // Calculate metrics
    let metrics = calculate_parlay_metrics(&body.bets, body.stake);

    // Start transaction
    let mut tx = pool.begin().await
        .map_err(|e| AppError::Database(e))?;

    // Insert parlay
    let parlay_id = sqlx::query_scalar::<_, Uuid>(
        r#"
        INSERT INTO parlays (
            user_id, name, total_stake, combined_odds, combined_probability,
            expected_value, potential_payout, risk_level, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'DRAFT')
        RETURNING id
        "#
    )
    .bind(user_id)
    .bind(&body.name)
    .bind(body.stake)
    .bind(metrics.combined_odds)
    .bind(metrics.combined_probability)
    .bind(metrics.expected_value)
    .bind(&metrics.projected_payout)
    .bind(&metrics.risk_level)
    .fetch_one(&mut *tx)
    .await
    .map_err(|e| {
        error!("Failed to insert parlay: {}", e);
        AppError::Database(e)
    })?;

    // Insert parlay legs
    for (index, bet) in body.bets.iter().enumerate() {
        sqlx::query(
            r#"
            INSERT INTO parlay_legs (
                parlay_id, event_id, team_name, bet_type, selection,
                odds, win_probability, leg_order
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            "#
        )
        .bind(parlay_id)
        .bind(bet.event_id)
        .bind(&bet.team)
        .bind(&bet.bet_type)
        .bind(&bet.selection)
        .bind(bet.odds)
        .bind(bet.win_prob)
        .bind(index as i32)
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            error!("Failed to insert parlay leg: {}", e);
            AppError::Database(e)
        })?;
    }

    tx.commit().await
        .map_err(|e| AppError::Database(e))?;

    info!("Parlay saved successfully: {}", parlay_id);

    Ok(HttpResponse::Created().json(serde_json::json!({
        "id": parlay_id,
        "message": "Parlay saved successfully"
    })))
}

/// GET /api/v1/parlay/saved
/// Get user's saved parlays
pub async fn get_saved_parlays(
    req: HttpRequest,
    pool: web::Data<PgPool>,
) -> AppResult<HttpResponse> {
    // Extract user_id from JWT claims
    let claims = get_claims(&req)
        .ok_or_else(|| AppError::Authentication("User not authenticated".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID in token".to_string()))?;

    info!("Fetching saved parlays for user {}", user_id);

    let parlays = sqlx::query_as::<_, Parlay>(
        "SELECT * FROM parlays WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50"
    )
    .bind(user_id)
    .fetch_all(pool.get_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch parlays: {}", e);
        AppError::Database(e)
    })?;

    Ok(HttpResponse::Ok().json(parlays))
}

/// GET /api/v1/parlay/{id}
/// Get a specific parlay with its legs
pub async fn get_parlay(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    parlay_id: web::Path<Uuid>,
) -> AppResult<HttpResponse> {
    // Extract user_id from JWT claims
    let claims = get_claims(&req)
        .ok_or_else(|| AppError::Authentication("User not authenticated".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID in token".to_string()))?;

    let parlay_id = parlay_id.into_inner();
    
    info!("Fetching parlay {} for user {}", parlay_id, user_id);

    // Fetch parlay
    let parlay = sqlx::query_as::<_, Parlay>(
        "SELECT * FROM parlays WHERE id = $1 AND user_id = $2"
    )
    .bind(parlay_id)
    .bind(user_id)
    .fetch_optional(pool.get_ref())
    .await
    .map_err(|e| AppError::Database(e))?
    .ok_or_else(|| AppError::UserNotFound)?;

    // Fetch legs
    let legs = sqlx::query_as::<_, ParlayLeg>(
        "SELECT * FROM parlay_legs WHERE parlay_id = $1 ORDER BY leg_order"
    )
    .bind(parlay_id)
    .fetch_all(pool.get_ref())
    .await
    .map_err(|e| AppError::Database(e))?;

    Ok(HttpResponse::Ok().json(ParlayWithLegs { parlay, legs }))
}

/// GET /api/v1/parlay/history
/// Get calculation history
pub async fn get_calculation_history(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> AppResult<HttpResponse> {
    // Extract user_id from JWT claims
    let claims = get_claims(&req)
        .ok_or_else(|| AppError::Authentication("User not authenticated".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID in token".to_string()))?;
    let limit: i64 = query.get("limit")
        .and_then(|s| s.parse().ok())
        .unwrap_or(20)
        .min(100);

    info!("Fetching calculation history for user {}", user_id);

    let calculations = sqlx::query_as::<_, ParlayCalculation>(
        "SELECT * FROM parlay_calculations WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2"
    )
    .bind(user_id)
    .bind(limit)
    .fetch_all(pool.get_ref())
    .await
    .map_err(|e| {
        error!("Failed to fetch calculation history: {}", e);
        AppError::Database(e)
    })?;

    Ok(HttpResponse::Ok().json(calculations))
}

/// DELETE /api/v1/parlay/{id}
/// Delete a saved parlay
pub async fn delete_parlay(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    parlay_id: web::Path<Uuid>,
) -> AppResult<HttpResponse> {
    // Extract user_id from JWT claims
    let claims = get_claims(&req)
        .ok_or_else(|| AppError::Authentication("User not authenticated".to_string()))?;
    
    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AppError::Authentication("Invalid user ID in token".to_string()))?;

    let parlay_id = parlay_id.into_inner();
    
    info!("Deleting parlay {} for user {}", parlay_id, user_id);

    let result = sqlx::query(
        "DELETE FROM parlays WHERE id = $1 AND user_id = $2"
    )
    .bind(parlay_id)
    .bind(user_id)
    .execute(pool.get_ref())
    .await
    .map_err(|e| AppError::Database(e))?;

    if result.rows_affected() == 0 {
        return Err(AppError::UserNotFound);
    }

    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "Parlay deleted successfully"
    })))
}
