/**
 * Admin Authentication Middleware
 * 
 * Provides role-based access control (RBAC) for admin endpoints
 * Verifies JWT token and checks user role
 */

use actix_web::{
    body::BoxBody,
    dev::{forward_ready, Service, ServiceRequest, ServiceResponse, Transform},
    Error, HttpMessage, HttpResponse,
};
use futures_util::future::LocalBoxFuture;
use std::future::{ready, Ready};
use std::rc::Rc;

use crate::auth::AuthService;

// ============================================================================
// ADMIN ROLE MIDDLEWARE
// ============================================================================

/// Middleware factory for requiring admin role
pub struct RequireAdmin {
    auth_service: Rc<AuthService>,
}

impl RequireAdmin {
    pub fn new(auth_service: Rc<AuthService>) -> Self {
        Self { auth_service }
    }
}

impl<S, B> Transform<S, ServiceRequest> for RequireAdmin
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    S::Future: 'static,
    B: actix_web::body::MessageBody + 'static,
{
    type Response = ServiceResponse<BoxBody>;
    type Error = Error;
    type InitError = ();
    type Transform = RequireAdminMiddleware<S>;
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ready(Ok(RequireAdminMiddleware {
            service: Rc::new(service),
            auth_service: self.auth_service.clone(),
        }))
    }
}

pub struct RequireAdminMiddleware<S> {
    service: Rc<S>,
    auth_service: Rc<AuthService>,
}

impl<S, B> Service<ServiceRequest> for RequireAdminMiddleware<S>
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
            let auth_header = req
                .headers()
                .get("Authorization")
                .and_then(|h| h.to_str().ok());

            if let Some(auth_header) = auth_header {
                // Extract token
                if let Some(token) = auth_header.strip_prefix("Bearer ") {
                    // Validate token
                    match auth_service.validate_token(token) {
                        Ok(claims) => {
                            // Check if user has admin or superadmin role
                            if claims.role == "admin" || claims.role == "superadmin" {
                                // Store claims in request extensions for later use
                                req.extensions_mut().insert(claims.clone());
                                
                                // Continue to the actual handler
                                return service.call(req).await.map(|res| res.map_into_boxed_body());
                            } else {
                                // User is not an admin
                                let response = HttpResponse::Forbidden()
                                    .json(serde_json::json!({
                                        "error": "Admin access required"
                                    }));
                                return Ok(req.into_response(response).map_into_boxed_body());
                            }
                        }
                        Err(_) => {
                            // Invalid token
                            let response = HttpResponse::Unauthorized()
                                .json(serde_json::json!({
                                    "error": "Invalid token"
                                }));
                            return Ok(req.into_response(response).map_into_boxed_body());
                        }
                    }
                }
            }

            // No authorization header or invalid format
            let response = HttpResponse::Unauthorized()
                .json(serde_json::json!({
                    "error": "Missing or invalid authorization header"
                }));
            Ok(req.into_response(response).map_into_boxed_body())
        })
    }
}

// ============================================================================
// SUPERADMIN ROLE MIDDLEWARE
// ============================================================================

/// Middleware factory for requiring superadmin role
pub struct RequireSuperAdmin {
    auth_service: Rc<AuthService>,
}

impl RequireSuperAdmin {
    pub fn new(auth_service: Rc<AuthService>) -> Self {
        Self { auth_service }
    }
}

impl<S, B> Transform<S, ServiceRequest> for RequireSuperAdmin
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    S::Future: 'static,
    B: actix_web::body::MessageBody + 'static,
{
    type Response = ServiceResponse<BoxBody>;
    type Error = Error;
    type InitError = ();
    type Transform = RequireSuperAdminMiddleware<S>;
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ready(Ok(RequireSuperAdminMiddleware {
            service: Rc::new(service),
            auth_service: self.auth_service.clone(),
        }))
    }
}

pub struct RequireSuperAdminMiddleware<S> {
    service: Rc<S>,
    auth_service: Rc<AuthService>,
}

impl<S, B> Service<ServiceRequest> for RequireSuperAdminMiddleware<S>
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
            let auth_header = req
                .headers()
                .get("Authorization")
                .and_then(|h| h.to_str().ok());

            if let Some(auth_header) = auth_header {
                // Extract token
                if let Some(token) = auth_header.strip_prefix("Bearer ") {
                    // Validate token
                    match auth_service.validate_token(token) {
                        Ok(claims) => {
                            // Check if user has superadmin role
                            if claims.role == "superadmin" {
                                // Store claims in request extensions
                                req.extensions_mut().insert(claims.clone());
                                
                                // Continue to the actual handler
                                return service.call(req).await.map(|res| res.map_into_boxed_body());
                            } else {
                                // User is not a superadmin
                                let response = HttpResponse::Forbidden()
                                    .json(serde_json::json!({
                                        "error": "Superadmin access required"
                                    }));
                                return Ok(req.into_response(response).map_into_boxed_body());
                            }
                        }
                        Err(_) => {
                            // Invalid token
                            let response = HttpResponse::Unauthorized()
                                .json(serde_json::json!({
                                    "error": "Invalid token"
                                }));
                            return Ok(req.into_response(response).map_into_boxed_body());
                        }
                    }
                }
            }

            // No authorization header or invalid format
            let response = HttpResponse::Unauthorized()
                .json(serde_json::json!({
                    "error": "Missing or invalid authorization header"
                }));
            Ok(req.into_response(response).map_into_boxed_body())
        })
    }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/// Extract admin claims from request extensions
/// Use this in handlers to get the authenticated admin's info
pub fn get_admin_claims(req: &actix_web::HttpRequest) -> Option<crate::models::Claims> {
    req.extensions().get::<crate::models::Claims>().cloned()
}
