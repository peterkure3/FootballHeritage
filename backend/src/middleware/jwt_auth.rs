use actix_web::{
    body::BoxBody,
    dev::{forward_ready, Service, ServiceRequest, ServiceResponse, Transform},
    Error, HttpMessage, HttpResponse,
};
use futures_util::future::LocalBoxFuture;
use std::future::{ready, Ready};
use std::sync::Arc;
use crate::auth::AuthService;
use crate::models::Claims;

/// Middleware to require JWT authentication for protected routes
pub struct RequireAuth {
    auth_service: AuthService,
}

impl RequireAuth {
    pub fn new(auth_service: AuthService) -> Self {
        Self { auth_service }
    }
}

impl<S, B> Transform<S, ServiceRequest> for RequireAuth
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    S::Future: 'static,
    B: actix_web::body::MessageBody + 'static,
{
    type Response = ServiceResponse<BoxBody>;
    type Error = Error;
    type InitError = ();
    type Transform = RequireAuthMiddleware<S>;
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ready(Ok(RequireAuthMiddleware {
            service: Arc::new(service),
            auth_service: self.auth_service.clone(),
        }))
    }
}

pub struct RequireAuthMiddleware<S> {
    service: Arc<S>,
    auth_service: AuthService,
}

impl<S, B> Service<ServiceRequest> for RequireAuthMiddleware<S>
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    S::Future: 'static,
    B: actix_web::body::MessageBody + 'static,
{
    type Response = ServiceResponse<BoxBody>;
    type Error = Error;
    type Future = LocalBoxFuture<'static, Result<Self::Response, Self::Error>>;

    forward_ready!(service);

    fn call(&self, req: ServiceRequest) -> Self::Future {
        let service = self.service.clone();
        let auth_service = self.auth_service.clone();

        Box::pin(async move {
            // Extract Authorization header
            if let Some(auth_header) = req.headers().get("Authorization") {
                if let Ok(auth_str) = auth_header.to_str() {
                    // Check if it's a Bearer token
                    if auth_str.starts_with("Bearer ") {
                        let token = &auth_str[7..]; // Remove "Bearer " prefix

                        // Validate token
                        match auth_service.validate_token(token) {
                            Ok(claims) => {
                                // Store claims in request extensions for handlers to use
                                req.extensions_mut().insert(claims);

                                // Continue to the actual handler
                                return service.call(req).await.map(|res| res.map_into_boxed_body());
                            }
                            Err(_) => {
                                // Invalid token
                                let response = HttpResponse::Unauthorized()
                                    .json(serde_json::json!({
                                        "error": "Invalid or expired token"
                                    }));
                                return Ok(req.into_response(response).map_into_boxed_body());
                            }
                        }
                    }
                }
            }

            // No valid authorization header
            let response = HttpResponse::Unauthorized()
                .json(serde_json::json!({
                    "error": "Missing or invalid authorization header"
                }));
            Ok(req.into_response(response).map_into_boxed_body())
        })
    }
}

/// Helper function to extract claims from request extensions
/// Use this in handlers to get the authenticated user's info
pub fn get_claims(req: &actix_web::HttpRequest) -> Option<Claims> {
    req.extensions().get::<Claims>().cloned()
}
