#![allow(dead_code)]
use actix_web::{
    dev::{forward_ready, Service, ServiceRequest, ServiceResponse, Transform},
    Error, HttpResponse,
    body::BoxBody,
};
use futures_util::future::LocalBoxFuture;
use std::future::{ready, Ready};
use std::rc::Rc;

/// Middleware for rate limiting requests
pub struct RateLimitMiddleware {
    // Configuration can be added here if needed
}

impl RateLimitMiddleware {
    pub fn new() -> Self {
        Self {}
    }
}

impl<S, B> Transform<S, ServiceRequest> for RateLimitMiddleware
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    S::Future: 'static,
    B: actix_web::body::MessageBody + 'static,
{
    type Response = ServiceResponse<BoxBody>;
    type Error = Error;
    type InitError = ();
    type Transform = RateLimitMiddlewareService<S>;
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ready(Ok(RateLimitMiddlewareService {
            service: Rc::new(service),
        }))
    }
}

pub struct RateLimitMiddlewareService<S> {
    service: Rc<S>,
}

impl<S, B> Service<ServiceRequest> for RateLimitMiddlewareService<S>
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

        Box::pin(async move {
            // Extract IP address from request
            let ip_address = req
                .connection_info()
                .realip_remote_addr()
                .unwrap_or("unknown")
                .to_string();

            // Get rate limiters from app data
            if let Some(rate_limiters) = req.app_data::<actix_web::web::Data<crate::rates::RateLimiters>>() {
                // Check general API rate limit
                if let Err(e) = rate_limiters.check_api_limit(&ip_address) {
                    let response = HttpResponse::TooManyRequests()
                        .json(serde_json::json!({
                            "error": "Rate limit exceeded",
                            "message": e.to_string()
                        }));
                    return Ok(req.into_response(response).map_into_boxed_body());
                }
            }

            // Continue with the request
            service.call(req).await.map(|res| res.map_into_boxed_body())
        })
    }
}
