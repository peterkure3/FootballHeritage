# Simplified Betting Service Guide

## Overview

The `SimpleBettingService` is a refactored, production-ready implementation of the betting system that addresses all the transaction handling issues identified in the original codebase. This service ensures atomic operations, proper error handling, and alignment with the database schema.

## Key Improvements

### 1. **Proper Transaction Handling**
- Single database transaction for all betting operations
- Automatic rollback on errors (SQLx handles this on transaction drop)
- Explicit commit only after all validations pass
- No partial state updates

### 2. **Schema Alignment**
- **Event Status**: Uses `UPCOMING` (not `scheduled`) to match schema constraints
- **Bet Types**: Converts to uppercase (`MONEYLINE`, `SPREAD`, `TOTAL`) to match schema CHECK constraints
- **Selections**: Converts to uppercase (`HOME`, `AWAY`, `OVER`, `UNDER`) to match schema
- **Transactions Table**: Uses correct fields (`balance_before`, `balance_after`, `metadata`, etc.)
- **Transaction Types**: Uses `BET_PLACED` enum value from schema

### 3. **Step-by-Step Validation**
Each bet placement follows a clear sequence:
1. Fetch and validate event
2. Validate bet amount (minimum $1.00)
3. Get wallet balance (decrypted)
4. Check sufficient funds
5. Check responsible gambling limits
6. Verify odds haven't changed (5% tolerance)
7. Calculate potential winnings
8. Create bet record
9. Update wallet balance (encrypted)
10. Create transaction audit record
11. Commit transaction
12. Run fraud detection asynchronously

### 4. **Fraud Detection**
Non-blocking fraud detection that runs after the bet is placed:
- **Rapid Betting**: Flags users placing 10+ bets in 10 minutes
- **Unusual Bet Size**: Flags bets 5x larger than user's 30-day average
- Logs warnings for manual review without blocking legitimate users

## API Reference

### Place Bet
```rust
pub async fn place_bet(
    &self,
    pool: &PgPool,
    user_id: Uuid,
    bet_request: PlaceBetRequest,
) -> AppResult<Bet>
```

**Parameters:**
- `pool`: Database connection pool
- `user_id`: Authenticated user's UUID
- `bet_request`: Bet details (event_id, bet_type, selection, odds, amount)

**Returns:**
- `Ok(Bet)`: Successfully placed bet
- `Err(AppError)`: Error with specific type

**Possible Errors:**
- `EventNotFound`: Event doesn't exist
- `EventNotAvailable`: Event status is not UPCOMING or has already started
- `InvalidBetAmount`: Bet amount < $1.00
- `InsufficientFunds`: User doesn't have enough balance
- `BetLimitExceeded`: Responsible gambling limit exceeded
- `OddsChanged`: Odds changed by more than 5%
- `AccountLocked`: User is self-excluded
- `Database`: Database operation failed

### Get User Bets
```rust
pub async fn get_user_bets(
    &self,
    pool: &PgPool,
    user_id: Uuid,
    limit: i64,
    offset: i64,
) -> AppResult<Vec<Bet>>
```

**Parameters:**
- `user_id`: User's UUID
- `limit`: Maximum number of bets to return
- `offset`: Pagination offset

**Returns:**
- List of bets ordered by creation date (descending)

### Get Bet by ID
```rust
pub async fn get_bet_by_id(
    &self,
    pool: &PgPool,
    bet_id: Uuid,
    user_id: Uuid,
) -> AppResult<Bet>
```

**Parameters:**
- `bet_id`: Bet UUID
- `user_id`: User UUID (ensures users can only view their own bets)

**Returns:**
- `Ok(Bet)`: Bet details
- `Err(BetNotFound)`: Bet doesn't exist or doesn't belong to user

### Get Events
```rust
pub async fn get_events(
    &self,
    pool: &PgPool,
    sport: Option<String>,
    status: Option<String>,
) -> AppResult<Vec<Event>>
```

**Parameters:**
- `sport`: Optional sport filter (e.g., "Football")
- `status`: Optional status filter (e.g., "UPCOMING")

