use crate::{auth::AuthService, config::AppConfig, errors::AppError, models::User};
use actix_web::{test, web, App, HttpResponse};
use futures_util::FutureExt;
use serde_json::json;
use sqlx::{postgres::PgPoolOptions, PgPool};
use std::sync::Arc;
use uuid::Uuid;

fn config() -> Arc<AppConfig> {
    Arc::new(serde_json::from_value(json!({
        "app_env":"test","database_url":"unused","jwt_secret":"session-tests-signing-key-at-least-32-bytes",
        "jwt_expiration_hours":24,"encryption_key":"01234567890123456789012345678901",
        "host":"127.0.0.1","port":0,"https_enabled":false,"tls_cert_path":"","tls_key_path":"",
        "bet_rate_limit_per_minute":100,"login_rate_limit_per_minute":100,"register_rate_limit_per_hour":100,
        "bcrypt_cost":4,"session_timeout_minutes":30,"max_login_attempts":5,"account_lock_minutes":15,
        "default_daily_loss_limit":1000.0,"default_weekly_loss_limit":5000.0,"default_monthly_loss_limit":15000.0,
        "default_daily_bet_limit":2000.0,"default_weekly_bet_limit":10000.0,"default_monthly_bet_limit":30000.0,
        "default_max_single_bet":500.0,"log_level":"info","fraud_alert_email":"test@example.test",
        "allowed_origins":["https://web.example.test"],"metrics_enabled":true,"health_check_interval_seconds":30
    })).unwrap())
}

fn user() -> User {
    serde_json::from_value(json!({
        "id":Uuid::new_v4(),"email":"session-test@example.test","password_hash":"test-only",
        "first_name":"Test","last_name":"Account","date_of_birth":"1990-01-01",
        "phone":null,"address":null,"is_verified":true,"is_active":true,"role":"user",
        "created_at":chrono::Utc::now(),"updated_at":chrono::Utc::now(),"last_login":null,
        "login_count":0,"failed_login_attempts":0,"locked_until":null
    }))
    .unwrap()
}

#[actix_web::test]
async fn storage_outage_does_not_report_valid_credentials_as_expired() {
    let pool = PgPoolOptions::new()
        .connect_lazy("postgresql://unused@127.0.0.1:1/unused")
        .unwrap();
    pool.close().await;
    let auth = AuthService::new(config()).with_database(pool);
    let token = auth.generate_token(&user(), "outage-test").unwrap();
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(auth.clone()))
            .service(
                web::scope("/protected")
                    .wrap(crate::middleware::jwt_auth::RequireAuth::new(auth))
                    .route("", web::get().to(|| async { HttpResponse::Ok().finish() })),
            )
            .route("/logout", web::post().to(crate::handlers::auth::logout)),
    )
    .await;
    for path in ["/protected", "/logout"] {
        let request = if path == "/logout" {
            test::TestRequest::post()
        } else {
            test::TestRequest::get()
        };
        let response = test::call_service(
            &app,
            request
                .uri(path)
                .insert_header(("Authorization", format!("Bearer {token}")))
                .to_request(),
        )
        .await;
        assert_eq!(response.status(), 503, "{path}");
        let body: serde_json::Value = test::read_body_json(response).await;
        assert_eq!(body["error"]["code"], "AUTH_STORAGE_UNAVAILABLE");
    }
    let response = test::call_service(
        &app,
        test::TestRequest::get()
            .uri("/protected")
            .insert_header(("Authorization", "Bearer invalid-test-token"))
            .to_request(),
    )
    .await;
    assert_eq!(response.status(), 401);
}

async fn schema_pool(url: &str, schema: String) -> PgPool {
    PgPoolOptions::new()
        .max_connections(2)
        .after_connect(move |connection, _| {
            let query = format!("SET search_path TO {schema}");
            Box::pin(async move {
                sqlx::query(&query).execute(connection).await?;
                Ok(())
            })
        })
        .connect(url)
        .await
        .unwrap()
}

