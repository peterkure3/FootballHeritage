use crate::crypto::CryptoService;
use crate::errors::{AppError, AppResult};
use crate::models::{Bet, Event, PlaceBetRequest};
use bigdecimal::BigDecimal;
use chrono::{DateTime, Utc};
use sqlx::{PgPool, Postgres, Transaction};
use std::str::FromStr;
use std::sync::Arc;
use tracing::{error, info, warn};
use uuid::Uuid;

/// Simplified betting service with proper transaction handling
pub struct SimpleBettingService {
    crypto_service: Arc<CryptoService>,
}

impl SimpleBettingService {
    pub fn new(crypto_service: Arc<CryptoService>) -> Self {
        Self { crypto_service }
    }

    /// Place a new bet with proper transaction handling
    pub async fn place_bet(
        &self,
        pool: &PgPool,
        user_id: Uuid,
        bet_request: PlaceBetRequest,
    ) -> AppResult<Bet> {
        // Start a single database transaction for all operations
        let mut tx = pool.begin().await.map_err(|e| {
            error!("Failed to start transaction: {}", e);
            AppError::Database(e)
        })?;

        // Step 1: Verify event exists and is available for betting
        let event = self.fetch_event(&mut tx, bet_request.event_id).await?;
        self.validate_event(&event)?;

        // Step 2: Validate bet amount
        self.validate_bet_amount(&bet_request.amount)?;

        // Step 3: Get wallet and decrypt balance
        let (wallet_id, current_balance) = self.get_wallet_balance(&mut tx, user_id).await?;

        // Step 4: Check if user has sufficient funds
        if current_balance < bet_request.amount {
            return Err(AppError::InsufficientFunds);
        }

        // Step 5: Check responsible gambling limits
        self.check_gambling_limits(&mut tx, user_id, &bet_request.amount).await?;

        // Step 6: Verify odds haven't changed significantly
        self.verify_odds(&event, &bet_request)?;

        // Step 7: Calculate potential winnings
        let potential_win = self.calculate_potential_win(&bet_request.amount, &bet_request.odds);

        // Step 8: Create the bet record
        let bet = self.create_bet_record(&mut tx, user_id, &bet_request, &potential_win).await?;

        // Step 9: Update wallet balance (encrypted)
        let new_balance = &current_balance - &bet_request.amount;
        self.update_wallet_balance(&mut tx, user_id, &new_balance).await?;

        // Step 10: Create transaction record for audit trail
        self.create_transaction_record(
            &mut tx,
            user_id,
            wallet_id,
            &bet_request.amount,
            &current_balance,
            &new_balance,
            bet.id,
        )
        .await?;

        // Step 11: Commit the transaction
        tx.commit().await.map_err(|e| {
            error!("Failed to commit bet transaction: {}", e);
            AppError::Database(e)
        })?;

        info!(
            "Bet placed successfully: user_id={}, bet_id={}, amount={}",
            user_id, bet.id, bet_request.amount
        );

        // Step 12: Run fraud detection asynchronously (after commit)
        tokio::spawn({
            let pool = pool.clone();
            let user_id = user_id;
            let amount = bet_request.amount.clone();
            async move {
                if let Err(e) = Self::detect_fraud_patterns(&pool, user_id, &amount).await {
                    error!("Fraud detection failed: {}", e);
                }
            }
        });

        Ok(bet)
    }

    /// Fetch event from database
    async fn fetch_event(
        &self,
        tx: &mut Transaction<'_, Postgres>,
        event_id: Uuid,
    ) -> AppResult<Event> {
        sqlx::query_as::<_, Event>(
            r#"
            SELECT * FROM events WHERE id = $1
            "#,
        )
        .bind(event_id)
        .fetch_one(&mut **tx)
        .await
        .map_err(|e| match e {
            sqlx::Error::RowNotFound => AppError::EventNotFound,
            _ => {
                error!("Failed to fetch event: {}", e);
                AppError::Database(e)
            }
        })
    }

