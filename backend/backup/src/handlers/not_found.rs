use actix_web::{HttpRequest, HttpResponse};
use serde_json::json;

pub async fn not_found(_req: HttpRequest) -> HttpResponse {
    HttpResponse::NotFound().json(json!({
        "error": "Not Found",
        "message": "The requested resource was not found"
    }))
}
