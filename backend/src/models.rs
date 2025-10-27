#![allow(dead_code)]
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;
use chrono::{DateTime, Utc};
use validator::Validate;
use bigdecimal::BigDecimal;
use std::collections::HashMap;

// User models
#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct User {
    pub id: Uuid,
    pub email: String,
    pub password_hash: String,
    pub first_name: String,
    pub last_name: String,
    pub date_of_birth: chrono::NaiveDate,
    pub phone: Option<String>,
    pub address: Option<String>,
    pub is_verified: bool,
    pub is_active: bool,
    pub role: Option<String>,  // 'user', 'admin', 'superadmin'
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub last_login: Option<DateTime<Utc>>,
    pub login_count: i32,
    pub failed_login_attempts: i32,
    pub locked_until: Option<DateTime<Utc>>,
}

impl User {
    pub fn is_admin(&self) -> bool {
        matches!(self.role.as_deref(), Some("admin") | Some("superadmin"))
    }

    pub fn is_super_admin(&self) -> bool {
        matches!(self.role.as_deref(), Some("superadmin"))
    }
}

#[derive(Debug, Deserialize, Validate)]
pub struct CreateUserRequest {
    #[validate(email)]
    pub email: String,

    #[validate(length(min = 8))]
    pub password: String,

    #[validate(length(min = 1, max = 100))]
    pub first_name: String,

    #[validate(length(min = 1, max = 100))]
    pub last_name: String,

    pub date_of_birth: chrono::NaiveDate,

    #[validate(length(max = 20))]
    pub phone: Option<String>,

    #[validate(length(max = 500))]
    pub address: Option<String>,
}

#[derive(Debug, Deserialize, Validate)]
pub struct RegisterRequest {
    #[validate(email)]
    pub email: String,

    #[validate(length(min = 8))]
    pub password: String,

    pub first_name: String,
    pub last_name: String,
    pub date_of_birth: chrono::NaiveDate,
    pub phone: Option<String>,
    pub address: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub email: String,
    pub password: String,
    pub remember_me: Option<bool>,
}

#[derive(Debug, Serialize)]
pub struct UserResponse {
    pub id: Uuid,
    pub email: String,
    pub first_name: String,
    pub last_name: String,
    pub is_verified: bool,
    pub created_at: DateTime<Utc>,
    pub last_login: Option<DateTime<Utc>>,
    pub login_count: i32,
}

#[derive(Debug, Deserialize, Validate)]
pub struct UpdateUserRequest {
    #[validate(length(max = 100))]
    pub first_name: Option<String>,

    #[validate(length(max = 100))]
    pub last_name: Option<String>,

    #[validate(length(max = 20))]
    pub phone: Option<String>,

    #[validate(length(max = 500))]
    pub address: Option<String>,
}

// Wallet models
#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Wallet {
    pub id: Uuid,
    pub user_id: Uuid,
    pub encrypted_balance: String,
    pub encryption_iv: String,
    pub total_deposits: BigDecimal,
    pub total_withdrawals: BigDecimal,
    pub total_winnings: BigDecimal,
    pub total_losses: BigDecimal,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize)]
pub struct WalletResponse {
    pub balance: BigDecimal,
    pub total_deposits: BigDecimal,
    pub total_withdrawals: BigDecimal,
    pub total_winnings: BigDecimal,
    pub total_losses: BigDecimal,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize, Validate)]
pub struct DepositRequest {
    pub amount: BigDecimal,

    #[validate(length(max = 500))]
    pub description: Option<String>,

    pub payment_method: String,
    pub payment_details: serde_json::Value,
}

#[derive(Debug, Deserialize, Validate)]
pub struct WithdrawalRequest {
    pub amount: BigDecimal,

    #[validate(length(max = 500))]
    pub description: Option<String>,

    pub destination: String,
    pub destination_details: serde_json::Value,
}

// Transaction models
#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Transaction {
    pub id: Uuid,
    pub user_id: Uuid,
    pub wallet_id: Uuid,
    pub transaction_type: String,
    pub amount: BigDecimal,
    pub balance_before: BigDecimal,
    pub balance_after: BigDecimal,
    pub description: Option<String>,
    pub metadata: Option<serde_json::Value>,
    pub created_at: DateTime<Utc>,
    pub is_fraud_flagged: bool,
}

#[derive(Debug, Serialize)]
pub struct TransactionResponse {
    pub id: Uuid,
    pub transaction_type: String,
    pub amount: BigDecimal,
    pub balance_before: BigDecimal,
    pub balance_after: BigDecimal,
    pub description: Option<String>,
    pub created_at: DateTime<Utc>,
    pub is_fraud_flagged: bool,
}

// Event models
#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Event {
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
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Serialize)]
pub struct EventResponse {
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
}

// Bet models
#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct Bet {
    pub id: Uuid,
    pub user_id: Uuid,
    pub event_id: Uuid,
    pub bet_type: String,
    pub selection: String,
    pub odds: BigDecimal,
    pub amount: BigDecimal,
    pub potential_win: BigDecimal,
    pub status: String,
    pub settled_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize, Validate)]
