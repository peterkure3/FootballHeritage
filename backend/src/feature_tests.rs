use super::*;
use crate::{auth::AuthService, config::AppConfig, models::User};
use actix_cors::Cors;
use actix_web::{test, App};
use std::sync::Arc;

fn config() -> AppConfig {
    serde_json::from_value(json!({
        "app_env":"test", "database_url":"unused", "jwt_secret":"feature-test-signing-key-over-32-bytes", "jwt_expiration_hours":1,
        "encryption_key":"01234567890123456789012345678901", "host":"127.0.0.1", "port":0, "https_enabled":false,
        "tls_cert_path":"", "tls_key_path":"", "bet_rate_limit_per_minute":100, "login_rate_limit_per_minute":100,
        "register_rate_limit_per_hour":100, "bcrypt_cost":4, "session_timeout_minutes":30,"max_login_attempts":5,
        "account_lock_minutes":15,"default_daily_loss_limit":1000.0,"default_weekly_loss_limit":5000.0,"default_monthly_loss_limit":15000.0,
        "default_daily_bet_limit":2000.0,"default_weekly_bet_limit":10000.0,"default_monthly_bet_limit":30000.0,"default_max_single_bet":500.0,
        "log_level":"info","fraud_alert_email":"test@example.test","allowed_origins":["https://web.example.test"],"metrics_enabled":true,
        "health_check_interval_seconds":30
    })).unwrap()
}
fn user(role: &str) -> User {
    serde_json::from_value(json!({
        "id":Uuid::new_v4(),"email":format!("{role}@example.test"),"password_hash":"test-only","first_name":"Test","last_name":"Account",
        "date_of_birth":"1990-01-01","phone":null,"address":null,"is_verified":true,"is_active":true,"role":role,
        "created_at":chrono::Utc::now(),"updated_at":chrono::Utc::now(),"last_login":null,"login_count":0,"failed_login_attempts":0,"locked_until":null
    })).unwrap()
}

