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

fn read_line(prompt: &str) -> String {
    print!("{}", prompt);
    io::stdout().flush().unwrap();
    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();
    input.trim().to_string()
}

fn read_password(prompt: &str) -> String {
    print!("{}", prompt);
    io::stdout().flush().unwrap();
    
    // For Windows, we'll use a simple approach
    // In production, consider using rpassword crate for hidden input
    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();
    input.trim().to_string()
}

fn validate_email(email: &str) -> bool {
    email.contains('@') && email.contains('.') && email.len() >= 5
}

fn validate_password(password: &str) -> Result<(), String> {
    if password.len() < 8 {
        return Err("Password must be at least 8 characters".to_string());
    }
    if !password.chars().any(|c| c.is_uppercase()) {
        return Err("Password must contain at least one uppercase letter".to_string());
    }
    if !password.chars().any(|c| c.is_lowercase()) {
        return Err("Password must contain at least one lowercase letter".to_string());
    }
    if !password.chars().any(|c| c.is_numeric()) {
        return Err("Password must contain at least one number".to_string());
    }
    if !password.chars().any(|c| !c.is_alphanumeric()) {
        return Err("Password must contain at least one special character".to_string());
    }
    Ok(())
}

fn validate_date(date: &str) -> bool {
    // Simple YYYY-MM-DD validation
    if date.len() != 10 {
        return false;
    }
    let parts: Vec<&str> = date.split('-').collect();
    if parts.len() != 3 {
        return false;
    }
    let year: Result<i32, _> = parts[0].parse();
    let month: Result<u32, _> = parts[1].parse();
    let day: Result<u32, _> = parts[2].parse();
    
    match (year, month, day) {
        (Ok(y), Ok(m), Ok(d)) => {
            y >= 1900 && y <= 2010 && m >= 1 && m <= 12 && d >= 1 && d <= 31
        }
        _ => false
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenv().ok();
    
    println!("\n╔════════════════════════════════════════════════════════════╗");
    println!("║       Football Heritage - Admin Account Initialization      ║");
    println!("╚════════════════════════════════════════════════════════════╝\n");
    
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
    
    println!("─────────────────────────────────────────────────────────────");
    println!("                    Enter Admin Details                       ");
    println!("─────────────────────────────────────────────────────────────\n");
    
    // Collect admin details
    let email = loop {
        let input = read_line("Email: ");
        if validate_email(&input) {
            // Check if email already exists
            let exists: Option<(i64,)> = sqlx::query_as(
                "SELECT COUNT(*) FROM users WHERE email = $1"
            )
            .bind(&input)
            .fetch_optional(&pool)
            .await?;
            
            if let Some((count,)) = exists {
                if count > 0 {
                    println!("  ⚠️  Email already exists in database. Use a different email.\n");
                    continue;
                }
            }
            break input;
        } else {
            println!("  ⚠️  Invalid email format. Please try again.\n");
        }
    };
    
    let first_name = loop {
        let input = read_line("First Name: ");
        if !input.is_empty() && input.len() <= 100 {
            break input;
        } else {
            println!("  ⚠️  First name is required (max 100 characters).\n");
        }
    };
    
    let last_name = loop {
        let input = read_line("Last Name: ");
        if !input.is_empty() && input.len() <= 100 {
            break input;
        } else {
            println!("  ⚠️  Last name is required (max 100 characters).\n");
        }
    };
    
    let date_of_birth = loop {
        let input = read_line("Date of Birth (YYYY-MM-DD): ");
        if validate_date(&input) {
            break input;
        } else {
            println!("  ⚠️  Invalid date format. Use YYYY-MM-DD (must be 21+ years old).\n");
        }
    };
    
    let phone = read_line("Phone (optional): ");
    let phone = if phone.is_empty() { None } else { Some(phone) };
    
    let address = read_line("Address (optional): ");
    let address = if address.is_empty() { None } else { Some(address) };
    
    println!("\n─────────────────────────────────────────────────────────────");
    println!("                    Set Admin Password                        ");
    println!("─────────────────────────────────────────────────────────────");
    println!("Requirements:");
    println!("  • At least 8 characters");
    println!("  • At least one uppercase letter");
    println!("  • At least one lowercase letter");
    println!("  • At least one number");
    println!("  • At least one special character\n");
    
    let password = loop {
        let input = read_password("Password: ");
        match validate_password(&input) {
            Ok(()) => {
                let confirm = read_password("Confirm Password: ");
                if input == confirm {
                    break input;
                } else {
                    println!("  ⚠️  Passwords do not match. Please try again.\n");
                }
            }
            Err(e) => {
                println!("  ⚠️  {}\n", e);
            }
        }
    };
    
    // Select role
    println!("\n─────────────────────────────────────────────────────────────");
    println!("                    Select Admin Role                         ");
    println!("─────────────────────────────────────────────────────────────");
    println!("1. admin      - Can manage users, events, and view reports");
    println!("2. superadmin - Full access including system configuration\n");
    
    let role = loop {
        let input = read_line("Select role (1 or 2): ");
        match input.as_str() {
            "1" => break "admin".to_string(),
            "2" => break "superadmin".to_string(),
            _ => println!("  ⚠️  Invalid selection. Enter 1 or 2.\n"),
        }
    };
    
    // Confirm details
    println!("\n─────────────────────────────────────────────────────────────");
    println!("                    Confirm Admin Details                     ");
    println!("─────────────────────────────────────────────────────────────");
    println!("  Email:         {}", email);
    println!("  Name:          {} {}", first_name, last_name);
    println!("  Date of Birth: {}", date_of_birth);
    println!("  Phone:         {}", phone.as_deref().unwrap_or("(not set)"));
    println!("  Address:       {}", address.as_deref().unwrap_or("(not set)"));
    println!("  Role:          {}", role);
    println!("─────────────────────────────────────────────────────────────\n");
    
    let confirm = read_line("Create this admin account? (yes/no): ");
    if confirm.to_lowercase() != "yes" && confirm.to_lowercase() != "y" {
        println!("\n❌ Admin creation cancelled.");
        return Ok(());
    }
    
    println!("\n⏳ Creating admin account...");
    
    // Hash password
    let password_hash = crypto_service.hash_password(&password)
        .map_err(|e| anyhow::anyhow!("Password hashing failed: {}", e))?;
    println!("  ✓ Password hashed");
    
    // Create user
    let user_id: (uuid::Uuid,) = sqlx::query_as(
        r#"
        INSERT INTO users (
            email, password_hash, first_name, last_name, date_of_birth,
            phone, address, role, is_verified, is_active, created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5::date, $6, $7, $8, true, true, NOW(), NOW())
        RETURNING id
        "#
    )
    .bind(&email)
    .bind(&password_hash)
    .bind(&first_name)
    .bind(&last_name)
    .bind(&date_of_birth)
    .bind(&phone)
    .bind(&address)
    .bind(&role)
    .fetch_one(&pool)
    .await?;
    
    println!("  ✓ Admin user created (ID: {})", user_id.0);
    
    // Create wallet with 0 balance
    let initial_balance = BigDecimal::from_str("0.00")?;
    let (encrypted_balance, iv) = crypto_service.encrypt_balance(&initial_balance)
        .map_err(|e| anyhow::anyhow!("Encryption failed: {}", e))?;
    
    sqlx::query(
        r#"
        INSERT INTO wallets (id, user_id, encrypted_balance, encryption_iv, created_at, updated_at)
        VALUES (gen_random_uuid(), $1, $2, $3, NOW(), NOW())
        "#
    )
    .bind(user_id.0)
    .bind(&encrypted_balance)
    .bind(&iv)
    .execute(&pool)
    .await?;
    
    println!("  ✓ Wallet created");
    
    // Create gambling limits with defaults
    sqlx::query(
        r#"
        INSERT INTO gambling_limits (
            user_id, daily_loss_limit, weekly_loss_limit, monthly_loss_limit,
            daily_bet_limit, weekly_bet_limit, monthly_bet_limit, max_single_bet,
            created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
        "#
    )
    .bind(user_id.0)
    .bind(config.default_daily_loss_limit)
    .bind(config.default_weekly_loss_limit)
    .bind(config.default_monthly_loss_limit)
    .bind(config.default_daily_bet_limit)
    .bind(config.default_weekly_bet_limit)
    .bind(config.default_monthly_bet_limit)
    .bind(config.default_max_single_bet)
    .execute(&pool)
    .await?;
    
    println!("  ✓ Gambling limits configured");
    
    println!("\n╔════════════════════════════════════════════════════════════╗");
    println!("║              ✅ Admin Account Created Successfully!         ║");
    println!("╚════════════════════════════════════════════════════════════╝");
    println!("\n  Email: {}", email);
    println!("  Role:  {}", role);
    println!("\n  You can now log in to the admin panel with these credentials.");
    println!("  ⚠️  Keep your password secure and do not share it!\n");
    
    Ok(())
}