pub struct PlaceBetRequest {
    pub event_id: Uuid,

    #[validate(custom(function = "validate_bet_type"))]
    pub bet_type: String,

    #[validate(custom(function = "validate_selection"))]
    pub selection: String,

    pub odds: BigDecimal,

    pub amount: BigDecimal,
}

#[derive(Debug, Serialize)]
pub struct BetResponse {
    pub id: Uuid,
    pub event_id: Uuid,
    pub bet_type: String,
    pub selection: String,
    pub odds: BigDecimal,
    pub amount: BigDecimal,
    pub potential_win: BigDecimal,
    pub status: String,
    pub settled_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

// Gambling limits models
#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct GamblingLimits {
    pub id: Uuid,
    pub user_id: Uuid,
    pub daily_loss_limit: Option<BigDecimal>,
    pub weekly_loss_limit: Option<BigDecimal>,
    pub monthly_loss_limit: Option<BigDecimal>,
    pub daily_bet_limit: Option<BigDecimal>,
    pub weekly_bet_limit: Option<BigDecimal>,
    pub monthly_bet_limit: Option<BigDecimal>,
    pub max_single_bet: Option<BigDecimal>,
    pub session_time_limit: Option<i32>,
    pub self_exclusion_until: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize, Validate)]
pub struct UpdateLimitsRequest {
    pub daily_loss_limit: Option<BigDecimal>,

    pub weekly_loss_limit: Option<BigDecimal>,

    pub monthly_loss_limit: Option<BigDecimal>,

    pub daily_bet_limit: Option<BigDecimal>,

    pub weekly_bet_limit: Option<BigDecimal>,

    pub monthly_bet_limit: Option<BigDecimal>,

    pub max_single_bet: Option<BigDecimal>,

    #[validate(range(min = 5, max = 1440))]
    pub session_time_limit: Option<i32>,
}

// User activity models
#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct UserActivity {
    pub id: Uuid,
    pub user_id: Uuid,
    pub activity_type: String,
    pub ip_address: Option<String>,
    pub user_agent: Option<String>,
    pub timestamp: DateTime<Utc>,
    pub metadata: Option<serde_json::Value>,
    pub is_suspicious: bool,
}

#[derive(Debug, Serialize)]
pub struct UserActivityResponse {
    pub id: Uuid,
    pub activity_type: String,
    pub ip_address: Option<String>,
    pub timestamp: DateTime<Utc>,
    pub is_suspicious: bool,
}

// JWT Claims
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String, // user id
    pub email: String,
    pub exp: usize,
    pub iat: usize,
    pub iss: String,
    pub aud: String,
    pub session_id: String,
    pub role: String,
}

// API Response wrappers
#[derive(Debug, Serialize)]
pub struct ApiResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub message: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Serialize)]
pub struct PaginatedResponse<T> {
    pub data: Vec<T>,
    pub pagination: PaginationMeta,
    pub success: bool,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Serialize)]
pub struct PaginationMeta {
    pub page: u32,
    pub per_page: u32,
    pub total: u64,
    pub total_pages: u32,
    pub has_next: bool,
    pub has_prev: bool,
}

// Fraud detection models
#[derive(Debug, Serialize, Deserialize, FromRow)]
pub struct BettingPattern {
    pub id: Uuid,
    pub user_id: Uuid,
    pub pattern_type: String,
    pub pattern_data: serde_json::Value,
    pub detected_at: DateTime<Utc>,
    pub is_flagged: bool,
    pub reviewed_by: Option<Uuid>,
    pub review_notes: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct FraudAlert {
    pub user_id: Uuid,
    pub alert_type: String,
    pub risk_score: f64,
    pub details: serde_json::Value,
    pub ip_address: Option<String>,
    pub user_agent: Option<String>,
}

// Health check models
#[derive(Debug, Serialize)]
pub struct HealthCheck {
    pub status: String,
    pub timestamp: DateTime<Utc>,
    pub uptime_seconds: u64,
    pub version: String,
    pub database: DatabaseHealth,
    pub rate_limiters: HashMap<String, RateLimitStatus>,
}

#[derive(Debug, Serialize)]
pub struct DatabaseHealth {
    pub status: String,
    pub connection_pool_size: u32,
    pub active_connections: u32,
    pub idle_connections: u32,
}

#[derive(Debug, Serialize)]
pub struct RateLimitStatus {
    pub status: String,
    pub remaining_requests: u32,
    pub reset_time: DateTime<Utc>,
}

// Validation functions
fn validate_bet_type(bet_type: &str) -> Result<(), validator::ValidationError> {
    match bet_type {
        "MONEYLINE" | "SPREAD" | "TOTAL" => Ok(()),
        _ => Err(validator::ValidationError::new("invalid_bet_type")),
    }
}

fn validate_selection(selection: &str) -> Result<(), validator::ValidationError> {
    match selection {
        "HOME" | "AWAY" | "OVER" | "UNDER" => Ok(()),
        _ => Err(validator::ValidationError::new("invalid_selection")),
    }
}

// Utility impls
impl<T> ApiResponse<T> {
    pub fn success(data: T, message: &str) -> Self {
        Self {
            success: true,
            data: Some(data),
            message: message.to_string(),
            timestamp: Utc::now(),
        }
    }

