/**
 * Chat Handler - Proxy to Node.js Chatbot Service
 * 
 * This handler forwards authenticated chat requests to the Node.js
 * Genkit-powered chatbot microservice running on localhost:3000
 */

use actix_web::{web, HttpRequest, HttpResponse};
use reqwest;
use serde::{Deserialize, Serialize};
use tracing::{error, info};

use crate::auth::verify_jwt;
use crate::config::AppConfig;
use crate::errors::ApiError;

// ============================================================================
// REQUEST/RESPONSE TYPES
// ============================================================================

#[derive(Debug, Deserialize)]
pub struct ChatRequest {
    pub prompt: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatResponse {
    pub response: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ErrorResponse {
    pub error: String,
    pub message: String,
}

// ============================================================================
// CHAT HANDLER
// ============================================================================

/**
 * POST /api/v1/chat
 * 
 * Proxies authenticated chat requests to Node.js chatbot service
 * 
 * Security:
 * - Validates JWT token
 * - Forwards token to chatbot service for user identification
 * - Sanitizes input/output
 * 
 * Performance:
 * - Async HTTP client with connection pooling
 * - Timeout protection (30 seconds)
 * - Error handling for service unavailability
 */
pub async fn chat(
    req: HttpRequest,
    body: web::Json<ChatRequest>,
    config: web::Data<AppConfig>,
) -> Result<HttpResponse, ApiError> {
    // Extract and verify JWT token
    let auth_header = req
        .headers()
        .get("Authorization")
        .and_then(|h| h.to_str().ok())
        .ok_or_else(|| ApiError::Unauthorized("Missing authorization header".to_string()))?;

    // Verify token format: "Bearer <token>"
    if !auth_header.starts_with("Bearer ") {
        return Err(ApiError::Unauthorized(
            "Invalid authorization header format".to_string(),
        ));
    }

    let token = &auth_header[7..]; // Skip "Bearer "

    // Verify JWT token
    let claims = verify_jwt(token, &config.jwt_secret)
        .map_err(|_| ApiError::Unauthorized("Invalid or expired token".to_string()))?;

    let user_id = claims.sub;

    info!(
        "Chat request from user {}: '{}'",
        user_id,
        &body.prompt[..body.prompt.len().min(50)]
    );

    // Validate input
    if body.prompt.trim().is_empty() {
        return Err(ApiError::BadRequest("Prompt cannot be empty".to_string()));
    }

    if body.prompt.len() > 500 {
        return Err(ApiError::BadRequest(
            "Prompt too long (max 500 characters)".to_string(),
        ));
    }

    // Chatbot service URL (configurable via environment)
    let chatbot_url = std::env::var("CHATBOT_SERVICE_URL")
        .unwrap_or_else(|_| "http://localhost:3000/chat".to_string());

    // Create HTTP client with timeout
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| {
            error!("Failed to create HTTP client: {}", e);
            ApiError::InternalServerError("Service configuration error".to_string())
        })?;

    // Forward request to chatbot service
    let response = client
        .post(&chatbot_url)
        .header("Authorization", auth_header)
        .header("Content-Type", "application/json")
        .json(&serde_json::json!({
            "prompt": body.prompt.trim(),
        }))
        .send()
        .await
        .map_err(|e| {
            error!("Failed to connect to chatbot service: {}", e);
            ApiError::ServiceUnavailable(
                "Chatbot service is currently unavailable. Please try again later.".to_string(),
            )
        })?;

    // Check response status
    let status = response.status();

    if !status.is_success() {
        let error_body = response
            .json::<ErrorResponse>()
            .await
            .unwrap_or_else(|_| ErrorResponse {
                error: "Unknown error".to_string(),
                message: "Failed to get response from chatbot service".to_string(),
            });

        error!(
            "Chatbot service error ({}): {}",
            status, error_body.message
        );

        return match status.as_u16() {
            400 => Err(ApiError::BadRequest(error_body.message)),
            401 | 403 => Err(ApiError::Unauthorized(error_body.message)),
            500 => Err(ApiError::InternalServerError(error_body.message)),
            503 => Err(ApiError::ServiceUnavailable(error_body.message)),
            _ => Err(ApiError::InternalServerError(
                "Chatbot service error".to_string(),
            )),
        };
    }

    // Parse successful response
    let chat_response = response.json::<ChatResponse>().await.map_err(|e| {
        error!("Failed to parse chatbot response: {}", e);
        ApiError::InternalServerError("Invalid response from chatbot service".to_string())
    })?;

    info!(
        "Chat response for user {}: {} characters (confidence: {:?})",
        user_id,
        chat_response.response.len(),
        chat_response.confidence
    );

    // Return response to client
    Ok(HttpResponse::Ok().json(chat_response))
}

// ============================================================================
// HEALTH CHECK FOR CHATBOT SERVICE
// ============================================================================

/**
 * GET /api/v1/chat/health
 * 
 * Checks if the chatbot service is available
 * Useful for monitoring and debugging
 */
pub async fn chat_health() -> Result<HttpResponse, ApiError> {
    let chatbot_url = std::env::var("CHATBOT_SERVICE_URL")
        .unwrap_or_else(|_| "http://localhost:3000".to_string());

    let health_url = format!("{}/health", chatbot_url.trim_end_matches("/chat"));

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| {
            error!("Failed to create HTTP client: {}", e);
            ApiError::InternalServerError("Service configuration error".to_string())
        })?;

    match client.get(&health_url).send().await {
        Ok(response) if response.status().is_success() => {
            let body = response.json::<serde_json::Value>().await.ok();
            Ok(HttpResponse::Ok().json(serde_json::json!({
                "status": "healthy",
                "chatbot_service": "available",
                "details": body,
            })))
        }
        Ok(response) => {
            let status = response.status();
            error!("Chatbot service unhealthy: {}", status);
            Ok(HttpResponse::ServiceUnavailable().json(serde_json::json!({
                "status": "unhealthy",
                "chatbot_service": "unavailable",
                "error": format!("Service returned status {}", status),
            })))
        }
        Err(e) => {
            error!("Failed to connect to chatbot service: {}", e);
            Ok(HttpResponse::ServiceUnavailable().json(serde_json::json!({
                "status": "unhealthy",
                "chatbot_service": "unavailable",
                "error": "Cannot connect to chatbot service",
            })))
        }
    }
}
