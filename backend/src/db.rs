/**
 * Database Connection Manager
 * 
 * Manages connections to multiple databases:
 * - Primary DB: User accounts, bets, transactions, wallets
 * - Sports DB: Events, odds, sports data (can be external/shared)
 */

use sqlx::postgres::PgPoolOptions;
use sqlx::PgPool;
use std::time::Duration;

/// Database pools container
#[derive(Clone)]
pub struct DatabasePools {
    /// Primary database for user data, bets, transactions
    pub primary: PgPool,
    /// Sports database for events, odds, leagues
    pub sports: PgPool,
}

impl DatabasePools {
    /// Create new database pools from URLs
    pub async fn new(primary_url: &str, sports_url: &str) -> Result<Self, sqlx::Error> {
        // Primary database pool
        let primary = PgPoolOptions::new()
            .max_connections(50)
            .min_connections(10)
            .acquire_timeout(Duration::from_secs(30))
            .idle_timeout(Duration::from_secs(600))
            .max_lifetime(Duration::from_secs(1800))
            .connect(primary_url)
            .await?;

        // Sports database pool (can be same or different database)
        let sports = if primary_url == sports_url {
            // If same URL, reuse the same pool
            primary.clone()
        } else {
            // Different database - create separate pool
            PgPoolOptions::new()
                .max_connections(30)
                .min_connections(5)
                .acquire_timeout(Duration::from_secs(30))
                .idle_timeout(Duration::from_secs(600))
                .max_lifetime(Duration::from_secs(1800))
                .connect(sports_url)
                .await?
        };

        Ok(Self { primary, sports })
    }

    /// Get primary database pool
    pub fn primary(&self) -> &PgPool {
        &self.primary
    }

    /// Get sports database pool
    pub fn sports(&self) -> &PgPool {
        &self.sports
    }
}
