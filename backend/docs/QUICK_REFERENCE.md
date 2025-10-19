# Quick Reference Card - SimpleBettingService

## 🚀 Quick Start

```rust
// Initialize
use crate::betting_simple::SimpleBettingService;
let service = SimpleBettingService::new(crypto_service);

// Place bet
let bet = service.place_bet(&pool, user_id, bet_request).await?;
```

## 📋 Bet Types & Selections

| Bet Type | Selections | Example Odds |
|----------|-----------|--------------|
| `MONEYLINE` | `HOME`, `AWAY` | -150, +130 |
| `SPREAD` | `HOME`, `AWAY` | -110, -110 |
| `TOTAL` | `OVER`, `UNDER` | -105, -115 |

**Note:** Case-insensitive input, automatically converted to uppercase.

## 🔧 Common Operations

### Place a Bet
```rust
let bet_request = PlaceBetRequest {
    event_id: event_uuid,
    bet_type: "moneyline".to_string(),
    selection: "home".to_string(),
    odds: BigDecimal::from_str("1.85").unwrap(),
    amount: BigDecimal::from_str("50.00").unwrap(),
};
let bet = service.place_bet(&pool, user_id, bet_request).await?;
```

### Get Bet History
```rust
let bets = service.get_user_bets(&pool, user_id, 20, 0).await?;
```

### Get Events
```rust
let events = service.get_events(
    &pool, 
    Some("Football".to_string()), 
    Some("UPCOMING".to_string())
).await?;
```

### Get Specific Bet
```rust
let bet = service.get_bet_by_id(&pool, bet_id, user_id).await?;
```

## ⚠️ Error Handling

```rust
match service.place_bet(&pool, user_id, bet_request).await {
    Ok(bet) => println!("Success: {}", bet.id),
    Err(AppError::InsufficientFunds) => println!("Need more funds"),
    Err(AppError::BetLimitExceeded) => println!("Limit reached"),
    Err(AppError::OddsChanged) => println!("Refresh odds"),
    Err(AppError::EventNotAvailable) => println!("Event not open"),
    Err(e) => println!("Error: {:?}", e),
}
```

## 🎯 Common Error Codes

| Error | Meaning | Solution |
|-------|---------|----------|
| `EventNotFound` | Event doesn't exist | Check event_id |
| `EventNotAvailable` | Status != UPCOMING | Only bet on upcoming events |
| `InvalidBetAmount` | Amount < $1.00 | Increase bet amount |
| `InsufficientFunds` | Balance too low | Deposit funds |
| `BetLimitExceeded` | Hit gambling limit | Wait or adjust limits |
| `OddsChanged` | Odds moved >5% | Refresh and retry |
| `AccountLocked` | Self-excluded | Wait until exclusion ends |

## ✅ Validation Rules

- **Minimum bet:** $1.00
- **Event status:** Must be `UPCOMING`
- **Event date:** Must be in future
- **Odds tolerance:** ±5% variance allowed
- **Balance:** Must cover bet amount

## 🔒 Security Features

✅ AES-256-GCM wallet encryption  
✅ ACID transactions (atomic operations)  
✅ Complete audit trail  
✅ Fraud detection (async)  
✅ Responsible gambling limits  
✅ Row-level locking (concurrency)  

## 📊 Database Schema Reference

### Events
```sql
status IN ('UPCOMING', 'LIVE', 'FINISHED', 'CANCELLED')
```

### Bets
```sql
bet_type IN ('MONEYLINE', 'SPREAD', 'TOTAL')
selection IN ('HOME', 'AWAY', 'OVER', 'UNDER')
status IN ('PENDING', 'WON', 'LOST', 'PUSH', 'CANCELLED')
```

### Transactions
```sql
transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'BET_PLACED', 'BET_WON', 'BET_LOST')
```

## 🧪 Testing Commands

```bash
# Run unit tests
cargo test betting_simple

# Run all tests
cargo test

# Run with logging
RUST_LOG=debug cargo test betting_simple

# Check compilation
cargo check
```

## 📦 Import Path

```rust
use crate::betting_simple::SimpleBettingService;
use crate::crypto::CryptoService;
use crate::models::{PlaceBetRequest, Bet, Event};
```

## 🔄 Transaction Flow

1. Begin transaction
2. Fetch & validate event
3. Get wallet balance (decrypt)
4. Check funds & limits
5. Verify odds
6. Create bet record
7. Update wallet (encrypt)
8. Create transaction record
9. Commit (atomic)
10. Fraud detection (async)

## 💡 Best Practices

✅ **Always handle errors explicitly**  
✅ **Validate inputs before calling service**  
✅ **Use pagination for large result sets**  
✅ **Refresh odds before betting**  
✅ **Log all operations for debugging**  
✅ **Monitor fraud detection alerts**  

## 📈 Performance Targets

- **Bet placement:** <150ms
- **Error rate:** <0.1%
- **Transaction success:** >99.9%
- **Throughput:** 500+ bets/second

## 🚨 Production Checklist

- [ ] Schema matches `schema.sql`
- [ ] All indexes in place
- [ ] Event status is UPPERCASE
- [ ] Connection pool configured
- [ ] TLS/HTTPS enabled
- [ ] Rate limiting active
- [ ] Monitoring dashboards ready
- [ ] Logging configured (INFO level)

## 🔗 Documentation Links

- **Full Guide:** `BETTING_SERVICE_GUIDE.md`
- **Fixes:** `TRANSACTION_FIXES.md`
- **README:** `SIMPLIFIED_BETTING_README.md`
- **Deploy:** `DEPLOYMENT_CHECKLIST.md`
- **Examples:** `examples/betting_integration.rs`

## 🆘 Troubleshooting

**Build fails on Windows?**
→ Use Linux/macOS or adjust TLS config

**EventNotAvailable error?**
→ Check event.status is UPPERCASE in DB

**OddsChanged frequently?**
→ May need to adjust 5% tolerance

**Transaction rollback?**
→ Check logs for specific failure point

## 📞 Support

1. Check documentation above
2. Review error logs (tracing output)
3. Verify schema compliance
4. Test with integration examples
5. Contact backend team

---

**Quick Reference Version:** 1.0  
**Last Updated:** 2024  
**Status:** ✅ Production Ready

---

## 💬 Common Snippets

### Place Moneyline Bet
```rust
PlaceBetRequest {
    event_id,
    bet_type: "moneyline".to_string(),
    selection: "home".to_string(),
    odds: BigDecimal::from_str("1.85")?,
    amount: BigDecimal::from_str("50.00")?,
}
```

### Place Spread Bet
```rust
PlaceBetRequest {
    event_id,
    bet_type: "spread".to_string(),
    selection: "away".to_string(),
    odds: BigDecimal::from_str("-110")?,
    amount: BigDecimal::from_str("100.00")?,
}
```

### Place Over/Under
```rust
PlaceBetRequest {
    event_id,
    bet_type: "total".to_string(),
    selection: "over".to_string(),
    odds: BigDecimal::from_str("-105")?,
    amount: BigDecimal::from_str("75.00")?,
}
```

### Paginated History
```rust
let page_size = 20;
let page = 0;
let bets = service.get_user_bets(
    &pool, 
    user_id, 
    page_size, 
    page * page_size
).await?;
```

---

**Pro Tip:** Always test bet placement with small amounts first in production!