    /// Validate event is available for betting
    fn validate_event(&self, event: &Event) -> AppResult<()> {
        // Check status - schema uses "UPCOMING", not "scheduled"
        if event.status != "UPCOMING" {
            return Err(AppError::EventNotAvailable);
        }

        // Check if event hasn't started yet
        if event.event_date <= Utc::now() {
            return Err(AppError::EventNotAvailable);
        }

        Ok(())
    }

    /// Validate bet amount
    fn validate_bet_amount(&self, amount: &BigDecimal) -> AppResult<()> {
        let min_bet = BigDecimal::from_str("1.00").map_err(|e| {
            AppError::Internal(format!("Failed to parse minimum bet: {}", e))
        })?;

        if amount < &min_bet {
            return Err(AppError::InvalidBetAmount);
        }

        Ok(())
    }

    /// Get wallet balance (decrypted)
    async fn get_wallet_balance(
        &self,
        tx: &mut Transaction<'_, Postgres>,
        user_id: Uuid,
    ) -> AppResult<(Uuid, BigDecimal)> {
        let wallet: WalletData = sqlx::query_as(
            r#"
            SELECT id, encrypted_balance, encryption_iv
            FROM wallets
            WHERE user_id = $1
            "#,
        )
        .bind(user_id)
        .fetch_one(&mut **tx)
        .await
        .map_err(|e| {
            error!("Failed to fetch wallet for user {}: {}", user_id, e);
            AppError::Database(e)
        })?;

        // Decrypt balance
        let balance = self
            .crypto_service
            .decrypt_balance(&wallet.encrypted_balance, &wallet.encryption_iv)?
            .to_string()
            .parse::<BigDecimal>()
            .map_err(|e| AppError::Internal(format!("Failed to parse balance: {}", e)))?;

        Ok((wallet.id, balance))
    }

    /// Check responsible gambling limits
    async fn check_gambling_limits(
        &self,
        tx: &mut Transaction<'_, Postgres>,
        user_id: Uuid,
        bet_amount: &BigDecimal,
    ) -> AppResult<()> {
        // Fetch gambling limits
        let limits: Option<GamblingLimitsData> = sqlx::query_as(
            r#"
            SELECT daily_bet_limit, weekly_bet_limit, monthly_bet_limit,
                   max_single_bet, self_exclusion_until
            FROM gambling_limits
            WHERE user_id = $1
            "#,
        )
        .bind(user_id)
        .fetch_optional(&mut **tx)
        .await
        .map_err(|e| {
            error!("Failed to fetch gambling limits: {}", e);
            AppError::Database(e)
        })?;

        // If no limits are set, allow the bet
        let Some(limits) = limits else {
            return Ok(());
        };

        // Check self-exclusion
        if let Some(excluded_until) = limits.self_exclusion_until {
            if excluded_until > Utc::now() {
                return Err(AppError::AccountLocked);
            }
        }

        // Check single bet limit
        if let Some(max_single) = limits.max_single_bet {
            if bet_amount > &max_single {
                return Err(AppError::BetLimitExceeded);
            }
        }

        // Check daily limit
        if let Some(daily_limit) = limits.daily_bet_limit {
            let daily_total = self.get_period_total(tx, user_id, 1).await?;
            if &daily_total + bet_amount > daily_limit {
                return Err(AppError::BetLimitExceeded);
            }
        }

        // Check weekly limit
        if let Some(weekly_limit) = limits.weekly_bet_limit {
            let weekly_total = self.get_period_total(tx, user_id, 7).await?;
            if &weekly_total + bet_amount > weekly_limit {
                return Err(AppError::BetLimitExceeded);
            }
        }

        // Check monthly limit
        if let Some(monthly_limit) = limits.monthly_bet_limit {
            let monthly_total = self.get_period_total(tx, user_id, 30).await?;
            if &monthly_total + bet_amount > monthly_limit {
                return Err(AppError::BetLimitExceeded);
            }
        }

        Ok(())
    }

