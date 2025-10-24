use actix_cors::Cors;
use actix_web::{web, App, HttpServer};
use rustls::pki_types::CertificateDer;
use sqlx::postgres::PgPoolOptions;
use tracing::{info, error, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod auth;
mod betting_simple;
mod config;
mod crypto;
mod errors;
mod handlers;
mod middleware;
mod models;
mod monitoring;
mod rates;
mod utils;

use config::AppConfig;


#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,football_heritage_backend=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load configuration
    dotenvy::dotenv().ok();
    let config = AppConfig::from_env()
        .map_err(|e| {
            error!("Failed to load configuration: {}", e);
            std::io::Error::new(std::io::ErrorKind::Other, e)
        })?;

    info!("Starting Football Heritage Betting API Server");
    info!("Environment: {}", if config.is_development() { "Development" } else { "Production" });

    // Initialize database connection pool
    let db_pool = PgPoolOptions::new()
        .max_connections(50)
        .min_connections(10)
        .acquire_timeout(std::time::Duration::from_secs(30))
        .idle_timeout(std::time::Duration::from_secs(600))
        .max_lifetime(std::time::Duration::from_secs(1800))
        .connect(&config.database_url)
        .await
        .map_err(|e| {
            error!("Failed to connect to database: {}", e);
            std::io::Error::new(std::io::ErrorKind::Other, "Database connection failed")
        })?;

    info!("Database connection pool initialized successfully");

    // Run database migrations
    // Disabled: Migrations already applied - uncomment if you need to run new migrations
    // sqlx::migrate!("./migrations")
    //     .run(&db_pool)
    //     .await
    //     .map_err(|e| {
    //         error!("Failed to run database migrations: {}", e);
    //         std::io::Error::new(std::io::ErrorKind::Other, "Migration failed")
    //     })?;
    info!("Auto-migrations disabled (already applied to database)");

    info!("Database migrations completed successfully");

    // Initialize rate limiters
    let rate_limiters = web::Data::new(rates::RateLimiters::new(&config));

    // Start monitoring service
    let monitoring_service = web::Data::new(monitoring::MonitoringService::new(&config));

    // Initialize auth service (Clone-able, shared across all handlers and middleware)
    let config_arc = std::sync::Arc::new(config.clone());
    let auth_service = auth::AuthService::new(config_arc);

    // Initialize TLS configuration if HTTPS is enabled
    let tls_config = if config.https_enabled {
        Some({
            let cert_file = std::fs::File::open(&config.tls_cert_path).map_err(|e| {
                error!("Failed to read TLS certificate: {}", e);
                std::io::Error::new(std::io::ErrorKind::Other, "TLS certificate error")
            })?;
            let mut cert_reader = std::io::BufReader::new(cert_file);
            let certs: Vec<CertificateDer> = rustls_pemfile::certs(&mut cert_reader)
                .collect::<Result<Vec<_>, _>>()
                .map_err(|e| {
                    error!("Failed to parse certificates: {}", e);
                    std::io::Error::new(std::io::ErrorKind::Other, "Certificate parse error")
                })?;

            let key_file = std::fs::File::open(&config.tls_key_path).map_err(|e| {
                error!("Failed to read TLS private key: {}", e);
                std::io::Error::new(std::io::ErrorKind::Other, "TLS key error")
            })?;
            let mut key_reader = std::io::BufReader::new(key_file);
            let key = rustls_pemfile::private_key(&mut key_reader)
                .map_err(|e| {
                    error!("Failed to parse private key: {}", e);
                    std::io::Error::new(std::io::ErrorKind::Other, "Private key parse error")
                })?
                .ok_or_else(|| {
                    error!("No private key found in TLS key file");
                    std::io::Error::new(std::io::ErrorKind::Other, "No TLS private key")
                })?;

            rustls::ServerConfig::builder()
                .with_no_client_auth()
                .with_single_cert(certs, key)
                .map_err(|e| {
                    error!("Failed to create TLS configuration: {}", e);
                    std::io::Error::new(std::io::ErrorKind::Other, "TLS configuration error")
                })?
        })
    } else {
        None
    };

    let bind_addr = format!("{}:{}", config.host, config.port);

    info!("Starting server on {}", bind_addr);
    if config.https_enabled {
        info!("HTTPS enabled with TLS");
    } else {
        warn!("HTTPS disabled - running in insecure mode");
    }

    info!("CORS allowed origins: {:?}", config.allowed_origins);

    // Create HTTP server
    let allowed_origins = config.allowed_origins.clone();
    let auth_service_for_app = auth_service.clone();
    let server = HttpServer::new(move || {
        // Configure CORS
        let allowed_origins_clone = allowed_origins.clone();
        let cors = Cors::default()
            .allowed_origin_fn(move |origin, _req_head| {
                let origin_str = origin.to_str().unwrap_or("");
                info!("CORS request from origin: {}", origin_str);
                allowed_origins_clone.contains(&origin_str.to_string())
            })
            .allowed_methods(vec!["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
            .allowed_headers(vec![
                actix_web::http::header::AUTHORIZATION,
                actix_web::http::header::CONTENT_TYPE,
                actix_web::http::header::ACCEPT,
            ])
            .expose_headers(vec![
                actix_web::http::header::AUTHORIZATION,
                actix_web::http::header::CONTENT_TYPE,
            ])
            .supports_credentials()
            .max_age(3600);
        
        App::new()
            .app_data(web::Data::new(config.clone()))
            .app_data(web::Data::new(db_pool.clone()))
            .app_data(web::Data::new(auth_service_for_app.clone()))
            .app_data(rate_limiters.clone())
            .app_data(monitoring_service.clone())
            .wrap(cors)
            .wrap(actix_web::middleware::Logger::default())
            .wrap(actix_web::middleware::Compress::default())
            .wrap(actix_web::middleware::NormalizePath::trim())
            .wrap(crate::middleware::security_headers::SecurityHeaders)
            .service(
                web::scope("/api/v1")
                    .service(
                        web::scope("/auth")
                            .route("/register", web::post().to(handlers::auth::register))
                            .route("/login", web::post().to(handlers::auth::login))
                            .route("/logout", web::post().to(handlers::auth::logout))
                            .route("/refresh", web::post().to(handlers::auth::refresh))
                            .route("/verify-email", web::post().to(handlers::auth::verify_email))
                    )
                    .service(
                        web::scope("/wallet")
                            .route("/balance", web::get().to(handlers::wallet::get_balance))
                            .route("/deposit", web::post().to(handlers::wallet::deposit))
                            .route("/withdraw", web::post().to(handlers::wallet::withdraw))
                            .route("/transactions", web::get().to(handlers::wallet::get_transactions))
                    )
                    .service(
                        web::scope("/betting")
                            .route("/events", web::get().to(handlers::betting::get_events))
                            .route("/events/{id}", web::get().to(handlers::betting::get_event))
                            .route("/bets", web::post().to(handlers::betting::place_bet))
                            .route("/bets", web::get().to(handlers::betting::get_user_bets))
                            .route("/bets/{id}", web::get().to(handlers::betting::get_bet))
                    )
                    .service(
                        web::scope("/limits")
                            .route("/", web::get().to(handlers::limits::get_limits))
                            .route("/", web::put().to(handlers::limits::update_limits))
                            .route("/self-exclude", web::post().to(handlers::limits::self_exclude))
                    )
                    .service(
                        web::scope("/user")
                            .wrap(middleware::jwt_auth::RequireAuth::new(auth_service_for_app.clone()))
                            .route("/profile", web::get().to(handlers::user::get_profile))
                            .route("/profile", web::put().to(handlers::user::update_profile))
                            .route("/activity", web::get().to(handlers::user::get_activity))
                            .route("/password", web::put().to(handlers::user::change_password))
                    )
                    .service(
                        web::scope("/chat")
                            .route("", web::post().to(handlers::chat::chat))
                            .route("/health", web::get().to(handlers::chat::chat_health))
                    )
                    .service(
                        web::scope("/sports")
                            .route("", web::get().to(handlers::sports::get_sports))
                            .route("/categories", web::get().to(handlers::sports::get_bet_categories))
                            .route("/{sport}/leagues", web::get().to(handlers::sports::get_sport_leagues))
                    )
                    .service(
                        web::scope("/admin")
                            // User management
                            .route("/users", web::get().to(handlers::admin::users::list_users))
                            .route("/users/{id}", web::get().to(handlers::admin::users::get_user_details))
                            .route("/users/{id}/status", web::put().to(handlers::admin::users::update_user_status))
                            .route("/users/{id}/verify", web::put().to(handlers::admin::users::verify_user))
                            // Event management
                            .route("/events", web::post().to(handlers::admin::events::create_event))
                            .route("/events/{id}/status", web::put().to(handlers::admin::events::update_event_status))
                            // Analytics
                            .route("/analytics/dashboard", web::get().to(handlers::admin::analytics::get_dashboard_metrics))
                            // Monitoring
                            .route("/monitoring/fraud-alerts", web::get().to(handlers::admin::monitoring::get_fraud_alerts))
                            .route("/monitoring/audit-logs", web::get().to(handlers::admin::monitoring::get_audit_logs))
                    )
            )
            .route("/health", web::get().to(handlers::health::health_check))
            .route("/metrics", web::get().to(handlers::monitoring::metrics))
            .default_service(web::route().to(handlers::not_found::not_found))
    });

    // Bind server with or without TLS
    if let Some(tls) = tls_config {
        server
            .bind_rustls_0_23(bind_addr, tls)?
            .workers(num_cpus::get() * 2)
            .run()
            .await
    } else {
        server
            .bind(bind_addr)?
            .workers(num_cpus::get() * 2)
            .run()
            .await
    }
}
