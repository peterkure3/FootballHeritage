use actix_web::{
    body::to_bytes, http::StatusCode, test::TestRequest, web, HttpMessage, HttpRequest,
    HttpResponse,
};
use serde_json::{json, Value};
use sqlx::{postgres::PgPoolOptions, PgPool};
use uuid::Uuid;

async fn fixture_pool() -> PgPool {
    dotenvy::dotenv().ok();
    let pool = PgPoolOptions::new()
        .max_connections(1)
        .connect(&std::env::var("DATABASE_URL").expect("DATABASE_URL required"))
        .await
        .unwrap();
    // These tables shadow public tables for this connection and disappear on close.
    for sql in [
        "CREATE TEMP TABLE users (id uuid PRIMARY KEY, email text, first_name text, last_name text, role text, is_verified bool, is_active bool, created_at timestamptz DEFAULT NOW(), last_login timestamptz, login_count int DEFAULT 0, locked_until timestamptz)",
        "CREATE TEMP TABLE bets (id uuid, user_id uuid, amount numeric, potential_win numeric, status text, created_at timestamptz DEFAULT NOW(), settled_at timestamptz DEFAULT NOW())",
        "CREATE TEMP TABLE events (LIKE public.events INCLUDING DEFAULTS)",
        "CREATE TEMP TABLE fraud_alerts (status text, severity text)",
        "CREATE TEMP TABLE admin_logs (admin_id uuid, action text, target_type text, target_id uuid)",
    ] { sqlx::query(sql).execute(&pool).await.unwrap(); }
    sqlx::query("INSERT INTO users (id,email,first_name,last_name,role,is_verified,is_active) VALUES ($1, 'member@example.test', 'Test', 'Member', 'user', false, true), ($2, 'other@example.test', 'Other', 'Member', 'user', true, false)")
        .bind(Uuid::new_v4()).bind(Uuid::new_v4()).execute(&pool).await.unwrap();
    pool
}

fn admin_request() -> HttpRequest {
    let req = TestRequest::default().to_http_request();
    req.extensions_mut().insert(crate::models::Claims {
        sub: Uuid::new_v4().to_string(),
        email: "admin@example.test".into(),
        exp: usize::MAX,
        iat: 0,
        iss: "test".into(),
        aud: "test".into(),
        session_id: "test".into(),
        role: "admin".into(),
    });
    req
}

async fn response_json(response: HttpResponse) -> Value {
    assert_eq!(response.status(), StatusCode::OK);
    serde_json::from_slice(&to_bytes(response.into_body()).await.unwrap()).unwrap()
}

#[actix_rt::test]
#[ignore = "requires local PostgreSQL; uses connection-local temporary tables only"]
async fn user_search_is_bound_and_pagination_totals_follow_filters() {
    let pool = fixture_pool().await;
    for (filter, expected) in [
        (json!({"status":"active", "limit":1}), 1),
        (
            json!({"search":"' OR 1=1 --", "sort_by":"email; SELECT 1", "sort_order":"DROP TABLE users"}),
            0,
        ),
        (json!({"verified":true, "limit":0}), 1),
    ] {
        let query = serde_json::from_value(filter).unwrap();
        let response = super::users::list_users(
            web::Data::new(pool.clone()),
            web::Query(query),
            admin_request(),
        )
        .await;
        let body = response_json(response).await;
        assert_eq!(body["total"], expected);
        assert_eq!(body["users"].as_array().unwrap().len(), expected as usize);
        assert!(body["limit"].as_i64().unwrap() >= 1);
    }
    pool.close().await;
}

#[actix_rt::test]
#[ignore = "requires local PostgreSQL; uses connection-local temporary tables only"]
async fn metrics_use_winning_payouts_and_event_pages_respect_offsets() {
    let pool = fixture_pool().await;
    sqlx::query("INSERT INTO bets (id,user_id,amount,potential_win,status) SELECT gen_random_uuid(), id, 10, 25, 'WON' FROM users WHERE is_active")
        .execute(&pool).await.unwrap();
    sqlx::query("INSERT INTO bets (id,user_id,amount,potential_win,status) VALUES (gen_random_uuid(),gen_random_uuid(),10,50,'LOST'),(gen_random_uuid(),gen_random_uuid(),30,90,'PENDING')").execute(&pool).await.unwrap();
    for team in ["First", "Second", "Third"] {
        sqlx::query("INSERT INTO events (id,sport,league,home_team,away_team,event_date,status) VALUES ($1,'SOCCER','Test',$2,'Away',NOW() + interval '1 day','UPCOMING')")
            .bind(Uuid::new_v4()).bind(team).execute(&pool).await.unwrap();
    }
    let response =
        super::analytics::get_dashboard_metrics(web::Data::new(pool.clone()), admin_request())
            .await;
    let body = response_json(response).await;
    assert_eq!(body["revenue_today"], -5.0);
    assert_eq!(body["bet_volume_today"], 50.0);
    assert_eq!(body["total_bets_today"], 3);
    assert_eq!(body["total_users"], 1);
    assert_eq!(body["upcoming_events"], 3);
    let response = super::events::get_all_events(
        web::Data::new(pool.clone()),
        web::Query(json!({"limit":"1","offset":"2"})),
        admin_request(),
    )
    .await;
    assert_eq!(response_json(response).await["count"], 1);
    pool.close().await;
}
