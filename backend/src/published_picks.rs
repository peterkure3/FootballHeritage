//! Read and rank published evidence using the application pool; never run inference.
use chrono::{DateTime, Duration, NaiveDate, Utc};
use serde_json::{json, Value};
use sqlx::PgPool;
use uuid::Uuid;

#[derive(sqlx::FromRow)]
struct Candidate {
    record_key: String,
    payload: Value,
    home_prob: f64,
    draw_prob: f64,
    away_prob: f64,
    published_at: DateTime<Utc>,
    version: i64,
}

fn rank_row(candidate: Candidate, now: DateTime<Utc>) -> Value {
    let payload = candidate.payload;
    let fixture = &payload["fixture"];
    let prediction = &payload["prediction"];
    let quotes: Vec<Value> = payload["quotes"]
        .as_array()
        .into_iter()
        .flatten()
        .filter(|quote| {
            quote["updated_at"]
                .as_str()
                .and_then(|value| DateTime::parse_from_rfc3339(value).ok())
                .is_some_and(|time| time <= now && time >= now - Duration::hours(24))
        })
        .cloned()
        .collect();
    json!({"match_id":fixture["match_id"],"home_team":fixture["home_team"],
        "away_team":fixture["away_team"],"competition":fixture["competition"],
        "match_date":fixture["date"],"model_version":prediction["model_version"],
        "prediction_created_at":prediction["created_at"],
        "home_prob":candidate.home_prob,"draw_prob":candidate.draw_prob,"away_prob":candidate.away_prob,
        "quotes":quotes,"published_at":candidate.published_at,"publication_version":candidate.version,
        "record_key":candidate.record_key})
}

