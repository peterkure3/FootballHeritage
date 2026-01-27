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
    pub event_home_team: Option<String>,
    pub event_away_team: Option<String>,
    pub event_date: Option<DateTime<Utc>>,
    pub bookmaker: String,
    pub market: String,
    pub outcome_a: String,
    pub outcome_b: String,
    pub odds_a: f64,
    pub odds_b: f64,
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
        "SELECT d.id, d.event_id, d.pipeline_match_id, e.home_team as event_home_team, e.away_team as event_away_team, e.event_date as event_date, d.bookmaker, d.market, d.outcome_a, d.outcome_b, d.odds_a, d.odds_b, d.fair_prob_a, d.fair_prob_b, d.vig, d.source_updated_at, d.created_at FROM devigged_odds d LEFT JOIN events e ON e.id = d.event_id",
    );

    let mut has_where = false;

    if let Some(event_id) = query.event_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("d.event_id = ").push_bind(event_id);
    }

    if let Some(ref pipeline_match_id) = query.pipeline_match_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("d.pipeline_match_id = ").push_bind(pipeline_match_id);
    }

    if let Some(ref bookmaker) = query.bookmaker {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("d.bookmaker = ").push_bind(bookmaker);
    }

    if let Some(ref market) = query.market {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        qb.push("d.market = ").push_bind(market);
    }

    qb.push(" ORDER BY d.created_at DESC");

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
    pub event_home_team: Option<String>,
    pub event_away_team: Option<String>,
    pub event_date: Option<DateTime<Utc>>,
    pub bookmaker: Option<String>,
    pub market: String,
    pub selection: String,
    pub odds: f64,
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
        "SELECT b.id, b.event_id, b.pipeline_match_id, e.home_team as event_home_team, e.away_team as event_away_team, e.event_date as event_date, b.bookmaker, b.market, b.selection, b.odds, b.stake, b.true_probability, b.expected_value, b.expected_value_pct, b.source_updated_at, b.created_at FROM ev_bets b LEFT JOIN events e ON e.id = b.event_id",
    );

    let mut has_where = false;

    if let Some(event_id) = query.event_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("b.event_id = ").push_bind(event_id);
    }

    if let Some(ref pipeline_match_id) = query.pipeline_match_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("b.pipeline_match_id = ").push_bind(pipeline_match_id);
    }

    if let Some(ref bookmaker) = query.bookmaker {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("b.bookmaker = ").push_bind(bookmaker);
    }

    if let Some(ref market) = query.market {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("b.market = ").push_bind(market);
    }

    if let Some(min_ev_pct) = query.min_ev_pct {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        qb.push("b.expected_value_pct >= ").push_bind(min_ev_pct);
    }

    qb.push(" ORDER BY b.expected_value_pct DESC, b.created_at DESC");

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
    pub event_home_team: Option<String>,
    pub event_away_team: Option<String>,
    pub event_date: Option<DateTime<Utc>>,
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
        "SELECT a.id, a.event_id, a.pipeline_match_id, e.home_team as event_home_team, e.away_team as event_away_team, e.event_date as event_date, a.market, a.selection_a, a.selection_b, a.book_a, a.book_b, a.odds_a, a.odds_b, a.arb_percentage, a.total_stake, a.stake_a, a.stake_b, a.source_updated_at, a.created_at FROM arbitrage a LEFT JOIN events e ON e.id = a.event_id",
    );

    let mut has_where = false;

    if let Some(event_id) = query.event_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("a.event_id = ").push_bind(event_id);
    }

    if let Some(ref pipeline_match_id) = query.pipeline_match_id {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("a.pipeline_match_id = ").push_bind(pipeline_match_id);
    }

    if let Some(ref market) = query.market {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        has_where = true;
        qb.push("a.market = ").push_bind(market);
    }

    if let Some(min_arb_pct) = query.min_arb_pct {
        qb.push(if !has_where { " WHERE " } else { " AND " });
        qb.push("a.arb_percentage >= ").push_bind(min_arb_pct);
    }

    qb.push(" ORDER BY a.arb_percentage DESC, a.created_at DESC");

    let limit = query.limit.unwrap_or(200).clamp(1, 2000);
    qb.push(" LIMIT ").push_bind(limit);

    let rows: Vec<ArbitrageRow> = qb.build_query_as().fetch_all(pool.get_ref()).await?;
    Ok(HttpResponse::Ok().json(rows))
}
