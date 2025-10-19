#![allow(dead_code)]

use crate::config::AppConfig;
use crate::crypto::CryptoService;
use crate::errors::{AppError, AppResult};
use crate::models::{Bet, Event, PlaceBetRequest};
use bigdecimal::BigDecimal;
use chrono::{DateTime, Utc};
use sqlx::PgPool;
use std::str::FromStr;
use std::sync::Arc;
use tracing::{error, info, warn};
use uuid::Uuid;

/// Betting service for managing bets and events
pub struct BettingService {
    config: Arc<AppConfig>,
    crypto_service: Arc<CryptoService>,
}

impl BettingService {
    pub fn new(config: Arc<AppConfig>, crypto_service: Arc<CryptoService>) -> Self {
        Self {
            config,
            crypto_service,
        }
    }

    /// Place a new bet
    pub async fn place_bet(
        &self,
        pool: &PgPool,
        user_id: Uuid,
        bet_request: PlaceBetRequest,
    ) -> AppResult<Bet> {
        // Start transaction
        let mut tx = pool.begin().await.map_err(|e| {
            error!("Failed to start transaction: {}", e);
            AppError::Database(e)
        })?;

        // Verify event exists and is available for betting
        let event = self.get_event_by_id(&mut *tx, bet_request.event_id).await?;

        if event.status != "scheduled" {
            return Err(AppError::EventNotAvailable);
        }

        // Check if event has already started
        if event.event_date <= Utc::now() {
            return Err(AppError::EventNotAvailable);
        }

        // Validate bet amount
        if bet_request.amount < BigDecimal::from_str("1.00").unwrap() {
            return Err(AppError::InvalidBetAmount);
        }

        // Check user's wallet balance
        let wallet = self.get_user_wallet(&mut *tx, user_id).await?;
        let encrypted_balance = wallet.encrypted_balance;
        let iv = wallet.encryption_iv;
        let balance = self.crypto_service.decrypt_balance(&encrypted_balance, &iv)?
            .to_string()
            .parse::<BigDecimal>()
            .map_err(|e| AppError::Internal(format!("Failed to parse balance: {}", e)))?;

        if balance < bet_request.amount {
            return Err(AppError::InsufficientFunds);
        }

        // Check responsible gambling limits
        self.check_betting_limits(&mut *tx, user_id, &bet_request.amount).await?;

        // Verify odds match current odds (prevent stale odds)
        let current_odds = self.get_current_odds(&event, &bet_request.bet_type, &bet_request.selection)?;

        // Allow small variance (0.05) for odds changes
        let odds_diff = (&bet_request.odds - &current_odds).abs();
        if odds_diff > BigDecimal::from_str("0.05").unwrap() {
            return Err(AppError::OddsChanged);
        }

        // Calculate potential win
        let potential_win = &bet_request.amount * &bet_request.odds;

        // Create bet record
        let bet_id = Uuid::new_v4();
        let bet = sqlx::query_as::<_, Bet>(
            r#"
            INSERT INTO bets (id, user_id, event_id, bet_type, selection, odds, amount, potential_win, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', NOW(), NOW())
            RETURNING *
            "#
        )
        .bind(bet_id)
        .bind(user_id)
        .bind(bet_request.event_id)
        .bind(&bet_request.bet_type)
        .bind(&bet_request.selection)
        .bind(&bet_request.odds)
        .bind(&bet_request.amount)
        .bind(&potential_win)
        .fetch_one(&mut *tx)
        .await
        .map_err(|e| {
            error!("Failed to create bet: {}", e);
            AppError::Database(e)
        })?;

        // Deduct amount from wallet
        let new_balance = balance - &bet_request.amount;
        let (encrypted_new_balance, new_iv) = self.crypto_service.encrypt_balance(&new_balance)?;

        sqlx::query(
            r#"
            UPDATE wallets
            SET encrypted_balance = $1, encryption_iv = $2, updated_at = NOW()
            WHERE user_id = $3
            "#
        )
        .bind(&encrypted_new_balance)
        .bind(&new_iv)
        .bind(user_id)
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            error!("Failed to update wallet: {}", e);
            AppError::Database(e)
        })?;

        // Create transaction record
        sqlx::query(
            r#"
            INSERT INTO transactions (id, user_id, transaction_type, amount, status, reference_id, created_at)
            VALUES ($1, $2, 'bet', $3, 'completed', $4, NOW())
            "#
        )
        .bind(Uuid::new_v4())
        .bind(user_id)
        .bind(&bet_request.amount)
        .bind(bet_id)
        .execute(&mut *tx)
        .await
        .map_err(|e| {
            error!("Failed to create transaction: {}", e);
            AppError::Database(e)
        })?;

        // Commit transaction
        tx.commit().await.map_err(|e| {
            error!("Failed to commit transaction: {}", e);
            AppError::Database(e)
        })?;

        info!(
            "Bet placed successfully: user_id={}, bet_id={}, amount={}",
            user_id, bet_id, bet_request.amount
        );

