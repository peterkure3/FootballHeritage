//! # Betting Service Integration Example
//!
//! This example demonstrates how to integrate the SimpleBettingService
//! into your application and use it to place bets, retrieve events, and
//! manage user betting history.

use bigdecimal::BigDecimal;
use sqlx::PgPool;
use std::str::FromStr;
use std::sync::Arc;
use uuid::Uuid;

// Import your application modules
use backend::betting_simple::SimpleBettingService;
use backend::crypto::CryptoService;
use backend::errors::AppError;
use backend::models::{Event, PlaceBetRequest};

/// Example: Initialize the betting service
async fn initialize_service() -> SimpleBettingService {
    // Load encryption key from environment
    let encryption_key = std::env::var("ENCRYPTION_KEY")
        .expect("ENCRYPTION_KEY must be set")
        .as_bytes()
        .to_vec();

    // Ensure key is 32 bytes for AES-256
    let mut key = [0u8; 32];
    key.copy_from_slice(&encryption_key[..32]);

    // Create crypto service
    let crypto_service = Arc::new(CryptoService::new(&key));

    // Create betting service
    SimpleBettingService::new(crypto_service)
}

/// Example: Place a bet on a moneyline
async fn example_place_moneyline_bet(
    service: &SimpleBettingService,
    pool: &PgPool,
    user_id: Uuid,
    event_id: Uuid,
) -> Result<(), AppError> {
    println!("Placing moneyline bet...");

    // Create bet request
    let bet_request = PlaceBetRequest {
        event_id,
        bet_type: "moneyline".to_string(), // Case-insensitive
        selection: "home".to_string(),     // Will be converted to HOME
        odds: BigDecimal::from_str("1.85").unwrap(),
        amount: BigDecimal::from_str("50.00").unwrap(),
    };

    // Place the bet
    match service.place_bet(pool, user_id, bet_request).await {
        Ok(bet) => {
            println!("✓ Bet placed successfully!");
            println!("  Bet ID: {}", bet.id);
            println!("  Amount: ${}", bet.amount);
            println!("  Potential Win: ${}", bet.potential_win);
            println!("  Status: {}", bet.status);
            Ok(())
        }
        Err(AppError::InsufficientFunds) => {
            println!("✗ Insufficient funds in wallet");
            Err(AppError::InsufficientFunds)
        }
        Err(AppError::BetLimitExceeded) => {
            println!("✗ Responsible gambling limit exceeded");
            Err(AppError::BetLimitExceeded)
        }
        Err(AppError::OddsChanged) => {
            println!("✗ Odds have changed, please refresh and try again");
            Err(AppError::OddsChanged)
        }
        Err(e) => {
            println!("✗ Error placing bet: {:?}", e);
            Err(e)
        }
    }
}

/// Example: Place a spread bet
async fn example_place_spread_bet(
    service: &SimpleBettingService,
    pool: &PgPool,
    user_id: Uuid,
    event_id: Uuid,
) -> Result<(), AppError> {
    println!("Placing spread bet...");

    let bet_request = PlaceBetRequest {
        event_id,
        bet_type: "SPREAD".to_string(), // Uppercase also works
        selection: "AWAY".to_string(),
        odds: BigDecimal::from_str("-110").unwrap(),
        amount: BigDecimal::from_str("100.00").unwrap(),
    };

    let bet = service.place_bet(pool, user_id, bet_request).await?;
    println!("✓ Spread bet placed: {}", bet.id);
    Ok(())
}

/// Example: Place an over/under bet
async fn example_place_total_bet(
    service: &SimpleBettingService,
    pool: &PgPool,
    user_id: Uuid,
    event_id: Uuid,
) -> Result<(), AppError> {
    println!("Placing over/under bet...");

    let bet_request = PlaceBetRequest {
        event_id,
        bet_type: "total".to_string(),
        selection: "over".to_string(),
        odds: BigDecimal::from_str("-105").unwrap(),
        amount: BigDecimal::from_str("75.00").unwrap(),
    };

    let bet = service.place_bet(pool, user_id, bet_request).await?;
    println!("✓ Total bet placed: {}", bet.id);
    Ok(())
}

