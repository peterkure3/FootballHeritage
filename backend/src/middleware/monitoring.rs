use actix_web::{
    body::BoxBody,
    dev::{forward_ready, Service, ServiceRequest, ServiceResponse, Transform},
    Error, HttpResponse,
    web,
};
use futures_util::future::LocalBoxFuture;
use std::future::{ready, Ready};
use std::rc::Rc;

use crate::monitoring::MonitoringService;

/// Middleware that records request/error metrics for observability
pub struct Metrics {
    monitoring: web::Data<MonitoringService>,
}

impl Metrics {
    pub fn new(monitoring: web::Data<MonitoringService>) -> Self {
        Self { monitoring }
    }
}

impl<S, B> Transform<S, ServiceRequest> for Metrics
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    S::Future: 'static,
    B: actix_web::body::MessageBody + 'static,
{
    type Response = ServiceResponse<BoxBody>;
    type Error = Error;
    type InitError = ();
    type Transform = MetricsMiddleware<S>;
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ready(Ok(MetricsMiddleware {
            service: Rc::new(service),
            monitoring: self.monitoring.clone(),
        }))
    }
}

pub struct MetricsMiddleware<S> {
    service: Rc<S>,
    monitoring: web::Data<MonitoringService>,
}

impl<S, B> Service<ServiceRequest> for MetricsMiddleware<S>
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
        let monitoring = self.monitoring.clone();
        monitoring.increment_requests();

        Box::pin(async move {
            match service.call(req).await {
                Ok(res) => {
                    if res.status().is_server_error() {
                        monitoring.increment_errors();
                    }
                    Ok(res.map_into_boxed_body())
                }
                Err(err) => {
                    monitoring.increment_errors();
                    Err(err)
                }
            }
        })
    }
}