/// None means no approved active-model manifest; empty picks mean no fresh evidence.
pub async fn visit_candidates(
    pool: &PgPool,
    stream: Uuid,
    competition: Option<&str>,
    date: Option<NaiveDate>,
    mut visit: impl FnMut(Value),
) -> Result<Option<(String, usize, DateTime<Utc>)>, sqlx::Error> {
    let mut transaction = pool.begin().await?;
    sqlx::query("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        .execute(&mut *transaction)
        .await?;
    sqlx::query("SET LOCAL statement_timeout = '5s'")
        .execute(&mut *transaction)
        .await?;
    let model: Option<String> = sqlx::query_scalar(
        "SELECT r.payload->>'model_version' FROM published.records r
         JOIN published.sources s USING(stream_id)
         WHERE r.stream_id=$1 AND s.enabled AND r.dataset='model_metadata'
           AND r.record_key='football:active-model' AND NOT r.deleted
           AND r.payload->>'schema_version'='1' AND r.payload->>'sport'='Football'
           AND length(r.payload->>'model_version') > 0",
    )
    .bind(stream)
    .fetch_optional(&mut *transaction)
    .await?;
    let Some(model) = model else {
        return Ok(None);
    };
    let now: DateTime<Utc> = sqlx::query_scalar("SELECT CURRENT_TIMESTAMP")
        .fetch_one(&mut *transaction)
        .await?;
    let mut after = String::new();
    let mut considered = 0_usize;
    // Keyset pages bound memory without silently truncating eligible fixtures.
    loop {
        let rows = sqlx::query_as::<_, Candidate>(
            "SELECT r.record_key,r.payload,r.published_at,r.version,
                (r.payload#>>'{prediction,home_prob}')::float8 AS home_prob,
                (r.payload#>>'{prediction,draw_prob}')::float8 AS draw_prob,
                (r.payload#>>'{prediction,away_prob}')::float8 AS away_prob
             FROM published.records r JOIN published.sources s USING(stream_id)
             WHERE r.stream_id=$1 AND s.enabled AND r.dataset='fixture_bundle'
               AND NOT r.deleted AND r.record_key>$2
               AND r.payload->>'schema_version'='1' AND r.payload->>'sport'='Football'
               AND r.payload#>>'{prediction,model_version}'=$3
               AND r.payload#>>'{prediction,match_id}'=r.payload->>'local_match_id'
               AND r.payload#>>'{fixture,match_id}'=r.payload->>'local_match_id'
               AND (r.payload#>>'{fixture,date}')::timestamptz > $6
               AND (r.payload#>>'{fixture,date}')::timestamptz <= $6 + INTERVAL '30 days'
               AND r.payload#>>'{fixture,result}' IS NULL
               AND UPPER(COALESCE(r.payload#>>'{fixture,status}','')) NOT IN
                   ('FINISHED','CANCELLED','CANCELED','POSTPONED','IN_PLAY','PAUSED')
               AND (r.payload#>>'{prediction,created_at}')::timestamptz >= $6 - INTERVAL '24 hours'
               AND (r.payload#>>'{prediction,created_at}')::timestamptz <= $6
               AND ($4::text IS NULL OR r.payload#>>'{fixture,competition}'=$4
                    OR r.payload#>>'{fixture,competition}'='UEFA ' || $4)
               AND ($5::date IS NULL OR
                    ((r.payload#>>'{fixture,date}')::timestamptz AT TIME ZONE 'UTC')::date=$5)
             ORDER BY r.record_key LIMIT 100",
        )
        .bind(stream)
        .bind(&after)
        .bind(&model)
        .bind(competition)
        .bind(date)
        .bind(now)
        .fetch_all(&mut *transaction)
        .await?;
        let count = rows.len();
        for row in rows {
            after.clone_from(&row.record_key);
            considered += 1;
            let value = rank_row(row, now);
            if crate::published::valid_probabilities(&value) {
                visit(value);
            }
        }
        if count < 100 {
            break;
        }
    }
    transaction.commit().await?;
    Ok(Some((model, considered, now)))
}

/// None means no approved active-model manifest; empty picks mean no fresh evidence.
pub async fn generate(
    pool: &PgPool,
    stream: Uuid,
    competition: Option<&str>,
    date: Option<NaiveDate>,
    limit: usize,
) -> Result<Option<Value>, sqlx::Error> {
    let mut picks = Vec::new();
    let result = visit_candidates(pool, stream, competition, date, |row| {
        let mut selected = crate::pick_selection::build_picks(std::slice::from_ref(&row), 1);
        for pick in &mut selected {
            pick["freshness"] = json!({"state":"fresh","published_at":row["published_at"],
                "generated_at":row["prediction_created_at"],"publication_version":row["publication_version"],
                "max_evidence_age_hours":24});
        }
        picks.extend(selected);
        picks = crate::pick_selection::rank(std::mem::take(&mut picks), limit);
    }).await?;
    let Some((model, considered, now)) = result else {
        return Ok(None);
    };
    let value_count = picks
        .iter()
        .filter(|pick| pick["pick_type"] == "value")
        .count();
    Ok(Some(json!({"picks":picks,"summary":{
        "fixtures_considered":considered,"value_picks":value_count,
        "prediction_picks":picks.len()-value_count,
        "message":if picks.is_empty(){"No recent published model predictions match these filters."}
            else{"Predictions ranked from the active model."}},
        "provenance":{"model":model,"criterion":"value_edge_then_model_probability",
            "min_edge":0.05,"max_evidence_age_hours":24,"reference_stake_units":1,
            "match_date_timezone":"UTC","odds_source":"stored_bookmaker_quotes",
            "data_source":"published_postgresql","stream_id":stream,"evaluated_at":now}})))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn quotes_require_observed_recent_timestamps() {
        let now = Utc::now();
        let row = rank_row(
            Candidate {
                record_key: "test-only".into(),
                home_prob: 0.5,
                draw_prob: 0.3,
                away_prob: 0.2,
                published_at: now,
                version: 1,
                payload: json!({"quotes":[
                {"bookmaker":"fresh","updated_at":now},
                {"bookmaker":"old","updated_at":now-Duration::hours(25)},
                {"bookmaker":"future","updated_at":now+Duration::seconds(1)},
                {"bookmaker":"unknown","updated_at":"invalid"}]}),
            },
            now,
        );
        assert_eq!(row["quotes"].as_array().unwrap().len(), 1);
        assert_eq!(row["quotes"][0]["bookmaker"], "fresh");
    }
}