/// Example: Fetch all upcoming NFL games
async fn example_fetch_upcoming_games(
    service: &SimpleBettingService,
    pool: &PgPool,
) -> Result<Vec<Event>, AppError> {
    println!("Fetching upcoming NFL games...");

    let events = service
        .get_events(
            pool,
            Some("Football".to_string()),
            Some("UPCOMING".to_string()),
        )
        .await?;

    println!("Found {} upcoming games:", events.len());
    for event in &events {
        println!("  {} vs {} on {}",
            event.home_team,
            event.away_team,
            event.event_date.format("%Y-%m-%d %H:%M")
        );
        println!("    Moneyline: Home {} / Away {}",
            event.moneyline_home.as_ref().map(|o| o.to_string()).unwrap_or("N/A".to_string()),
            event.moneyline_away.as_ref().map(|o| o.to_string()).unwrap_or("N/A".to_string())
        );
    }

    Ok(events)
}

/// Example: Fetch user's betting history
async fn example_fetch_bet_history(
    service: &SimpleBettingService,
    pool: &PgPool,
    user_id: Uuid,
) -> Result<(), AppError> {
    println!("Fetching bet history for user {}...", user_id);

    // Get first 20 bets
    let bets = service.get_user_bets(pool, user_id, 20, 0).await?;

    println!("Found {} bets:", bets.len());
    for bet in bets {
        println!("  Bet #{}", bet.id);
        println!("    Type: {} - {}", bet.bet_type, bet.selection);
        println!("    Amount: ${}", bet.amount);
        println!("    Odds: {}", bet.odds);
        println!("    Potential Win: ${}", bet.potential_win);
        println!("    Status: {}", bet.status);
        println!("    Created: {}", bet.created_at.format("%Y-%m-%d %H:%M:%S"));
        println!();
    }

    Ok(())
}

/// Example: Get specific bet details
async fn example_get_bet_details(
    service: &SimpleBettingService,
    pool: &PgPool,
    user_id: Uuid,
    bet_id: Uuid,
) -> Result<(), AppError> {
    println!("Fetching bet details...");

    let bet = service.get_bet_by_id(pool, bet_id, user_id).await?;

    println!("Bet Details:");
    println!("  ID: {}", bet.id);
    println!("  User ID: {}", bet.user_id);
    println!("  Event ID: {}", bet.event_id);
    println!("  Type: {}", bet.bet_type);
    println!("  Selection: {}", bet.selection);
    println!("  Odds: {}", bet.odds);
    println!("  Amount: ${}", bet.amount);
    println!("  Potential Win: ${}", bet.potential_win);
    println!("  Status: {}", bet.status);
    println!("  Created: {}", bet.created_at);

    if let Some(settled) = bet.settled_at {
        println!("  Settled: {}", settled);
    }

    Ok(())
}

/// Example: Handle multiple bet placements with error handling
async fn example_place_multiple_bets(
    service: &SimpleBettingService,
    pool: &PgPool,
    user_id: Uuid,
    event_ids: Vec<Uuid>,
) -> Result<(), AppError> {
    println!("Placing multiple bets...");

    let mut successful = 0;
    let mut failed = 0;

    for event_id in event_ids {
        let bet_request = PlaceBetRequest {
            event_id,
            bet_type: "moneyline".to_string(),
            selection: "home".to_string(),
            odds: BigDecimal::from_str("2.00").unwrap(),
            amount: BigDecimal::from_str("25.00").unwrap(),
        };

        match service.place_bet(pool, user_id, bet_request).await {
            Ok(bet) => {
                successful += 1;
                println!("  ✓ Bet {} placed successfully", bet.id);
            }
            Err(e) => {
                failed += 1;
                println!("  ✗ Failed to place bet on event {}: {:?}", event_id, e);
            }
        }
    }

    println!("Results: {} successful, {} failed", successful, failed);
    Ok(())
}

/// Example: Paginated bet history
async fn example_paginated_history(
    service: &SimpleBettingService,
    pool: &PgPool,
    user_id: Uuid,
) -> Result<(), AppError> {
    println!("Fetching paginated bet history...");

    let page_size = 10;
    let mut page = 0;
    let mut total_bets = 0;

    loop {
        let offset = page * page_size;
        let bets = service.get_user_bets(pool, user_id, page_size, offset).await?;

        if bets.is_empty() {
            break;
        }

        total_bets += bets.len();
        println!("Page {}: {} bets", page + 1, bets.len());

        for bet in bets {
            println!("  - {} on {} (${}) - {}",
                bet.bet_type,
                bet.created_at.format("%Y-%m-%d"),
                bet.amount,
                bet.status
            );
        }

        page += 1;
    }

    println!("Total bets found: {}", total_bets);
    Ok(())
}

