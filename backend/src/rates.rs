#![allow(dead_code)]
use crate::config::AppConfig;
use crate::errors::{AppError, AppResult};
use dashmap::DashMap;
use governor::{
    clock::{Clock, DefaultClock},
    middleware::NoOpMiddleware,
    state::{InMemoryState, NotKeyed},
    Quota, RateLimiter as GovernorRateLimiter,
};
use std::num::NonZeroU32;
use std::sync::Arc;
use std::time::Duration;
use tracing::{info, warn};
use uuid::Uuid;

/// Rate limiter types for different operations
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RateLimitType {
    Bet,
    Login,
    Register,
    Deposit,
    Withdraw,
    ApiGeneral,
}

/// Rate limiter for a specific operation type
pub struct RateLimiter {
    limiter: Arc<GovernorRateLimiter<NotKeyed, InMemoryState, DefaultClock, NoOpMiddleware>>,
    limit_type: RateLimitType,
    max_requests: u32,
    window_seconds: u64,
}

impl RateLimiter {
    /// Create a new rate limiter with specified quota
    pub fn new(limit_type: RateLimitType, max_requests: u32, window_seconds: u64) -> Self {
        let quota = Quota::with_period(Duration::from_secs(window_seconds))
            .unwrap()
            .allow_burst(NonZeroU32::new(max_requests).unwrap());

        let limiter = Arc::new(GovernorRateLimiter::direct(quota));

        info!(
            "Initialized rate limiter for {:?}: {} requests per {} seconds",
            limit_type, max_requests, window_seconds
        );

        Self {
            limiter,
            limit_type,
            max_requests,
            window_seconds,
        }
    }

    /// Check if a request is allowed
    pub fn check(&self) -> AppResult<()> {
        match self.limiter.check() {
            Ok(_) => Ok(()),
            Err(_) => {
                warn!(
                    "Rate limit exceeded for {:?}: {} requests per {} seconds",
                    self.limit_type, self.max_requests, self.window_seconds
                );
                Err(AppError::RateLimitExceeded(format!(
                    "Rate limit exceeded: {} requests per {} seconds allowed",
                    self.max_requests, self.window_seconds
                )))
            }
        }
    }

    /// Get the current quota information
    pub fn get_quota_info(&self) -> (u32, u64) {
        (self.max_requests, self.window_seconds)
    }
}

/// Per-user rate limiters for tracking individual user activity
pub struct UserRateLimiter {
    user_limiters: DashMap<Uuid, Arc<GovernorRateLimiter<NotKeyed, InMemoryState, DefaultClock, NoOpMiddleware>>>,
    max_requests: u32,
    window_seconds: u64,
    limit_type: RateLimitType,
}

impl UserRateLimiter {
    /// Create a new per-user rate limiter
    pub fn new(limit_type: RateLimitType, max_requests: u32, window_seconds: u64) -> Self {
        info!(
            "Initialized per-user rate limiter for {:?}: {} requests per {} seconds",
            limit_type, max_requests, window_seconds
        );

        Self {
            user_limiters: DashMap::new(),
            max_requests,
            window_seconds,
            limit_type,
        }
    }

    /// Check if a request is allowed for a specific user
    pub fn check(&self, user_id: Uuid) -> AppResult<()> {
        let limiter = self.user_limiters.entry(user_id).or_insert_with(|| {
            let quota = Quota::with_period(Duration::from_secs(self.window_seconds))
                .unwrap()
                .allow_burst(NonZeroU32::new(self.max_requests).unwrap());
            Arc::new(GovernorRateLimiter::direct(quota))
        });

        match limiter.check() {
            Ok(_) => Ok(()),
            Err(_) => {
                warn!(
                    "User {} exceeded rate limit for {:?}: {} requests per {} seconds",
                    user_id, self.limit_type, self.max_requests, self.window_seconds
                );
                Err(AppError::RateLimitExceeded(format!(
                    "Rate limit exceeded: {} requests per {} seconds allowed",
                    self.max_requests, self.window_seconds
                )))
            }
        }
    }

    /// Clean up inactive user limiters (for memory management)
    pub fn cleanup_inactive(&self) {
        let _now = DefaultClock::default().now();
        let _cleanup_threshold = Duration::from_secs(self.window_seconds * 10);

        self.user_limiters.retain(|_, _limiter| {
            // Keep limiters that have been used recently
            // This is a simplified cleanup - in production, you'd track last access time
            true
        });
    }