**Returns:**
- List of events ordered by event date (ascending)

### Get Event by ID
```rust
pub async fn get_event(
    &self,
    pool: &PgPool,
    event_id: Uuid,
) -> AppResult<Event>
```

## Usage Examples

### Basic Bet Placement
```rust
use crate::betting_simple::SimpleBettingService;
use crate::models::PlaceBetRequest;
use bigdecimal::BigDecimal;
use std::str::FromStr;

// Initialize service
let crypto_service = Arc::new(CryptoService::new(&encryption_key));
let betting_service = SimpleBettingService::new(crypto_service);

// Create bet request
let bet_request = PlaceBetRequest {
    event_id: event_uuid,
    bet_type: "moneyline".to_string(),  // Will be converted to MONEYLINE
    selection: "home".to_string(),       // Will be converted to HOME
    odds: BigDecimal::from_str("1.85").unwrap(),
    amount: BigDecimal::from_str("50.00").unwrap(),
};

// Place bet
match betting_service.place_bet(&pool, user_id, bet_request).await {
    Ok(bet) => {
        println!("Bet placed! ID: {}, Potential win: {}", bet.id, bet.potential_win);
    }
    Err(AppError::InsufficientFunds) => {
        println!("Insufficient funds in wallet");
    }
    Err(AppError::BetLimitExceeded) => {
        println!("Responsible gambling limit exceeded");
    }
    Err(e) => {
        println!("Error: {:?}", e);
    }
}
```

### Fetching Events
```rust
// Get all upcoming NFL games
let events = betting_service
    .get_events(&pool, Some("Football".to_string()), Some("UPCOMING".to_string()))
    .await?;

for event in events {
    println!("{} vs {} on {}", 
        event.home_team, 
        event.away_team, 
        event.event_date
    );
}
```

### Fetching User Bet History
```rust
// Get first 20 bets for user
let bets = betting_service
    .get_user_bets(&pool, user_id, 20, 0)
    .await?;

for bet in bets {
    println!("Bet #{}: {} on {} - Status: {}", 
        bet.id,
        bet.amount,
        bet.bet_type,
        bet.status
    );
}
```

## Responsible Gambling

The service enforces responsible gambling limits configured per user:

### Limits Checked
- **Single Bet Limit**: Maximum amount for one bet
- **Daily Bet Limit**: Total amount that can be bet in 24 hours
- **Weekly Bet Limit**: Total amount that can be bet in 7 days
- **Monthly Bet Limit**: Total amount that can be bet in 30 days
- **Self-Exclusion**: Users can exclude themselves until a specific date

### Setting Limits
Limits are stored in the `gambling_limits` table. If no limits exist for a user, all bets are allowed (subject to balance).

```sql
INSERT INTO gambling_limits (user_id, daily_bet_limit, max_single_bet)
VALUES ('user-uuid', 500.00, 100.00);
```

## Security Features

### 1. **Wallet Encryption**
- Balances are encrypted using AES-256-GCM
- Each balance has a unique initialization vector (IV)
- Encryption/decryption happens within the transaction

### 2. **Transaction Audit Trail**
Every bet creates a transaction record with:
- User ID and wallet ID
- Transaction type (`BET_PLACED`)
- Amount
- Balance before and after
- Metadata (bet ID, source)
- Fraud flag
- Timestamp

### 3. **Fraud Detection**
Asynchronous fraud detection monitors:
- Rapid betting patterns
- Unusually large bets
- Other suspicious patterns

Alerts are logged for manual review without blocking legitimate users.

### 4. **Input Validation**
- Bet amounts validated (minimum $1.00)
- Event status validated (UPCOMING only)
- Event date validated (future only)
- Odds validated (within 5% of current odds)
- Bet type and selection validated against schema constraints

## Performance Considerations

