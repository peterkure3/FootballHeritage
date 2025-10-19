#![allow(dead_code)]
use crate::errors::{AppError, AppResult};
use actix_web::HttpRequest;
use chrono::{NaiveDate, Utc};
use validator::ValidationError;

/// Extract IP address from HTTP request
pub fn extract_ip_address(req: &HttpRequest) -> String {
    req.connection_info()
        .realip_remote_addr()
        .unwrap_or("unknown")
        .to_string()
}

/// Extract User-Agent from HTTP request
pub fn extract_user_agent(req: &HttpRequest) -> String {
    req.headers()
        .get("User-Agent")
        .and_then(|h| h.to_str().ok())
        .unwrap_or("unknown")
        .to_string()
}

/// Validate age (must be 21+)
pub fn validate_age(date_of_birth: &NaiveDate) -> AppResult<()> {
    let today = Utc::now().date_naive();
    let age = today.years_since(*date_of_birth).unwrap_or(0);

    if age < 21 {
        return Err(AppError::Validation("Must be 21 years or older to register".to_string()));
    }

    Ok(())
}

/// Validate bet type
pub fn validate_bet_type(bet_type: &str) -> Result<(), ValidationError> {
    match bet_type {
        "moneyline" | "spread" | "total" => Ok(()),
        _ => Err(ValidationError::new("Invalid bet type")),
    }
}

/// Validate bet selection
pub fn validate_selection(selection: &str) -> Result<(), ValidationError> {
    match selection {
        "home" | "away" | "over" | "under" => Ok(()),
        _ => Err(ValidationError::new("Invalid selection")),
    }
}

/// Validate email format (basic)
pub fn validate_email(email: &str) -> AppResult<()> {
    if !email.contains('@') || !email.contains('.') {
        return Err(AppError::Validation("Invalid email format".to_string()));
    }
    Ok(())
}

/// Sanitize string input
pub fn sanitize_string(input: &str) -> String {
    input
        .trim()
        .chars()
        .filter(|c| c.is_alphanumeric() || c.is_whitespace() || *c == '@' || *c == '.' || *c == '-' || *c == '_')
        .collect()
}

/// Generate session ID
pub fn generate_session_id() -> String {
    use rand::{thread_rng, Rng};
    use rand::distributions::Alphanumeric;

    let session_id: String = thread_rng()
        .sample_iter(&Alphanumeric)
        .take(32)
        .map(char::from)
        .collect();

    format!("sess_{}", session_id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::NaiveDate;

    #[test]
    fn test_validate_age_valid() {
        let dob = NaiveDate::from_ymd_opt(1990, 1, 1).unwrap();
        assert!(validate_age(&dob).is_ok());
    }

    #[test]
    fn test_validate_age_invalid() {
        let dob = NaiveDate::from_ymd_opt(2010, 1, 1).unwrap();
        assert!(validate_age(&dob).is_err());
    }

    #[test]
    fn test_validate_bet_type() {
        assert!(validate_bet_type("moneyline").is_ok());
        assert!(validate_bet_type("spread").is_ok());
        assert!(validate_bet_type("total").is_ok());
        assert!(validate_bet_type("invalid").is_err());
    }

    #[test]
    fn test_validate_selection() {
        assert!(validate_selection("home").is_ok());
        assert!(validate_selection("away").is_ok());
        assert!(validate_selection("over").is_ok());
        assert!(validate_selection("under").is_ok());
        assert!(validate_selection("invalid").is_err());
    }

    #[test]
    fn test_sanitize_string() {
        let input = "test@example.com<script>alert('xss')</script>";
        let sanitized = sanitize_string(input);
        assert!(!sanitized.contains("<script>"));
    }
}