    /// Get the number of tracked users
    pub fn tracked_users_count(&self) -> usize {
        self.user_limiters.len()
    }
}

/// IP-based rate limiter for preventing abuse from specific IPs
pub struct IpRateLimiter {
    ip_limiters: DashMap<String, Arc<GovernorRateLimiter<NotKeyed, InMemoryState, DefaultClock, NoOpMiddleware>>>,
    max_requests: u32,
    window_seconds: u64,
    limit_type: RateLimitType,
}

impl IpRateLimiter {
    /// Create a new IP-based rate limiter
    pub fn new(limit_type: RateLimitType, max_requests: u32, window_seconds: u64) -> Self {
        info!(
            "Initialized IP-based rate limiter for {:?}: {} requests per {} seconds",
            limit_type, max_requests, window_seconds
        );

        Self {
            ip_limiters: DashMap::new(),
            max_requests,
            window_seconds,
            limit_type,
        }
    }

    /// Check if a request is allowed from a specific IP
    pub fn check(&self, ip_address: &str) -> AppResult<()> {
        let limiter = self.ip_limiters.entry(ip_address.to_string()).or_insert_with(|| {
            let quota = Quota::with_period(Duration::from_secs(self.window_seconds))
                .unwrap()
                .allow_burst(NonZeroU32::new(self.max_requests).unwrap());
            Arc::new(GovernorRateLimiter::direct(quota))
        });

        match limiter.check() {
            Ok(_) => Ok(()),
            Err(_) => {
                warn!(
                    "IP {} exceeded rate limit for {:?}: {} requests per {} seconds",
                    ip_address, self.limit_type, self.max_requests, self.window_seconds
                );
                Err(AppError::RateLimitExceeded(format!(
                    "Rate limit exceeded from your IP: {} requests per {} seconds allowed",
                    self.max_requests, self.window_seconds
                )))
            }
        }
    }

    /// Clean up inactive IP limiters
    pub fn cleanup_inactive(&self) {
        // Simplified cleanup - in production, track last access time
        if self.ip_limiters.len() > 10000 {
            warn!("IP rate limiter cache size exceeded 10000 entries, consider cleanup");
        }
    }

    /// Get the number of tracked IPs
    pub fn tracked_ips_count(&self) -> usize {
        self.ip_limiters.len()
    }
}

/// Main rate limiters container
pub struct RateLimiters {
    // Global rate limiters
    pub bet_limiter: Arc<UserRateLimiter>,
    pub login_limiter: Arc<IpRateLimiter>,
    pub register_limiter: Arc<IpRateLimiter>,
    pub deposit_limiter: Arc<UserRateLimiter>,
    pub withdraw_limiter: Arc<UserRateLimiter>,
    pub api_general_limiter: Arc<IpRateLimiter>,
}

impl RateLimiters {
    /// Create new rate limiters from configuration
    pub fn new(config: &AppConfig) -> Self {
        Self {
            // Bet rate limiter: 5 bets per minute per user (as per requirements)
            bet_limiter: Arc::new(UserRateLimiter::new(
                RateLimitType::Bet,
                config.bet_rate_limit_per_minute,
                60,
            )),

            // Login rate limiter: 10 attempts per minute per IP
            login_limiter: Arc::new(IpRateLimiter::new(
                RateLimitType::Login,
                config.login_rate_limit_per_minute,
                60,
            )),

            // Register rate limiter: 5 registrations per hour per IP
            register_limiter: Arc::new(IpRateLimiter::new(
                RateLimitType::Register,
                config.register_rate_limit_per_hour,
                3600,
            )),

            // Deposit rate limiter: 10 deposits per hour per user
            deposit_limiter: Arc::new(UserRateLimiter::new(
                RateLimitType::Deposit,
                10,
                3600,
            )),

            // Withdraw rate limiter: 5 withdrawals per hour per user
            withdraw_limiter: Arc::new(UserRateLimiter::new(
                RateLimitType::Withdraw,
                5,
                3600,
            )),

            // General API rate limiter: 100 requests per minute per IP
            api_general_limiter: Arc::new(IpRateLimiter::new(
                RateLimitType::ApiGeneral,
                100,
                60,
            )),
        }
    }

