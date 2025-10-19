#![allow(dead_code)]
use crate::config::AppConfig;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use tokio::sync::RwLock;

/// Monitoring service for tracking system metrics
pub struct MonitoringService {
    config: Arc<AppConfig>,
    metrics: Arc<RwLock<SystemMetrics>>,
    request_counter: Arc<AtomicU64>,
    error_counter: Arc<AtomicU64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemMetrics {
    pub total_requests: u64,
    pub total_errors: u64,
    pub total_bets_placed: u64,
    pub total_users_registered: u64,
    pub total_deposits: u64,
    pub total_withdrawals: u64,
    pub uptime_seconds: u64,
    pub last_updated: DateTime<Utc>,
}

impl Default for SystemMetrics {
    fn default() -> Self {
        Self {
            total_requests: 0,
            total_errors: 0,
            total_bets_placed: 0,
            total_users_registered: 0,
            total_deposits: 0,
            total_withdrawals: 0,
            uptime_seconds: 0,
            last_updated: Utc::now(),
        }
    }
}

impl MonitoringService {
    pub fn new(config: &AppConfig) -> Self {
        Self {
            config: Arc::new(config.clone()),
            metrics: Arc::new(RwLock::new(SystemMetrics::default())),
            request_counter: Arc::new(AtomicU64::new(0)),
            error_counter: Arc::new(AtomicU64::new(0)),
        }
    }

    /// Increment request counter
    pub fn increment_requests(&self) {
        self.request_counter.fetch_add(1, Ordering::Relaxed);
    }

    /// Increment error counter
    pub fn increment_errors(&self) {
        self.error_counter.fetch_add(1, Ordering::Relaxed);
    }

    /// Get current metrics
    pub async fn get_metrics(&self) -> SystemMetrics {
        let mut metrics = self.metrics.read().await.clone();
        metrics.total_requests = self.request_counter.load(Ordering::Relaxed);
        metrics.total_errors = self.error_counter.load(Ordering::Relaxed);
        metrics.last_updated = Utc::now();
        metrics
    }

    /// Update bet metrics
    pub async fn record_bet(&self) {
        let mut metrics = self.metrics.write().await;
        metrics.total_bets_placed += 1;
    }

    /// Update user registration metrics
    pub async fn record_registration(&self) {
        let mut metrics = self.metrics.write().await;
        metrics.total_users_registered += 1;
    }

    /// Update deposit metrics
    pub async fn record_deposit(&self) {
        let mut metrics = self.metrics.write().await;
        metrics.total_deposits += 1;
    }

    /// Update withdrawal metrics
    pub async fn record_withdrawal(&self) {
        let mut metrics = self.metrics.write().await;
        metrics.total_withdrawals += 1;
    }

    /// Get health status
    pub fn get_health_status(&self) -> HealthStatus {
        HealthStatus {
            status: "healthy".to_string(),
            timestamp: Utc::now(),
            version: env!("CARGO_PKG_VERSION").to_string(),
        }
    }
}

#[derive(Debug, Serialize)]
pub struct HealthStatus {
    pub status: String,
    pub timestamp: DateTime<Utc>,
    pub version: String,
}