    /// Get total bets for a period (in days)
    async fn get_period_total(
        &self,
        tx: &mut Transaction<'_, Postgres>,
        user_id: Uuid,
        days: i32,
    ) -> AppResult<BigDecimal> {
        let total: Option<BigDecimal> = sqlx::query_scalar(
            r#"
            SELECT COALESCE(SUM(amount), 0)
            FROM bets
            WHERE user_id = $1
              AND created_at > NOW() - INTERVAL '1 day' * $2
              AND status != 'CANCELLED'
            "#,
        )
        .bind(user_id)
        .bind(days)
        .fetch_one(&mut **tx)
        .await
        .map_err(|e| {
            error!("Failed to fetch period total: {}", e);
            AppError::Database(e)
        })?;

        Ok(total.unwrap_or_else(|| BigDecimal::from(0)))
    }

    /// Verify odds haven't changed significantly
    fn verify_odds(&self, event: &Event, bet_request: &PlaceBetRequest) -> AppResult<()> {
        let current_odds = self.get_current_odds(event, &bet_request.bet_type, &bet_request.selection)?;

        // Allow 5% variance in odds
        let odds_diff = (&bet_request.odds - &current_odds).abs();
        let max_variance = BigDecimal::from_str("0.05")
            .map_err(|e| AppError::Internal(format!("Failed to parse variance: {}", e)))?;

        if odds_diff > max_variance {
            return Err(AppError::OddsChanged);
        }

        Ok(())
    }

    /// Get current odds for a bet
    fn get_current_odds(
        &self,
        event: &Event,
        bet_type: &str,
        selection: &str,
    ) -> AppResult<BigDecimal> {
        // Convert to uppercase to match schema constraints
        let bet_type_upper = bet_type.to_uppercase();
        let selection_upper = selection.to_uppercase();

        match bet_type_upper.as_str() {
            "MONEYLINE" => match selection_upper.as_str() {
                "HOME" => event
                    .moneyline_home
                    .clone()
                    .ok_or(AppError::InvalidBetAmount),
                "AWAY" => event
                    .moneyline_away
                    .clone()
                    .ok_or(AppError::InvalidBetAmount),
                _ => Err(AppError::InvalidBetAmount),
            },
            "SPREAD" => match selection_upper.as_str() {
                "HOME" => event
                    .spread_home_odds
                    .clone()
                    .ok_or(AppError::InvalidBetAmount),
                "AWAY" => event
                    .spread_away_odds
                    .clone()
                    .ok_or(AppError::InvalidBetAmount),
                _ => Err(AppError::InvalidBetAmount),
            },
            "TOTAL" => match selection_upper.as_str() {
                "OVER" => event.over_odds.clone().ok_or(AppError::InvalidBetAmount),
                "UNDER" => event.under_odds.clone().ok_or(AppError::InvalidBetAmount),
                _ => Err(AppError::InvalidBetAmount),
            },
            _ => Err(AppError::InvalidBetAmount),
        }
    }

    /// Calculate potential winnings
    fn calculate_potential_win(&self, amount: &BigDecimal, odds: &BigDecimal) -> BigDecimal {
        amount * odds
    }

