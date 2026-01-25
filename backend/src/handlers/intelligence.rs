use actix_web::{web, HttpResponse};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::{PgPool, Postgres, QueryBuilder};
use uuid::Uuid;

use crate::errors::AppResult;

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct DeviggedOddsRow {
    pub id: Uuid,
    pub event_id: Option<Uuid>,
    pub pipeline_match_id: Option<String>,
    pub bookmaker: String,
    pub market: String,
    pub outcome_a: String,
    pub outcome_b: String,
    pub odds_a: i32,
    pub odds_b: i32,
    pub fair_prob_a: f64,
    pub fair_prob_b: f64,
    pub vig: f64,
    pub source_updated_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct DeviggedOddsQuery {
    pub event_id: Option<Uuid>,
    pub pipeline_match_id: Option<String>,
    pub bookmaker: Option<String>,
    pub market: Option<String>,
    pub limit: Option<i64>,
}

pub async fn get_devigged_odds(
    pool: web::Data<PgPool>,
    query: web::Query<DeviggedOddsQuery>,
) -> AppResult<HttpResponse> {
    let mut qb: QueryBuilder<Postgres> = QueryBuilder::new(
        "SELECT id, event_id, pipeline_match_id, bookmaker, market, outcome_a, outcome_b, odds_a, odds_b, fair_prob_a, fair_prob_b, vig, source_updated_at, created_at FROM devigged_odds",
    );

    let mut has_where = false;

    if let Some(event_id) = query.event_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("event_id = ").push_bind(event_id);
    }

    if let Some(ref pipeline_match_id) = query.pipeline_match_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("pipeline_match_id = ").push_bind(pipeline_match_id);
    }

    if let Some(ref bookmaker) = query.bookmaker {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("bookmaker = ").push_bind(bookmaker);
    }

    if let Some(ref market) = query.market {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        qb.push("market = ").push_bind(market);
    }

    qb.push(" ORDER BY created_at DESC");

    let limit = query.limit.unwrap_or(200).clamp(1, 2000);
    qb.push(" LIMIT ").push_bind(limit);

    let rows: Vec<DeviggedOddsRow> = qb.build_query_as().fetch_all(pool.get_ref()).await?;
    Ok(HttpResponse::Ok().json(rows))
}

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct EvBetRow {
    pub id: Uuid,
    pub event_id: Option<Uuid>,
    pub pipeline_match_id: Option<String>,
    pub bookmaker: Option<String>,
    pub market: String,
    pub selection: String,
    pub odds: i32,
    pub stake: sqlx::types::BigDecimal,
    pub true_probability: f64,
    pub expected_value: f64,
    pub expected_value_pct: f64,
    pub source_updated_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct EvBetsQuery {
    pub event_id: Option<Uuid>,
    pub pipeline_match_id: Option<String>,
    pub bookmaker: Option<String>,
    pub market: Option<String>,
    pub min_ev_pct: Option<f64>,
    pub limit: Option<i64>,
}

pub async fn get_ev_bets(pool: web::Data<PgPool>, query: web::Query<EvBetsQuery>) -> AppResult<HttpResponse> {
    let mut qb: QueryBuilder<Postgres> = QueryBuilder::new(
        "SELECT id, event_id, pipeline_match_id, bookmaker, market, selection, odds, stake, true_probability, expected_value, expected_value_pct, source_updated_at, created_at FROM ev_bets",
    );

    let mut has_where = false;

    if let Some(event_id) = query.event_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("event_id = ").push_bind(event_id);
    }

    if let Some(ref pipeline_match_id) = query.pipeline_match_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("pipeline_match_id = ").push_bind(pipeline_match_id);
    }

    if let Some(ref bookmaker) = query.bookmaker {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("bookmaker = ").push_bind(bookmaker);
    }

    if let Some(ref market) = query.market {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("market = ").push_bind(market);
    }

    if let Some(min_ev_pct) = query.min_ev_pct {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        qb.push("expected_value_pct >= ").push_bind(min_ev_pct);
    }

    qb.push(" ORDER BY expected_value_pct DESC, created_at DESC");

    let limit = query.limit.unwrap_or(200).clamp(1, 2000);
    qb.push(" LIMIT ").push_bind(limit);

    let rows: Vec<EvBetRow> = qb.build_query_as().fetch_all(pool.get_ref()).await?;
    Ok(HttpResponse::Ok().json(rows))
}

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct ArbitrageRow {
    pub id: Uuid,
    pub event_id: Option<Uuid>,
    pub pipeline_match_id: Option<String>,
    pub market: String,
    pub selection_a: String,
    pub selection_b: String,
    pub book_a: String,
    pub book_b: String,
    pub odds_a: f64,
    pub odds_b: f64,
    pub arb_percentage: f64,
    pub total_stake: sqlx::types::BigDecimal,
    pub stake_a: sqlx::types::BigDecimal,
    pub stake_b: sqlx::types::BigDecimal,
    pub source_updated_at: Option<DateTime<Utc>>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Deserialize)]
pub struct ArbitrageQuery {
    pub event_id: Option<Uuid>,
    pub pipeline_match_id: Option<String>,
    pub market: Option<String>,
    pub min_arb_pct: Option<f64>,
    pub limit: Option<i64>,
}

pub async fn get_arbitrage(pool: web::Data<PgPool>, query: web::Query<ArbitrageQuery>) -> AppResult<HttpResponse> {
    let mut qb: QueryBuilder<Postgres> = QueryBuilder::new(
        "SELECT id, event_id, pipeline_match_id, market, selection_a, selection_b, book_a, book_b, odds_a, odds_b, arb_percentage, total_stake, stake_a, stake_b, source_updated_at, created_at FROM arbitrage",
    );

    let mut has_where = false;

    if let Some(event_id) = query.event_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("event_id = ").push_bind(event_id);
    }

    if let Some(ref pipeline_match_id) = query.pipeline_match_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("pipeline_match_id = ").push_bind(pipeline_match_id);
    }

    if let Some(ref market) = query.market {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("market = ").push_bind(market);
    }

    if let Some(min_arb_pct) = query.min_arb_pct {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        qb.push("arb_percentage >= ").push_bind(min_arb_pct);
    }

    qb.push(" ORDER BY arb_percentage DESC, created_at DESC");

    let limit = query.limit.unwrap_or(200).clamp(1, 2000);
    qb.push(" LIMIT ").push_bind(limit);

    let rows: Vec<ArbitrageRow> = qb.build_query_as().fetch_all(pool.get_ref()).await?;
    Ok(HttpResponse::Ok().json(rows))
}