/// Example: Get event details before placing bet
async fn example_bet_with_event_check(
    service: &SimpleBettingService,
    pool: &PgPool,
    user_id: Uuid,
    event_id: Uuid,
) -> Result<(), AppError> {
    println!("Checking event details before betting...");

    // First, get event details
    let event = service.get_event(pool, event_id).await?;

    println!("Event: {} vs {}", event.home_team, event.away_team);
    println!("Status: {}", event.status);
    println!("Date: {}", event.event_date);

    // Check if event is available for betting
    if event.status != "UPCOMING" {
        println!("✗ Event is not available for betting");
        return Err(AppError::EventNotAvailable);
    }

    // Check if event has odds
    if event.moneyline_home.is_none() || event.moneyline_away.is_none() {
        println!("✗ Event does not have odds set");
        return Err(AppError::InvalidBetAmount);
    }

    // Get the current odds
    let home_odds = event.moneyline_home.as_ref().unwrap();
    println!("Current home odds: {}", home_odds);

    // Place bet with current odds
    let bet_request = PlaceBetRequest {
        event_id,
        bet_type: "moneyline".to_string(),
        selection: "home".to_string(),
        odds: home_odds.clone(),
        amount: BigDecimal::from_str("50.00").unwrap(),
    };

    let bet = service.place_bet(pool, user_id, bet_request).await?;
    println!("✓ Bet placed: {}", bet.id);

    Ok(())
}

/// Main example runner
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Load environment variables
    dotenvy::dotenv().ok();

    // Initialize logging
    tracing_subscriber::fmt::init();

    // Connect to database
    let database_url = std::env::var("DATABASE_URL")?;
    let pool = PgPool::connect(&database_url).await?;

    // Initialize service
    let service = initialize_service().await;

    // Example user ID (replace with actual authenticated user)
    let user_id = Uuid::parse_str("00000000-0000-0000-0000-000000000001")?;

    println!("\n=== Betting Service Integration Examples ===\n");

    // Example 1: Fetch upcoming games
    println!("\n--- Example 1: Fetch Upcoming Games ---");
    if let Ok(events) = example_fetch_upcoming_games(&service, &pool).await {
        if let Some(first_event) = events.first() {
            let event_id = first_event.id;

            // Example 2: Place moneyline bet
            println!("\n--- Example 2: Place Moneyline Bet ---");
            let _ = example_place_moneyline_bet(&service, &pool, user_id, event_id).await;

            // Example 3: Place spread bet
            println!("\n--- Example 3: Place Spread Bet ---");
            let _ = example_place_spread_bet(&service, &pool, user_id, event_id).await;

            // Example 4: Place total bet
            println!("\n--- Example 4: Place Total Bet ---");
            let _ = example_place_total_bet(&service, &pool, user_id, event_id).await;
        }
    }

    // Example 5: Fetch bet history
    println!("\n--- Example 5: Fetch Bet History ---");
    let _ = example_fetch_bet_history(&service, &pool, user_id).await;

    // Example 6: Paginated history
    println!("\n--- Example 6: Paginated Bet History ---");
    let _ = example_paginated_history(&service, &pool, user_id).await;

    println!("\n=== Examples Complete ===\n");

    Ok(())
}

// Unit tests
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bet_request_creation() {
        let bet_request = PlaceBetRequest {
            event_id: Uuid::new_v4(),
            bet_type: "moneyline".to_string(),
            selection: "home".to_string(),
            odds: BigDecimal::from_str("1.85").unwrap(),
            amount: BigDecimal::from_str("50.00").unwrap(),
        };

        assert_eq!(bet_request.bet_type, "moneyline");
        assert_eq!(bet_request.selection, "home");
    }

    #[test]
    fn test_odds_calculation() {
        let amount = BigDecimal::from_str("100.00").unwrap();
        let odds = BigDecimal::from_str("2.50").unwrap();
        let potential_win = &amount * &odds;

        assert_eq!(potential_win, BigDecimal::from_str("250.00").unwrap());
    }
}