    /// Create bet record
    async fn create_bet_record(
        &self,
        tx: &mut Transaction<'_, Postgres>,
        user_id: Uuid,
        bet_request: &PlaceBetRequest,
        potential_win: &BigDecimal,
    ) -> AppResult<Bet> {
        let bet_id = Uuid::new_v4();

        // Convert to uppercase to match schema constraints
        let bet_type_upper = bet_request.bet_type.to_uppercase();
        let selection_upper = bet_request.selection.to_uppercase();

        let bet = sqlx::query_as::<_, Bet>(
            r#"
            INSERT INTO bets (
                id, user_id, event_id, bet_type, selection,
                odds, amount, potential_win, status, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'PENDING', NOW(), NOW())
            RETURNING *
            "#,
        )
        .bind(bet_id)
        .bind(user_id)
        .bind(bet_request.event_id)
        .bind(&bet_type_upper)
        .bind(&selection_upper)
        .bind(&bet_request.odds)
        .bind(&bet_request.amount)
        .bind(potential_win)
        .fetch_one(&mut **tx)
        .await
        .map_err(|e| {
            error!("Failed to create bet: {}", e);
            AppError::Database(e)
        })?;

        Ok(bet)
    }

    /// Update wallet balance with encryption
    async fn update_wallet_balance(
        &self,
        tx: &mut Transaction<'_, Postgres>,
        user_id: Uuid,
        new_balance: &BigDecimal,
    ) -> AppResult<()> {
        // Encrypt new balance
        let (encrypted_balance, iv) = self.crypto_service.encrypt_balance(new_balance)?;

        sqlx::query(
            r#"
            UPDATE wallets
            SET encrypted_balance = $1,
                encryption_iv = $2,
                updated_at = NOW()
            WHERE user_id = $3
            "#,
        )
        .bind(&encrypted_balance)
        .bind(&iv)
        .bind(user_id)
        .execute(&mut **tx)
        .await
        .map_err(|e| {
            error!("Failed to update wallet balance: {}", e);
            AppError::Database(e)
        })?;

        Ok(())
    }

    /// Create transaction record aligned with schema
    async fn create_transaction_record(
        &self,
        tx: &mut Transaction<'_, Postgres>,
        user_id: Uuid,
        wallet_id: Uuid,
        amount: &BigDecimal,
        balance_before: &BigDecimal,
        balance_after: &BigDecimal,
        bet_id: Uuid,
    ) -> AppResult<()> {
        let metadata = serde_json::json!({
            "bet_id": bet_id,
            "transaction_source": "betting"
        });

        sqlx::query(
            r#"
            INSERT INTO transactions (
                id, user_id, wallet_id, transaction_type, amount,
                balance_before, balance_after, description, metadata,
                created_at, is_fraud_flagged
            )
            VALUES ($1, $2, $3, 'BET_PLACED', $4, $5, $6, $7, $8, NOW(), false)
            "#,
        )
        .bind(Uuid::new_v4())
        .bind(user_id)
        .bind(wallet_id)
        .bind(amount)
        .bind(balance_before)
        .bind(balance_after)
        .bind(format!("Bet placed on event"))
        .bind(&metadata)
        .execute(&mut **tx)
        .await
        .map_err(|e| {
            error!("Failed to create transaction record: {}", e);
            AppError::Database(e)
        })?;

        Ok(())
    }

    /// Detect fraud patterns (async, non-blocking)
    async fn detect_fraud_patterns(
        pool: &PgPool,
        user_id: Uuid,
        bet_amount: &BigDecimal,
    ) -> AppResult<()> {
        // Check for rapid betting (10+ bets in 10 minutes)
        let recent_count: i64 = sqlx::query_scalar(
            r#"
            SELECT COUNT(*)
            FROM bets
            WHERE user_id = $1
              AND created_at > NOW() - INTERVAL '10 minutes'
            "#,
        )
        .bind(user_id)
        .fetch_one(pool)
        .await
        .unwrap_or(0);

        if recent_count > 10 {
            warn!(
                "FRAUD ALERT: Rapid betting detected - user_id={}, count={}",
                user_id, recent_count
            );
        }

        // Check for unusually large bets (5x average)
        let avg_bet: Option<BigDecimal> = sqlx::query_scalar(
            r#"
            SELECT AVG(amount)
            FROM bets
            WHERE user_id = $1
              AND created_at > NOW() - INTERVAL '30 days'
            "#,
        )
        .bind(user_id)
        .fetch_one(pool)
        .await
        .ok()
        .flatten();

        if let Some(avg) = avg_bet {
            let threshold = &avg * BigDecimal::from(5);
            if bet_amount > &threshold {
                warn!(
                    "FRAUD ALERT: Unusually large bet - user_id={}, amount={}, avg={}",
                    user_id, bet_amount, avg
                );
            }
        }

        Ok(())
    }

