use super::*;
use crate::{auth::AuthService, crypto::CryptoService, handlers::wallet, models::PlaceBetRequest};
use actix_web::{test, App};
use bigdecimal::BigDecimal;
use futures_util::future::join_all;
use std::sync::Arc;

#[actix_web::test]
async fn financial_operations_are_serialized_and_balance_reads_do_not_create_wallets() {
    let Ok(url) = std::env::var("FEATURE_TEST_DATABASE_URL") else {
        eprintln!("SKIP financial DB tests: use an isolated FEATURE_TEST_DATABASE_URL");
        return;
    };
    let bootstrap = PgPool::connect(&url).await.unwrap();
    // Extensions belong to the disposable database's public schema, so later
    // unique-schema runs do not depend on a previous test's search_path.
    sqlx::query("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\" WITH SCHEMA public")
        .execute(&bootstrap)
        .await
        .unwrap();
    let schema = format!("finance_test_{}", Uuid::new_v4().simple());
    sqlx::query(&format!("CREATE SCHEMA {schema}"))
        .execute(&bootstrap)
        .await
        .unwrap();
    let pool = sqlx::postgres::PgPoolOptions::new()
        .max_connections(10)
        .after_connect(move |conn, _| {
            let query = format!("SET search_path TO {schema},public");
            Box::pin(async move {
                sqlx::query(&query).execute(conn).await?;
                Ok(())
            })
        })
        .connect(&url)
        .await
        .unwrap();
    sqlx::migrate!("./migrations").run(&pool).await.unwrap();
    let config = super::integration_tests::config();
    let crypto = Arc::new(CryptoService::from_string(&config.encryption_key));
    let auth = AuthService::new(Arc::new(config.clone()));
    let mut users = Vec::new();
    for name in ["depositor", "bettor", "reader"] {
        let mut user = super::integration_tests::user("user");
        user.email = format!("{name}@example.test");
        sqlx::query("INSERT INTO users(id,email,password_hash,first_name,last_name,date_of_birth,role,is_active) VALUES($1,$2,'test-only','Test','Account','1990-01-01','user',TRUE)")
            .bind(user.id).bind(&user.email).execute(&pool).await.unwrap();
        auth.create_session(&user, &user.id.to_string(), "127.0.0.1", "financial-test");
        let token = auth.generate_token(&user, &user.id.to_string()).unwrap();
        users.push((user.id, token));
    }
    let app = test::init_service(
        App::new()
            .app_data(web::Data::new(pool.clone()))
            .app_data(web::Data::new(config.clone()))
            .app_data(web::Data::new(crate::rates::RateLimiters::new(&config)))
            .app_data(web::Data::new(crate::monitoring::MonitoringService::new(
                &config,
            )))
            .app_data(web::Data::new(auth.clone()))
            .wrap(FeatureGate)
            .service(
                web::scope("/api/v1/wallet")
                    .wrap(crate::middleware::jwt_auth::RequireAuth::new(auth))
                    .route("/balance", web::get().to(wallet::get_balance))
                    .route("/deposit", web::post().to(wallet::deposit))
                    .route("/withdraw", web::post().to(wallet::withdraw)),
            ),
    )
    .await;
    let before = sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM wallets")
        .fetch_one(&pool)
        .await
        .unwrap();
    let anonymous = test::call_service(
        &app,
        test::TestRequest::get()
            .uri("/api/v1/wallet/balance")
            .to_request(),
    )
    .await;
    assert_eq!(anonymous.status(), 401);
    let reader = test::TestRequest::get()
        .uri("/api/v1/wallet/balance")
        .insert_header(("Authorization", format!("Bearer {}", users[2].1)))
        .to_request();
    assert_eq!(test::call_service(&app, reader).await.status(), 200);
    assert_eq!(
        sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM wallets")
            .fetch_one(&pool)
            .await
            .unwrap(),
        before
    );

    let requests = (0..4).map(|_| {
        let request = test::TestRequest::post()
            .uri("/api/v1/wallet/deposit")
            .insert_header(("Authorization", format!("Bearer {}", users[0].1)))
            .set_json(json!({"amount":25}))
            .to_request();
        test::call_service(&app, request)
    });
    for response in join_all(requests).await {
        assert_eq!(response.status(), 200);
    }
    let balance = sqlx::query_as::<_, (String, String)>(
        "SELECT encrypted_balance,encryption_iv FROM wallets WHERE user_id=$1",
    )
    .bind(users[0].0)
    .fetch_one(&pool)
    .await
    .unwrap();
    assert_eq!(
        crypto.decrypt_balance(&balance.0, &balance.1).unwrap(),
        BigDecimal::from(100)
    );
    assert_eq!(
        sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM wallets WHERE user_id=$1")
            .bind(users[0].0)
            .fetch_one(&pool)
            .await
            .unwrap(),
        1
    );
    let requests = (0..4).map(|_| {
        let request = test::TestRequest::post()
            .uri("/api/v1/wallet/withdraw")
            .insert_header(("Authorization", format!("Bearer {}", users[0].1)))
            .set_json(json!({"amount":10}))
            .to_request();
        test::call_service(&app, request)
    });
    for response in join_all(requests).await {
        assert_eq!(response.status(), 200);
    }
    let balance = sqlx::query_as::<_, (String, String)>(
        "SELECT encrypted_balance,encryption_iv FROM wallets WHERE user_id=$1",
    )
    .bind(users[0].0)
    .fetch_one(&pool)
    .await
    .unwrap();
    assert_eq!(
        crypto.decrypt_balance(&balance.0, &balance.1).unwrap(),
        BigDecimal::from(60)
    );
    assert_eq!(
        sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM transactions WHERE user_id=$1")
            .bind(users[0].0)
            .fetch_one(&pool)
            .await
            .unwrap(),
        8
    );

    let (encrypted, iv) = crypto.encrypt_balance(&BigDecimal::from(100)).unwrap();
    sqlx::query(
        "INSERT INTO wallets(id,user_id,encrypted_balance,encryption_iv) VALUES($1,$2,$3,$4)",
    )
    .bind(Uuid::new_v4())
    .bind(users[1].0)
    .bind(encrypted)
    .bind(iv)
    .execute(&pool)
    .await
    .unwrap();
    let event = Uuid::new_v4();
    sqlx::query("INSERT INTO events(id,sport,league,home_team,away_team,event_date,status,moneyline_home,moneyline_away) VALUES($1,'NFL','NFL','Staging Home','Staging Away',NOW()+INTERVAL '1 day','UPCOMING',2,2)").bind(event).execute(&pool).await.unwrap();
    let service = crate::betting_simple::SimpleBettingService::new(crypto.clone());
    let results = join_all((0..8).map(|_| {
        service.place_bet(
            &pool,
            users[1].0,
            PlaceBetRequest {
                event_id: event,
                bet_type: "moneyline".into(),
                selection: "home".into(),
                odds: BigDecimal::from(2),
                amount: BigDecimal::from(25),
            },
        )
    }))
    .await;
    assert_eq!(results.iter().filter(|r| r.is_ok()).count(), 4);
    assert!(results
        .iter()
        .filter_map(|r| r.as_ref().err())
        .all(|error| matches!(error, crate::errors::AppError::InsufficientFunds)));
    let balance = sqlx::query_as::<_, (String, String)>(
        "SELECT encrypted_balance,encryption_iv FROM wallets WHERE user_id=$1",
    )
    .bind(users[1].0)
    .fetch_one(&pool)
    .await
    .unwrap();
    assert_eq!(
        crypto.decrypt_balance(&balance.0, &balance.1).unwrap(),
        BigDecimal::from(0)
    );
    assert_eq!(
        sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM bets WHERE user_id=$1")
            .bind(users[1].0)
            .fetch_one(&pool)
            .await
            .unwrap(),
        4
    );
    pool.close().await;
    bootstrap.close().await;
}
