use crate::betting_simple::SimpleBettingService;
use crate::config::AppConfig;
use crate::crypto::CryptoService;
use crate::errors::{AppError, AppResult};
use crate::models::{BetResponse, EventResponse, PlaceBetRequest};
use crate::monitoring::MonitoringService;
use crate::utils::extract_user_id;
use crate::rates::RateLimiters;
use actix_web::{web, HttpRequest, HttpResponse};
use serde::Deserialize;
use sqlx::PgPool;
use std::sync::Arc;
use tracing::info;
use uuid::Uuid;
use validator::Validate;

#[derive(Debug, Deserialize)]
pub struct EventQuery {
    pub sport: Option<String>,
    pub league: Option<String>,  // Filter by league (e.g., "nba_cup", "nba", "nfl")
    pub status: Option<String>,
}

pub async fn get_events(
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
    query: web::Query<EventQuery>,
) -> AppResult<HttpResponse> {
    let crypto_service = Arc::new(CryptoService::from_string(&config.encryption_key));
    let betting_service = SimpleBettingService::new(crypto_service);

    let events = betting_service
        .get_events(pool.as_ref(), query.sport.clone(), query.league.clone(), query.status.clone())
        .await?;

    let event_responses: Vec<EventResponse> = events
        .into_iter()
        .map(|e| EventResponse {
            id: e.id,
            sport: e.sport,
            league: e.league,
            home_team: e.home_team,
            away_team: e.away_team,
            event_date: e.event_date,
            status: e.status,
            home_score: e.home_score,
            away_score: e.away_score,
            moneyline_home: e.moneyline_home,
            moneyline_away: e.moneyline_away,
            point_spread: e.point_spread,
            spread_home_odds: e.spread_home_odds,
            spread_away_odds: e.spread_away_odds,
            total_points: e.total_points,
            over_odds: e.over_odds,
            under_odds: e.under_odds,
        })
        .collect();

    Ok(HttpResponse::Ok().json(event_responses))
}

pub async fn get_event(
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
    event_id: web::Path<Uuid>,
) -> AppResult<HttpResponse> {
    let crypto_service = Arc::new(CryptoService::from_string(&config.encryption_key));
    let betting_service = SimpleBettingService::new(crypto_service);

    let event = betting_service.get_event(pool.as_ref(), *event_id).await?;

    let event_response = EventResponse {
        id: event.id,
        sport: event.sport,
        league: event.league,
        home_team: event.home_team,
        away_team: event.away_team,
        event_date: event.event_date,
        status: event.status,
        home_score: event.home_score,
        away_score: event.away_score,
        moneyline_home: event.moneyline_home,
        moneyline_away: event.moneyline_away,
        point_spread: event.point_spread,
        spread_home_odds: event.spread_home_odds,
        spread_away_odds: event.spread_away_odds,
        total_points: event.total_points,
        over_odds: event.over_odds,
        under_odds: event.under_odds,
    };

    Ok(HttpResponse::Ok().json(event_response))
}

pub async fn place_bet(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
    rate_limiters: web::Data<RateLimiters>,
    monitoring: web::Data<MonitoringService>,
    body: web::Json<PlaceBetRequest>,
) -> AppResult<HttpResponse> {
    // Validate input
    body.validate().map_err(|e| AppError::Validation(e.to_string()))?;

    let user_id = extract_user_id(&req)?;

    // Check bet rate limit
    rate_limiters.check_bet_limit(user_id)?;

    let crypto_service = Arc::new(CryptoService::from_string(&config.encryption_key));
    let betting_service = SimpleBettingService::new(crypto_service);

    let bet = betting_service
        .place_bet(pool.as_ref(), user_id, body.into_inner())
        .await?;

    info!("Bet placed: user_id={}, bet_id={}", user_id, bet.id);

    monitoring.record_bet().await;

    let bet_response = BetResponse {
        id: bet.id,
        event_id: bet.event_id,
        bet_type: bet.bet_type,
        selection: bet.selection,
        odds: bet.odds,
        amount: bet.amount,
        potential_win: bet.potential_win,
        status: bet.status,
        settled_at: bet.settled_at,
        created_at: bet.created_at,
    };

    Ok(HttpResponse::Created().json(bet_response))
}

pub async fn get_user_bets(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
) -> AppResult<HttpResponse> {
    let user_id = extract_user_id(&req)?;

    let crypto_service = Arc::new(CryptoService::from_string(&config.encryption_key));
    let betting_service = SimpleBettingService::new(crypto_service);

    let bets = betting_service
        .get_user_bets(pool.as_ref(), user_id, 50, 0)
        .await?;

    let bet_responses: Vec<BetResponse> = bets
        .into_iter()
        .map(|b| BetResponse {
            id: b.id,
            event_id: b.event_id,
            bet_type: b.bet_type,
            selection: b.selection,
            odds: b.odds,
            amount: b.amount,
            potential_win: b.potential_win,
            status: b.status,
            settled_at: b.settled_at,
            created_at: b.created_at,
        })
        .collect();

    Ok(HttpResponse::Ok().json(bet_responses))
}

pub async fn get_bet(
    req: HttpRequest,
    pool: web::Data<PgPool>,
    config: web::Data<AppConfig>,
    bet_id: web::Path<Uuid>,
) -> AppResult<HttpResponse> {
    let user_id = extract_user_id(&req)?;

    let crypto_service = Arc::new(CryptoService::from_string(&config.encryption_key));
    let betting_service = SimpleBettingService::new(crypto_service);

    let bet = betting_service
        .get_bet_by_id(pool.as_ref(), *bet_id, user_id)
        .await?;

    let bet_response = BetResponse {
        id: bet.id,
        event_id: bet.event_id,
        bet_type: bet.bet_type,
        selection: bet.selection,
        odds: bet.odds,
        amount: bet.amount,
        potential_win: bet.potential_win,
        status: bet.status,
        settled_at: bet.settled_at,
        created_at: bet.created_at,
    };

    Ok(HttpResponse::Ok().json(bet_response))
}