#[actix_web::test]
#[ignore = "requires SESSION_TEST_DATABASE_URL on loopback; creates disposable UUID schemas"]
async fn durable_sessions_survive_independent_instances_and_revocation() {
    let url =
        std::env::var("SESSION_TEST_DATABASE_URL").expect("SESSION_TEST_DATABASE_URL required");
    let parsed = reqwest::Url::parse(&url).unwrap();
    assert!(
        matches!(
            parsed.host_str(),
            Some("127.0.0.1" | "localhost" | "[::1]" | "::1")
        ),
        "Loopback database required"
    );
    let schema = format!("session_test_{}", Uuid::new_v4().simple());
    let admin = PgPool::connect(&url).await.unwrap();
    sqlx::query(&format!("CREATE SCHEMA {schema}"))
        .execute(&admin)
        .await
        .unwrap();
    let first_pool = schema_pool(&url, schema.clone()).await;
    let second_pool = schema_pool(&url, schema.clone()).await;
    let outcome = std::panic::AssertUnwindSafe(async {
    sqlx::query("CREATE TABLE users(id UUID PRIMARY KEY,is_active BOOLEAN NOT NULL,locked_until TIMESTAMPTZ)")
        .execute(&first_pool).await.unwrap();
    sqlx::raw_sql(include_str!(
        "../migrations/20261026000002_persistent_auth_sessions.sql"
    ))
    .execute(&first_pool)
    .await
    .unwrap();
    let account = user();
    sqlx::query("INSERT INTO users(id,is_active) VALUES($1,TRUE)")
        .bind(account.id)
        .execute(&first_pool)
        .await
        .unwrap();
    let first = AuthService::new(config()).with_database(first_pool.clone());
    first
        .create_persistent_session(&account, "session-one", "127.0.0.1", "test")
        .await
        .unwrap();
    first
        .create_persistent_session(&account, "session-two", "127.0.0.1", "test")
        .await
        .unwrap();
    let token = first.generate_token(&account, "session-one").unwrap();
    let other = first.generate_token(&account, "session-two").unwrap();
    let second = AuthService::new(config()).with_database(second_pool.clone());
    assert_eq!(
        second.validate_request_token(&token).await.unwrap().sub,
        account.id.to_string()
    );
    drop(first);
    let restarted = AuthService::new(config()).with_database(first_pool.clone());
    let claims = restarted.validate_request_token(&token).await.unwrap();
    second.revoke_request_session(&claims).await.unwrap();
    assert!(matches!(
        restarted.validate_request_token(&token).await,
        Err(AppError::SessionExpired)
    ));
    assert!(second.validate_request_token(&other).await.is_ok());
    let wrong_account = first_user_token(&second, "session-two");
    assert!(matches!(
        restarted.validate_request_token(&wrong_account).await,
        Err(AppError::SessionExpired)
    ));
    sqlx::query("UPDATE auth_sessions SET last_activity_at=NOW()-INTERVAL '31 minutes' WHERE session_id='session-two'")
        .execute(&first_pool).await.unwrap();
    assert!(matches!(
        second.validate_request_token(&other).await,
        Err(AppError::SessionExpired)
    ));
    restarted
        .create_persistent_session(&account, "session-three", "127.0.0.1", "test")
        .await
        .unwrap();
    let third = restarted.generate_token(&account, "session-three").unwrap();
    sqlx::query("UPDATE users SET is_active=FALSE")
        .execute(&first_pool)
        .await
        .unwrap();
    assert!(matches!(
        second.validate_request_token(&third).await,
        Err(AppError::SessionExpired)
    ));
    sqlx::query("UPDATE users SET is_active=TRUE").execute(&first_pool).await.unwrap();
    restarted
        .create_persistent_session(&account, "session-four", "127.0.0.1", "test")
        .await
        .unwrap();
    let admin_token = restarted.generate_token(&account, "session-four").unwrap();
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(restarted.clone()))
            .app_data(web::Data::new(first_pool.clone()))
            .service(
                web::scope("/admin")
                    .wrap(crate::middleware::admin_auth::RequireAdmin::new(
                        std::rc::Rc::new(restarted.clone()),
                    ))
                    .route("", web::get().to(|| async { HttpResponse::Ok().finish() })),
            )
            .service(
                web::scope("/super")
                    .wrap(crate::middleware::admin_auth::RequireSuperAdmin::new(
                        std::rc::Rc::new(restarted),
                    ))
                    .route("", web::get().to(|| async { HttpResponse::Ok().finish() })),
            ),
    )
    .await;
    // The deliberately minimal users table has no role column. A failed role
    // lookup is unavailable, never permission granted or a false forbidden.
    for path in ["/admin", "/super"] {
        let response = test::call_service(
            &app,
            test::TestRequest::get()
                .uri(path)
                .insert_header(("Authorization", format!("Bearer {admin_token}")))
                .to_request(),
        )
        .await;
        assert_eq!(response.status(), 503);
    }
    drop(app);
    sqlx::query("UPDATE users SET is_active=TRUE,locked_until=NOW()+INTERVAL '1 hour'")
        .execute(&first_pool)
        .await
        .unwrap();
    assert!(matches!(
        second.validate_request_token(&third).await,
        Err(AppError::SessionExpired)
    ));
    sqlx::query("UPDATE users SET locked_until=NULL")
        .execute(&first_pool)
        .await
        .unwrap();
    assert!(second.validate_request_token(&third).await.is_ok());
    sqlx::query("UPDATE auth_sessions SET created_at=NOW()-INTERVAL '2 days',expires_at=NOW()-INTERVAL '1 day' WHERE session_id='session-three'")
        .execute(&first_pool).await.unwrap();
    assert!(matches!(
        second.validate_request_token(&third).await,
        Err(AppError::SessionExpired)
    ));
    }).catch_unwind().await;
    first_pool.close().await;
    second_pool.close().await;
    sqlx::query(&format!("DROP SCHEMA {schema} CASCADE"))
        .execute(&admin)
        .await
        .unwrap();
    admin.close().await;
    if let Err(failure) = outcome {
        std::panic::resume_unwind(failure);
    }
}

fn first_user_token(auth: &AuthService, session: &str) -> String {
    auth.generate_token(&user(), session).unwrap()
}

#[actix_web::test]
#[ignore = "HTTP server fixture, launched explicitly by scripts/verify_auth_http.py"]
async fn serve_http_fixture() {
    if std::env::var("AUTH_HTTP_FIXTURE_MODE").as_deref() != Ok("enabled") {
        return;
    }
    crate::run_server().await.unwrap();
}