### Database Efficiency
- Uses parameterized queries (SQLx compile-time checks)
- Single transaction for atomicity (reduces round trips)
- Indexes on frequently queried fields (user_id, event_id, created_at)
- Asynchronous fraud detection (doesn't block bet placement)

### Concurrency
- Tokio async runtime for non-blocking I/O
- Transaction isolation prevents race conditions
- Wallet balance updates are atomic within transaction

### Scalability Recommendations
1. **Connection Pooling**: Use PgPool with appropriate max_connections
2. **Read Replicas**: Route event queries to read replicas
3. **Caching**: Cache frequently accessed events (Redis)
4. **Rate Limiting**: Implement per-user rate limits (already scaffolded in handlers)
5. **Horizontal Scaling**: Service is stateless, can scale horizontally

## Testing

### Unit Tests
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_potential_win() {
        // Tests potential win calculation
    }

    #[test]
    fn test_validate_bet_amount() {
        // Tests bet amount validation
    }
}
```

### Integration Tests
Create integration tests with a test database:
```rust
#[tokio::test]
async fn test_place_bet_success() {
    let pool = create_test_pool().await;
    let service = create_test_service();
    
    // Create test user and wallet
    let user_id = create_test_user(&pool).await;
    fund_wallet(&pool, user_id, BigDecimal::from(1000)).await;
    
    // Create test event
    let event_id = create_test_event(&pool).await;
    
    // Place bet
    let bet_request = PlaceBetRequest { /* ... */ };
    let result = service.place_bet(&pool, user_id, bet_request).await;
    
    assert!(result.is_ok());
}
```

## Migration from Original Service

### Changes Required

1. **Import New Service**
```rust
// Replace
use crate::betting::BettingService;
// With
use crate::betting_simple::SimpleBettingService;
```

2. **Update Initialization**
```rust
// Original
let betting_service = BettingService::new(config, crypto_service);
// Simplified (no config needed)
let betting_service = SimpleBettingService::new(crypto_service);
```

3. **API Remains Same**
All public methods have the same signatures, so handler code doesn't need changes.

### Benefits of Migration
- ✅ Proper transaction handling (atomic operations)
- ✅ Schema alignment (no more field mismatches)
- ✅ Better error messages
- ✅ Cleaner code structure
- ✅ Comprehensive validation
- ✅ Non-blocking fraud detection
- ✅ Unit tests included

## Troubleshooting

### Common Issues

**Issue**: `EventNotFound`
- **Cause**: Event ID doesn't exist
- **Solution**: Verify event_id is valid UUID from events table

**Issue**: `EventNotAvailable`
- **Cause**: Event status is not UPCOMING or has already started
- **Solution**: Only bet on upcoming events; check event.event_date

**Issue**: `InsufficientFunds`
- **Cause**: Wallet balance < bet amount
- **Solution**: User needs to deposit funds

**Issue**: `BetLimitExceeded`
- **Cause**: Responsible gambling limit reached
- **Solution**: User must wait or adjust limits

**Issue**: `OddsChanged`
- **Cause**: Odds changed by >5% since user saw them
- **Solution**: Fetch fresh odds and retry

**Issue**: `AccountLocked`
- **Cause**: User is self-excluded
- **Solution**: User must wait until self_exclusion_until date passes

### Database Transaction Failures

If a transaction fails to commit:
1. All changes are automatically rolled back
2. User's wallet balance remains unchanged
3. No bet or transaction record is created
4. Error is logged with details
5. User receives appropriate error message

## Future Enhancements

### Potential Improvements
1. **Parlay Bets**: Multiple selections in one bet
2. **Live Betting**: Bet on events after they start
3. **Bet Cancellation**: Allow cancellation within time window
4. **Cash Out**: Settle bets early for partial payout
5. **Bonus Funds**: Track and apply promotional bonuses
6. **Bet History Export**: CSV/JSON export of bet history
7. **Advanced Fraud Detection**: Machine learning models
8. **Webhooks**: Notify external systems of bet events

### Performance Monitoring
Add these metrics:
- Average bet placement time
- Transaction commit success rate
- Fraud detection alert rate
- Database query performance
- Concurrent bet capacity

## Support

For issues or questions:
1. Check this guide
2. Review error logs (`tracing` output)
3. Verify database schema matches `schema.sql`
4. Test with integration tests
5. Check database transaction logs

## License

This betting service is part of the Football Heritage Betting platform.