    pub fn error(message: &str) -> Self {
        Self {
            success: false,
            data: None,
            message: message.to_string(),
            timestamp: Utc::now(),
        }
    }
}

impl UserResponse {
    pub fn from_user(user: User) -> Self {
        Self {
            id: user.id,
            email: user.email,
            first_name: user.first_name,
            last_name: user.last_name,
            is_verified: user.is_verified,
            created_at: user.created_at,
            last_login: user.last_login,
            login_count: user.login_count,
        }
    }
}

impl EventResponse {
    pub fn from_event(event: Event) -> Self {
        Self {
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
        }
    }
}

impl BetResponse {
    pub fn from_bet(bet: Bet) -> Self {
        Self {
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
        }
    }
}

impl TransactionResponse {
    pub fn from_transaction(transaction: Transaction) -> Self {
        Self {
            id: transaction.id,
            transaction_type: transaction.transaction_type,
            amount: transaction.amount,
            balance_before: transaction.balance_before,
            balance_after: transaction.balance_after,
            description: transaction.description,
            created_at: transaction.created_at,
            is_fraud_flagged: transaction.is_fraud_flagged,
        }
    }
}

// ============================================================================
// PARLAY CALCULATOR MODELS
// ============================================================================

/// Individual bet in a parlay
#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct ParlayBet {
    pub event_id: Uuid,
    pub team: String,
    pub odds: f64,
    pub win_prob: Option<f64>, // Optional user override
    pub bet_type: String,
    pub selection: String,
}

/// Request to calculate parlay expected value
#[derive(Debug, Deserialize, Validate)]
pub struct CalculateParlayRequest {
    #[validate(length(min = 2, max = 15, message = "Parlay must have 2-15 legs"))]
    pub bets: Vec<ParlayBet>,
    
    #[validate(range(min = 0.01, message = "Stake must be at least 0.01"))]
    pub stake: f64,
}

/// Response from parlay calculation
#[derive(Debug, Serialize)]
pub struct ParlayCalculationResponse {
    pub combined_odds: f64,
    pub combined_probability: f64,
    pub expected_profit: BigDecimal,
    pub projected_payout: BigDecimal,
    pub break_even_probability: f64,
    pub recommendation: String,
    pub risk_level: String,
    pub expected_value: f64,
    pub kelly_criterion: f64,
}

/// Request to save a parlay
#[derive(Debug, Deserialize, Validate)]
pub struct SaveParlayRequest {
    #[validate(length(max = 100))]
    pub name: Option<String>,
    
    #[validate(length(min = 2, max = 15))]
    pub bets: Vec<ParlayBet>,
    
    #[validate(range(min = 0.01))]
    pub stake: f64,
}

/// Parlay database model
#[derive(Debug, Serialize, FromRow)]
pub struct Parlay {
    pub id: Uuid,
    pub user_id: Uuid,
    pub name: Option<String>,
    pub total_stake: BigDecimal,
    pub combined_odds: BigDecimal,
    pub combined_probability: BigDecimal,
    pub expected_value: BigDecimal,
    pub potential_payout: BigDecimal,
    pub risk_level: String,
    pub status: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

/// Parlay leg database model
#[derive(Debug, Serialize, FromRow)]
pub struct ParlayLeg {
    pub id: Uuid,
    pub parlay_id: Uuid,
    pub event_id: Uuid,
    pub team_name: String,
    pub bet_type: String,
    pub selection: String,
    pub odds: BigDecimal,
    pub win_probability: Option<BigDecimal>,
    pub leg_order: i32,
    pub created_at: DateTime<Utc>,
}

/// Parlay calculation history model
#[derive(Debug, Serialize, FromRow)]
pub struct ParlayCalculation {
    pub id: Uuid,
    pub user_id: Uuid,
    pub num_legs: i32,
    pub total_stake: BigDecimal,
    pub combined_odds: BigDecimal,
    pub combined_probability: BigDecimal,
    pub expected_value: BigDecimal,
    pub expected_profit: BigDecimal,
    pub potential_payout: BigDecimal,
    pub break_even_probability: BigDecimal,
    pub kelly_criterion: Option<BigDecimal>,
    pub risk_level: String,
    pub recommendation: String,
    pub calculation_data: serde_json::Value,
    pub created_at: DateTime<Utc>,
}

/// Response with parlay and its legs
#[derive(Debug, Serialize)]
pub struct ParlayWithLegs {
    #[serde(flatten)]
    pub parlay: Parlay,
    pub legs: Vec<ParlayLeg>,
}