#[actix_web::test]
async fn database_policy_and_http_enforcement() {
    let Ok(url) = std::env::var("FEATURE_TEST_DATABASE_URL") else {
        eprintln!("SKIPPED database feature checks: set FEATURE_TEST_DATABASE_URL to a disposable PostgreSQL database");
        return;
    };
    // A unique schema isolates each run; CI destroys the disposable database.
    let schema = format!("feature_test_{}", Uuid::new_v4().simple());
    let bootstrap = PgPool::connect(&url).await.unwrap();
    sqlx::query(&format!("CREATE SCHEMA {schema}"))
        .execute(&bootstrap)
        .await
        .unwrap();
    let pool = sqlx::postgres::PgPoolOptions::new()
        .max_connections(4)
        .after_connect(move |conn, _| {
            let sql = format!("SET search_path TO {schema}");
            Box::pin(async move {
                sqlx::query(&sql).execute(conn).await?;
                Ok(())
            })
        })
        .connect(&url)
        .await
        .unwrap();
    sqlx::query("CREATE TABLE users(id UUID PRIMARY KEY,role TEXT,is_active BOOLEAN NOT NULL,locked_until TIMESTAMPTZ)").execute(&pool).await.unwrap();
    sqlx::raw_sql(include_str!(
        "../migrations/20261022000001_feature_management.sql"
    ))
    .execute(&pool)
    .await
    .unwrap();
    let auth = AuthService::new(Arc::new(config()));
    let admin = user("superadmin");
    let ordinary = user("user");
    for user in [&admin, &ordinary] {
        sqlx::query("INSERT INTO users(id,role,is_active) VALUES($1,$2,TRUE)")
            .bind(user.id)
            .bind(&user.role)
            .execute(&pool)
            .await
            .unwrap();
        auth.create_session(user, &user.id.to_string(), "127.0.0.1", "feature-test");
    }
    let admin_token = auth.generate_token(&admin, &admin.id.to_string()).unwrap();
    let user_token = auth
        .generate_token(&ordinary, &ordinary.id.to_string())
        .unwrap();
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .app_data(web::Data::new(auth.clone()))
            .wrap(FeatureGate)
            .wrap(
                Cors::default()
                    .allowed_origin("https://web.example.test")
                    .allowed_methods(vec!["GET", "PATCH", "POST"])
                    .allowed_headers(vec!["authorization", "content-type"]),
            )
            .service(
                web::scope("/api/v1/admin")
                    .wrap(crate::middleware::admin_auth::RequireAdmin::new(Rc::new(
                        auth,
                    )))
                    .configure(configure_admin)
                    .route(
                        "/whoami",
                        web::get().to(|req: HttpRequest| async move {
                            HttpResponse::Ok().json(
                                crate::middleware::admin_auth::get_admin_claims(&req)
                                    .map(|claims| claims.role),
                            )
                        }),
                    ),
            )
            .route("/api/v1/me/features", web::get().to(effective))
            .route(
                "/api/v1/wallet/deposit",
                web::post().to(|| async { HttpResponse::Ok().body("business handler ran") }),
            )
            .route(
                "/api/v1/ai-picks/chat",
                web::post().to(|| async { HttpResponse::Ok().finish() }),
            )
            .route(
                "/api/v1/auth/logout",
                web::post().to(|| async { HttpResponse::Ok().finish() }),
            ),
    )
    .await;
    for token in [None, Some(&user_token)] {
        let mut req = test::TestRequest::patch()
            .uri("/api/v1/admin/features/wallet")
            .set_json(json!({"enabled":false}));
        if let Some(token) = token {
            req = req.insert_header(("Authorization", format!("Bearer {token}")));
        }
        let response = test::call_service(&app, req.to_request()).await;
        assert!(matches!(response.status().as_u16(), 401 | 403));
    }
    assert!(available(&pool, "wallet", Some(ordinary.id), "user")
        .await
        .unwrap());
    assert!(
        !available(&pool, "unknown-key", Some(admin.id), "superadmin")
            .await
            .unwrap()
    );
    let patch = test::TestRequest::patch()
        .uri("/api/v1/admin/features/wallet")
        .insert_header(("Authorization", format!("Bearer {admin_token}")))
        .set_json(json!({"enabled":false}))
        .to_request();
    assert_eq!(test::call_service(&app, patch).await.status(), 200);
    for token in [&user_token, &admin_token] {
        let req = test::TestRequest::post()
            .uri("/api/v1/wallet/deposit")
            .insert_header(("Authorization", format!("Bearer {token}")))
            .to_request();
        let response = test::call_service(&app, req).await;
        assert_eq!(response.status(), 403);
        let body: Value = test::read_body_json(response).await;
        assert_eq!(body["error"]["code"], "FEATURE_DISABLED");
    }
    assert_eq!(
        sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM feature_audit_logs")
            .fetch_one(&pool)
            .await
            .unwrap(),
        1
    );
    assert!(sqlx::query("DELETE FROM feature_audit_logs")
        .execute(&pool)
        .await
        .is_err());
    sqlx::query("UPDATE feature_flags SET enabled=TRUE WHERE key='wallet'")
        .execute(&pool)
        .await
        .unwrap();
    let restrict = test::TestRequest::patch()
        .uri(&format!(
            "/api/v1/admin/users/{}/features/wallet",
            ordinary.id
        ))
        .insert_header(("Authorization", format!("Bearer {admin_token}")))
        .set_json(json!({"enabled":false}))
        .to_request();
    assert_eq!(test::call_service(&app, restrict).await.status(), 200);
    assert!(!available(&pool, "wallet", Some(ordinary.id), "user")
        .await
        .unwrap());
    assert!(available(&pool, "wallet", Some(admin.id), "superadmin")
        .await
        .unwrap());
    let req = test::TestRequest::post()
        .uri("/api/v1/wallet/deposit")
        .insert_header(("Authorization", format!("Bearer {user_token}")))
        .to_request();
    assert_eq!(test::call_service(&app, req).await.status(), 403);
    sqlx::query("UPDATE user_feature_overrides SET enabled=TRUE WHERE user_id=$1")
        .bind(ordinary.id)
        .execute(&pool)
        .await
        .unwrap();
    let restrict = test::TestRequest::patch()
        .uri("/api/v1/admin/features/wallet/roles/user")
        .insert_header(("Authorization", format!("Bearer {admin_token}")))
        .set_json(json!({"enabled":false}))
        .to_request();
    assert_eq!(test::call_service(&app, restrict).await.status(), 200);
    assert!(!available(&pool, "wallet", Some(ordinary.id), "user")
        .await
        .unwrap());
    let req = test::TestRequest::get()
        .uri(&format!("/api/v1/admin/users/{}/features", ordinary.id))
        .insert_header(("Authorization", format!("Bearer {admin_token}")))
        .to_request();
    let response: Value = test::call_and_read_body_json(&app, req).await;
    assert_eq!(response["features"]["wallet"], false);
    assert_eq!(response["overrides"]["wallet"], true);
    let req = test::TestRequest::get()
        .uri("/api/v1/me/features")
        .insert_header(("Authorization", format!("Bearer {user_token}")))
        .to_request();
    let response: Value = test::call_and_read_body_json(&app, req).await;
    assert_eq!(response["features"]["wallet"], false);
    // Audit insertion failure must roll back the feature update too.
    sqlx::query("ALTER TABLE feature_audit_logs ADD CONSTRAINT test_reject CHECK (feature_key<>'wallet') NOT VALID").execute(&pool).await.unwrap();
    let req = test::TestRequest::patch()
        .uri("/api/v1/admin/features/wallet")
        .insert_header(("Authorization", format!("Bearer {admin_token}")))
        .set_json(json!({"enabled":false}))
        .to_request();
    assert_eq!(test::call_service(&app, req).await.status(), 503);
    assert!(
        sqlx::query_scalar::<_, bool>("SELECT enabled FROM feature_flags WHERE key='wallet'")
            .fetch_one(&pool)
            .await
            .unwrap()
    );
    sqlx::query("ALTER TABLE feature_audit_logs DROP CONSTRAINT test_reject")
        .execute(&pool)
        .await
        .unwrap();
    sqlx::query("UPDATE feature_flags SET emergency_disabled=TRUE WHERE key='wallet'")
        .execute(&pool)
        .await
        .unwrap();
    assert!(!available(&pool, "wallet", Some(admin.id), "superadmin")
        .await
        .unwrap());
    sqlx::query("UPDATE feature_flags SET enabled=TRUE WHERE key='maintenance'")
        .execute(&pool)
        .await
        .unwrap();
    let req = test::TestRequest::post()
        .uri("/api/v1/ai-picks/chat")
        .insert_header(("Authorization", format!("Bearer {admin_token}")))
        .to_request();
    assert_eq!(test::call_service(&app, req).await.status(), 403);
    assert_eq!(
        test::call_service(
            &app,
            test::TestRequest::post()
                .uri("/api/v1/auth/logout")
                .to_request()
        )
        .await
        .status(),
        200
    );
    let req = test::TestRequest::patch()
        .uri("/api/v1/admin/features/unknown-key")
        .insert_header(("Authorization", format!("Bearer {admin_token}")))
        .set_json(json!({"enabled":true}))
        .to_request();
    assert_eq!(test::call_service(&app, req).await.status(), 404);
    assert_eq!(
        sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM feature_audit_logs")
            .fetch_one(&pool)
            .await
            .unwrap(),
        3
    );
    let preflight = test::TestRequest::default()
        .method(actix_web::http::Method::OPTIONS)
        .uri("/api/v1/admin/features/wallet")
        .insert_header(("Origin", "https://web.example.test"))
        .insert_header(("Access-Control-Request-Method", "PATCH"))
        .insert_header((
            "Access-Control-Request-Headers",
            "authorization,content-type",
        ))
        .to_request();
    assert!(test::call_service(&app, preflight)
        .await
        .status()
        .is_success());
    let denied = test::TestRequest::default()
        .method(actix_web::http::Method::OPTIONS)
        .uri("/api/v1/admin/features/wallet")
        .insert_header(("Origin", "https://evil.example.test"))
        .insert_header(("Access-Control-Request-Method", "PATCH"))
        .to_request();
    assert_eq!(test::call_service(&app, denied).await.status(), 400);
    assert!(sqlx::query("UPDATE users SET is_active=FALSE WHERE id=$1")
        .bind(admin.id)
        .execute(&pool)
        .await
        .is_err());
    assert!(sqlx::query("UPDATE users SET role='user' WHERE id=$1")
        .bind(admin.id)
        .execute(&pool)
        .await
        .is_err());
    // A second administrator permits revocation, and an old signed JWT loses access.
    sqlx::query("INSERT INTO users(id,role,is_active) VALUES($1,'superadmin',TRUE)")
        .bind(Uuid::new_v4())
        .execute(&pool)
        .await
        .unwrap();
    sqlx::query("UPDATE users SET role='admin' WHERE id=$1")
        .bind(admin.id)
        .execute(&pool)
        .await
        .unwrap();
    let req = test::TestRequest::get()
        .uri("/api/v1/admin/whoami")
        .insert_header(("Authorization", format!("Bearer {admin_token}")))
        .to_request();
    let role: Value = test::call_and_read_body_json(&app, req).await;
    assert_eq!(role, "admin");
    sqlx::query("UPDATE users SET role='user' WHERE id=$1")
        .bind(admin.id)
        .execute(&pool)
        .await
        .unwrap();
    let req = test::TestRequest::get()
        .uri("/api/v1/admin/features")
        .insert_header(("Authorization", format!("Bearer {admin_token}")))
        .to_request();
    assert_eq!(test::call_service(&app, req).await.status(), 403);
    pool.close().await;
    bootstrap.close().await;
}