    /// Check bet rate limit for a user
    pub fn check_bet_limit(&self, user_id: Uuid) -> AppResult<()> {
        self.bet_limiter.check(user_id)
    }

    /// Check login rate limit for an IP
    pub fn check_login_limit(&self, ip_address: &str) -> AppResult<()> {
        self.login_limiter.check(ip_address)
    }

    /// Check registration rate limit for an IP
    pub fn check_register_limit(&self, ip_address: &str) -> AppResult<()> {
        self.register_limiter.check(ip_address)
    }

    /// Check deposit rate limit for a user
    pub fn check_deposit_limit(&self, user_id: Uuid) -> AppResult<()> {
        self.deposit_limiter.check(user_id)
    }

    /// Check withdrawal rate limit for a user
    pub fn check_withdraw_limit(&self, user_id: Uuid) -> AppResult<()> {
        self.withdraw_limiter.check(user_id)
    }

    /// Check general API rate limit for an IP
    pub fn check_api_limit(&self, ip_address: &str) -> AppResult<()> {
        self.api_general_limiter.check(ip_address)
    }

    /// Cleanup inactive limiters (should be called periodically)
    pub fn cleanup_all(&self) {
        self.bet_limiter.cleanup_inactive();
        self.deposit_limiter.cleanup_inactive();
        self.withdraw_limiter.cleanup_inactive();
        self.login_limiter.cleanup_inactive();
        self.register_limiter.cleanup_inactive();
        self.api_general_limiter.cleanup_inactive();
    }

    /// Get statistics about tracked entities
    pub fn get_stats(&self) -> RateLimiterStats {
        RateLimiterStats {
            tracked_bet_users: self.bet_limiter.tracked_users_count(),
            tracked_deposit_users: self.deposit_limiter.tracked_users_count(),
            tracked_withdraw_users: self.withdraw_limiter.tracked_users_count(),
            tracked_login_ips: self.login_limiter.tracked_ips_count(),
            tracked_register_ips: self.register_limiter.tracked_ips_count(),
            tracked_api_ips: self.api_general_limiter.tracked_ips_count(),
        }
    }
}

/// Statistics about rate limiters
#[derive(Debug, Clone)]
pub struct RateLimiterStats {
    pub tracked_bet_users: usize,
    pub tracked_deposit_users: usize,
    pub tracked_withdraw_users: usize,
    pub tracked_login_ips: usize,
    pub tracked_register_ips: usize,
    pub tracked_api_ips: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rate_limiter_allows_within_quota() {
        let limiter = RateLimiter::new(RateLimitType::Bet, 5, 60);

        // Should allow first 5 requests
        for _ in 0..5 {
            assert!(limiter.check().is_ok());
        }
    }

    #[test]
    fn test_rate_limiter_blocks_over_quota() {
        let limiter = RateLimiter::new(RateLimitType::Bet, 2, 60);

        // Allow first 2 requests
        assert!(limiter.check().is_ok());
        assert!(limiter.check().is_ok());

        // Third request should be blocked
        assert!(limiter.check().is_err());
    }

    #[test]
    fn test_user_rate_limiter() {
        let limiter = UserRateLimiter::new(RateLimitType::Bet, 3, 60);
        let user1 = Uuid::new_v4();
        let user2 = Uuid::new_v4();

        // User 1 can make 3 requests
        assert!(limiter.check(user1).is_ok());
        assert!(limiter.check(user1).is_ok());
        assert!(limiter.check(user1).is_ok());
        assert!(limiter.check(user1).is_err());

        // User 2 should have independent quota
        assert!(limiter.check(user2).is_ok());
        assert!(limiter.check(user2).is_ok());
    }

    #[test]
    fn test_ip_rate_limiter() {
        let limiter = IpRateLimiter::new(RateLimitType::Login, 2, 60);
        let ip1 = "192.168.1.1";
        let ip2 = "192.168.1.2";

        // IP 1 can make 2 requests
        assert!(limiter.check(ip1).is_ok());
        assert!(limiter.check(ip1).is_ok());
        assert!(limiter.check(ip1).is_err());

        // IP 2 should have independent quota
        assert!(limiter.check(ip2).is_ok());
    }
}
