use anyhow::Result;
use bigdecimal::BigDecimal;
use dotenvy::dotenv;
use sqlx::PgPool;
use std::io::{self, Write};
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
    
    println!("⚠️  WALLET RESET UTILITY");
    println!("========================\n");
    println!("This will reset ALL wallet balances to 0.00 using the new encryption key.");
    println!("This is necessary when the ENCRYPTION_KEY has been changed.\n");
    
    // Confirmation prompt
    print!("Are you sure you want to continue? (yes/no): ");
    io::stdout().flush()?;
    
    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    
    if input.trim().to_lowercase() != "yes" {
        println!("Operation cancelled.");
        return Ok(());
    }
    
    // Load configuration
    let config = AppConfig::from_env()?;
    println!("\n✓ Configuration loaded");
    
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
    
    // Get all wallets
    let wallets: Vec<(uuid::Uuid, uuid::Uuid, String)> = sqlx::query_as(
        r#"
        SELECT w.id, w.user_id, u.email
        FROM wallets w
        JOIN users u ON w.user_id = u.id
        "#
    )
    .fetch_all(&pool)
    .await?;
    
    println!("Found {} wallets to reset:", wallets.len());
    
    let initial_balance = BigDecimal::from_str("0.00")?;
    let (encrypted_balance, iv) = crypto_service.encrypt_balance(&initial_balance)
        .map_err(|e| anyhow::anyhow!("Encryption failed: {}", e))?;
    
    for (wallet_id, _user_id, email) in wallets {
        sqlx::query(
            r#"
            UPDATE wallets
            SET encrypted_balance = $1,
                encryption_iv = $2,
                updated_at = NOW()
            WHERE id = $3
            "#
        )
        .bind(&encrypted_balance)
        .bind(&iv)
        .bind(wallet_id)
        .execute(&pool)
        .await?;
        
        println!("  ✓ Reset wallet for {}", email);
    }
    
    println!("\n✅ All wallets have been reset to 0.00 with the new encryption key!");
    println!("Users can now deposit funds using the wallet endpoints.");
    
    Ok(())
}