    /// Get user's bet history
    pub async fn get_user_bets(
        &self,
        pool: &PgPool,
        user_id: Uuid,
        limit: i64,
        offset: i64,
    ) -> AppResult<Vec<Bet>> {
        sqlx::query_as::<_, Bet>(
            r#"
            SELECT * FROM bets
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            "#,
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
    pub async fn get_bet_by_id(
        &self,
        pool: &PgPool,
        bet_id: Uuid,
        user_id: Uuid,
    ) -> AppResult<Bet> {
        sqlx::query_as::<_, Bet>(
            r#"
            SELECT * FROM bets
            WHERE id = $1 AND user_id = $2
            "#,
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

    /// Get available events
    /// 
    /// Filters out expired events (event_date <= NOW())
    /// Only returns future events to prevent betting on past games
    pub async fn get_events(
        &self,
        pool: &PgPool,
        sport: Option<String>,
        status: Option<String>,
    ) -> AppResult<Vec<Event>> {
        let mut query_str = String::from(
            r#"
            SELECT * FROM events
            WHERE 1=1
            AND event_date > NOW()
            "#,
        );

        let mut bind_count = 0;

        if sport.is_some() {
            bind_count += 1;
            query_str.push_str(&format!(" AND sport = ${}", bind_count));
        }

        if status.is_some() {
            bind_count += 1;
            query_str.push_str(&format!(" AND status = ${}", bind_count));
        }

        query_str.push_str(" ORDER BY event_date ASC");

        let mut query = sqlx::query_as::<_, Event>(&query_str);

        if let Some(s) = sport {
            query = query.bind(s);
        }

        if let Some(st) = status {
            query = query.bind(st);
        }

        query.fetch_all(pool).await.map_err(|e| {
            error!("Failed to fetch events: {}", e);
            AppError::Database(e)
        })
    }

    /// Get event by ID
    pub async fn get_event(&self, pool: &PgPool, event_id: Uuid) -> AppResult<Event> {
        sqlx::query_as::<_, Event>(
            r#"
            SELECT * FROM events WHERE id = $1
            "#,
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

// Helper structs for database queries
#[derive(sqlx::FromRow)]
struct WalletData {
    id: Uuid,
    encrypted_balance: String,
    encryption_iv: String,
}

#[derive(sqlx::FromRow)]
struct GamblingLimitsData {
    daily_bet_limit: Option<BigDecimal>,
    weekly_bet_limit: Option<BigDecimal>,
    monthly_bet_limit: Option<BigDecimal>,
    max_single_bet: Option<BigDecimal>,
    self_exclusion_until: Option<DateTime<Utc>>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_potential_win() {
        let service = SimpleBettingService::new(Arc::new(CryptoService::new(&[0u8; 32])));
        let amount = BigDecimal::from_str("100.00").unwrap();
        let odds = BigDecimal::from_str("2.5").unwrap();
        let potential_win = service.calculate_potential_win(&amount, &odds);
        assert_eq!(potential_win, BigDecimal::from_str("250.00").unwrap());
    }

    #[test]
    fn test_validate_bet_amount() {
        let service = SimpleBettingService::new(Arc::new(CryptoService::new(&[0u8; 32])));

        // Valid amount
        let valid = BigDecimal::from_str("10.00").unwrap();
        assert!(service.validate_bet_amount(&valid).is_ok());

        // Invalid amount (too small)
        let invalid = BigDecimal::from_str("0.50").unwrap();
        assert!(service.validate_bet_amount(&invalid).is_err());
    }
}
