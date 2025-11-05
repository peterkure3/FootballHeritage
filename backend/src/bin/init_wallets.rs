use anyhow::Result;
use bigdecimal::BigDecimal;
use dotenvy::dotenv;
use sqlx::PgPool;
use std::str::FromStr;

#[path = "../config.rs"]
mod config;
#[path = "../crypto.rs"]
mod crypto;
#[path = "../errors.rs"]
mod errors;

use config::AppConfig;
use crypto::CryptoService;

#[tokio::main]
async fn main() -> Result<()> {
    dotenv().ok();
    
    println!("🔧 Wallet Initialization Utility");
    println!("================================\n");
    
    // Load configuration
    let config = AppConfig::from_env()?;
    println!("✓ Configuration loaded");
    
    // Validate encryption key
    if !config.validate_encryption_key() {
        eprintln!("❌ ERROR: ENCRYPTION_KEY must be exactly 32 bytes");
        eprintln!("Current length: {} bytes", config.encryption_key.len());
        std::process::exit(1);
    }
    println!("✓ Encryption key validated (32 bytes)");
    
    // Connect to database
    let pool = PgPool::connect(&config.database_url).await?;
    println!("✓ Database connected\n");
    
    // Initialize crypto service
    let crypto_service = CryptoService::from_string(&config.encryption_key);
    
    // Get all users without wallets
    let users_without_wallets: Vec<(uuid::Uuid, String)> = sqlx::query_as(
        r#"
        SELECT u.id, u.email
        FROM users u
        LEFT JOIN wallets w ON u.id = w.user_id
        WHERE w.id IS NULL
        "#
    )
    .fetch_all(&pool)
    .await?;
    
    if users_without_wallets.is_empty() {
        println!("✓ All users already have wallets");
    } else {
        println!("Found {} users without wallets:", users_without_wallets.len());
        
        for (user_id, email) in &users_without_wallets {
            println!("  - {} ({})", email, user_id);
        }
        
        println!("\nCreating wallets with 0.00 balance...");
        
        for (user_id, email) in users_without_wallets {
            let initial_balance = BigDecimal::from_str("0.00")?;
            let (encrypted_balance, iv) = crypto_service.encrypt_balance(&initial_balance)
                .map_err(|e| anyhow::anyhow!("Encryption failed: {}", e))?;
            
            sqlx::query(
                r#"
                INSERT INTO wallets (id, user_id, encrypted_balance, encryption_iv, created_at, updated_at)
                VALUES (gen_random_uuid(), $1, $2, $3, NOW(), NOW())
                "#
            )
            .bind(user_id)
            .bind(&encrypted_balance)
            .bind(&iv)
            .execute(&pool)
            .await?;
            
            println!("  ✓ Created wallet for {}", email);
        }
    }
    
    // Get all existing wallets and re-encrypt with new key
    println!("\nChecking existing wallets...");
    
    let existing_wallets: Vec<(uuid::Uuid, uuid::Uuid, String)> = sqlx::query_as(
        r#"
        SELECT w.id, w.user_id, u.email
        FROM wallets w
        JOIN users u ON w.user_id = u.id
        "#
    )
    .fetch_all(&pool)
    .await?;
    
    println!("Found {} existing wallets", existing_wallets.len());
    
    if !existing_wallets.is_empty() {
        println!("\n⚠️  WARNING: Existing wallets detected!");
        println!("If you changed the ENCRYPTION_KEY, existing balances cannot be decrypted.");
        println!("Options:");
        println!("  1. Keep existing encrypted data (may cause decryption errors)");
        println!("  2. Reset all balances to 0.00 with new encryption");
        println!("\nTo reset balances, run:");
        println!("  cargo run --bin reset_wallets");
    }
    
    println!("\n✅ Wallet initialization complete!");
    
    Ok(())
}