        // Check for anomaly detection
        self.detect_betting_anomalies(pool, user_id, &bet_request.amount).await;

        Ok(bet)
    }

    /// Get event by ID
    async fn get_event_by_id(&self, executor: &mut sqlx::PgConnection, event_id: Uuid) -> AppResult<Event> {
        sqlx::query_as::<_, Event>(
            r#"
            SELECT * FROM events WHERE id = $1
            "#
        )
        .bind(event_id)
        .fetch_one(executor)
        .await
        .map_err(|e| match e {
            sqlx::Error::RowNotFound => AppError::EventNotFound,
            _ => {
                error!("Failed to fetch event: {}", e);
                AppError::Database(e)
            }
        })
    }

    /// Get user wallet
    async fn get_user_wallet(&self, executor: &mut sqlx::PgConnection, user_id: Uuid) -> AppResult<Wallet> {
        sqlx::query_as::<_, Wallet>(
            r#"
            SELECT encrypted_balance, encryption_iv FROM wallets WHERE user_id = $1
            "#
        )
        .bind(user_id)
        .fetch_one(executor)
        .await
        .map_err(|e| {
            error!("Failed to fetch wallet: {}", e);
            AppError::Database(e)
        })
    }

    /// Get current odds for a bet type and selection
    fn get_current_odds(&self, event: &Event, bet_type: &str, selection: &str) -> AppResult<BigDecimal> {
        match bet_type {
            "moneyline" => {
                match selection {
                    "home" => event.moneyline_home.clone().ok_or(AppError::InvalidBetAmount),
                    "away" => event.moneyline_away.clone().ok_or(AppError::InvalidBetAmount),
                    _ => Err(AppError::InvalidBetAmount),
                }
            }
            "spread" => {
                match selection {
                    "home" => event.spread_home_odds.clone().ok_or(AppError::InvalidBetAmount),
                    "away" => event.spread_away_odds.clone().ok_or(AppError::InvalidBetAmount),
                    _ => Err(AppError::InvalidBetAmount),
                }
            }
            "total" => {
                match selection {
                    "over" => event.over_odds.clone().ok_or(AppError::InvalidBetAmount),
                    "under" => event.under_odds.clone().ok_or(AppError::InvalidBetAmount),
                    _ => Err(AppError::InvalidBetAmount),
                }
            }
            _ => Err(AppError::InvalidBetAmount),
        }
    }

    /// Check responsible gambling limits
    async fn check_betting_limits(
        &self,
        executor: &mut sqlx::PgConnection,
        user_id: Uuid,
        bet_amount: &BigDecimal,
    ) -> AppResult<()> {
        // Get user's gambling limits
        let limits = sqlx::query_as::<_, GamblingLimits>(
            r#"
            SELECT * FROM gambling_limits WHERE user_id = $1
            "#
        )
        .bind(user_id)
        .fetch_one(&mut *executor)
        .await
        .map_err(|e| {
            error!("Failed to fetch gambling limits: {}", e);
            AppError::Database(e)
        })?;

        // Check if user is self-excluded
        if let Some(excluded_until) = limits.self_excluded_until {
            if excluded_until > Utc::now() {
                return Err(AppError::AccountLocked);
            }
        }

        // Check single bet limit
        if let Some(max_single_bet) = limits.max_single_bet {
            if bet_amount > &max_single_bet {
                return Err(AppError::BetLimitExceeded);
            }
        }

        // Check daily bet limit
        if let Some(daily_limit) = limits.daily_bet_limit {
            let today_bets = self.get_period_bet_total(&mut *executor, user_id, "day").await?;
            if &today_bets + bet_amount > daily_limit {
                return Err(AppError::BetLimitExceeded);
            }
        }

        // Check weekly bet limit
        if let Some(weekly_limit) = limits.weekly_bet_limit {
            let week_bets = self.get_period_bet_total(&mut *executor, user_id, "week").await?;
            if &week_bets + bet_amount > weekly_limit {
                return Err(AppError::BetLimitExceeded);
            }
        }

        // Check monthly bet limit
        if let Some(monthly_limit) = limits.monthly_bet_limit {
            let month_bets = self.get_period_bet_total(&mut *executor, user_id, "month").await?;
            if &month_bets + bet_amount > monthly_limit {
                return Err(AppError::BetLimitExceeded);
            }
        }

        Ok(())
    }

    /// Get total bets for a period
    async fn get_period_bet_total(
        &self,
        executor: &mut sqlx::PgConnection,
        user_id: Uuid,
        period: &str,
    ) -> AppResult<BigDecimal> {
        let interval = match period {
            "day" => "1 day",
            "week" => "7 days",
            "month" => "30 days",
            _ => "1 day",
        };

        let result: Option<BigDecimal> = sqlx::query_scalar(
            &format!(
                r#"
                SELECT COALESCE(SUM(amount), 0)
                FROM bets
                WHERE user_id = $1 AND created_at > NOW() - INTERVAL '{}'
                "#,
                interval
            )
        )
        .bind(user_id)
        .fetch_one(executor)
        .await
        .map_err(|e| {
            error!("Failed to fetch period bet total: {}", e);
            AppError::Database(e)
        })?;

        Ok(result.unwrap_or_else(|| BigDecimal::from(0)))
    }

    /// Detect betting anomalies (fraud detection)
    async fn detect_betting_anomalies(&self, pool: &PgPool, user_id: Uuid, bet_amount: &BigDecimal) {
        // Check for unusual bet patterns
        let recent_bets_count: i64 = sqlx::query_scalar(
            r#"
            SELECT COUNT(*)
            FROM bets
            WHERE user_id = $1 AND created_at > NOW() - INTERVAL '10 minutes'
            "#
        )
        .bind(user_id)
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        if recent_bets_count > 10 {
            warn!(
                "FRAUD ALERT: User {} placed {} bets in 10 minutes",
                user_id, recent_bets_count
            );
        }

        // Check for unusually large bets
        let avg_bet: Option<BigDecimal> = sqlx::query_scalar(
            r#"
            SELECT AVG(amount)
            FROM bets
            WHERE user_id = $1
            "#
        )
        .bind(user_id)
        .fetch_one(pool)
        .await
        .ok()
        .flatten();

        if let Some(avg) = avg_bet {
            if bet_amount > &(&avg * BigDecimal::from(5)) {
                warn!(
                    "FRAUD ALERT: User {} placed bet 5x larger than average: {} vs {}",
                    user_id, bet_amount, avg
                );
            }
        }
    }

    /// Get user's bets
    pub async fn get_user_bets(&self, pool: &PgPool, user_id: Uuid, limit: i64, offset: i64) -> AppResult<Vec<Bet>> {
        sqlx::query_as::<_, Bet>(
            r#"
            SELECT * FROM bets
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            "#
        )
        .bind(user_id)
        .bind(limit)
        .bind(offset)
        .fetch_all(pool)
        .await
        .map_err(|e| {
            error!("Failed to fetch user bets: {}", e);
            AppError::Database(e)
        })
    }

    /// Get bet by ID
    pub async fn get_bet_by_id(&self, pool: &PgPool, bet_id: Uuid, user_id: Uuid) -> AppResult<Bet> {
        sqlx::query_as::<_, Bet>(
            r#"
            SELECT * FROM bets
            WHERE id = $1 AND user_id = $2
            "#
        )
        .bind(bet_id)
        .bind(user_id)
        .fetch_one(pool)
        .await
        .map_err(|e| match e {
            sqlx::Error::RowNotFound => AppError::BetNotFound,
            _ => {
                error!("Failed to fetch bet: {}", e);
                AppError::Database(e)
            }
        })
    }

    /// Get all events
    pub async fn get_events(&self, pool: &PgPool, sport: Option<String>, status: Option<String>) -> AppResult<Vec<Event>> {
        let mut query = String::from("SELECT * FROM events WHERE 1=1");

        if sport.is_some() {
            query.push_str(" AND sport = $1");
        }

        if status.is_some() {
            query.push_str(if sport.is_some() { " AND status = $2" } else { " AND status = $1" });
        }

        query.push_str(" ORDER BY event_date ASC");

        let mut sql_query = sqlx::query_as::<_, Event>(&query);

        if let Some(s) = sport {
            sql_query = sql_query.bind(s);
        }

        if let Some(st) = status {
            sql_query = sql_query.bind(st);
        }

        sql_query
            .fetch_all(pool)
            .await
            .map_err(|e| {
                error!("Failed to fetch events: {}", e);
                AppError::Database(e)
            })
    }

    /// Get event by ID (public version)
    pub async fn get_event(&self, pool: &PgPool, event_id: Uuid) -> AppResult<Event> {
        sqlx::query_as::<_, Event>(
            r#"
            SELECT * FROM events WHERE id = $1
            "#
        )
        .bind(event_id)
        .fetch_one(pool)
        .await
        .map_err(|e| match e {
            sqlx::Error::RowNotFound => AppError::EventNotFound,
            _ => {
                error!("Failed to fetch event: {}", e);
                AppError::Database(e)
            }
        })
    }
}

// Helper struct for wallet queries
#[derive(sqlx::FromRow)]
struct Wallet {
    encrypted_balance: String,
    encryption_iv: String,
}

// Helper struct for gambling limits queries
#[derive(sqlx::FromRow)]
#[allow(dead_code)]
struct GamblingLimits {
    user_id: Uuid,
    daily_bet_limit: Option<BigDecimal>,
    weekly_bet_limit: Option<BigDecimal>,
    monthly_bet_limit: Option<BigDecimal>,
    daily_loss_limit: Option<BigDecimal>,
    weekly_loss_limit: Option<BigDecimal>,
    monthly_loss_limit: Option<BigDecimal>,
    max_single_bet: Option<BigDecimal>,
    self_excluded_until: Option<DateTime<Utc>>,
}
