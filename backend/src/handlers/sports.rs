use actix_web::{web, HttpResponse};
use serde::Serialize;
use sqlx::PgPool;
use std::collections::HashMap;

// ============================================================================
// RESPONSE TYPES
// ============================================================================

#[derive(Debug, Serialize)]
pub struct SportsResponse {
    pub sports: Vec<SportInfo>,
    pub total_events: i64,
}

#[derive(Debug, Serialize)]
pub struct SportInfo {
    pub name: String,
    pub display_name: String,
    pub icon: String,
    pub event_count: i64,
    pub leagues: Vec<LeagueInfo>,
    pub active: bool,
}

#[derive(Debug, Serialize, Clone)]
pub struct LeagueInfo {
    pub name: String,
    pub sport: String,
    pub event_count: i64,
    pub upcoming_events: i64,
}

#[derive(Debug, Serialize)]
pub struct BetCategoriesResponse {
    pub categories: Vec<BetCategory>,
}

#[derive(Debug, Serialize)]
pub struct BetCategory {
    pub id: String,
    pub name: String,
    pub description: String,
    pub icon: String,
    pub example: String,
}

// ============================================================================
// HANDLERS
// ============================================================================

/**
 * GET /api/v1/sports
 * 
 * Get all supported sports with event counts and leagues
 */
pub async fn get_sports(pool: web::Data<PgPool>) -> HttpResponse {
    // Query sports with event counts
    // Filter out expired events (event_date <= NOW())
    let sports_query = sqlx::query!(
        r#"
        SELECT 
            sport,
            COUNT(*) as event_count,
            COUNT(*) FILTER (WHERE status = 'UPCOMING') as upcoming_count
        FROM events
        WHERE status IN ('UPCOMING', 'LIVE')
        AND event_date > NOW()
        GROUP BY sport
        ORDER BY event_count DESC
        "#
    )
    .fetch_all(pool.get_ref())
    .await;

    let sports_data = match sports_query {
        Ok(data) => data,
        Err(e) => {
            eprintln!("Database error fetching sports: {}", e);
            return HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to fetch sports data"
            }));
        }
    };

    // Query leagues per sport
    // Filter out expired events (event_date <= NOW())
    let leagues_query = sqlx::query!(
        r#"
        SELECT 
            sport,
            league,
            COUNT(*) as event_count,
            COUNT(*) FILTER (WHERE status = 'UPCOMING') as upcoming_count
        FROM events
        WHERE status IN ('UPCOMING', 'LIVE')
        AND event_date > NOW()
        GROUP BY sport, league
        ORDER BY sport, event_count DESC
        "#
    )
    .fetch_all(pool.get_ref())
    .await;

    let leagues_data = match leagues_query {
        Ok(data) => data,
        Err(e) => {
            eprintln!("Database error fetching leagues: {}", e);
            return HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to fetch leagues data"
            }));
        }
    };

    // Group leagues by sport
    let mut leagues_by_sport: HashMap<String, Vec<LeagueInfo>> = HashMap::new();
    for league in leagues_data {
        let league_info = LeagueInfo {
            name: league.league.clone(),
            sport: league.sport.clone(),
            event_count: league.event_count.unwrap_or(0),
            upcoming_events: league.upcoming_count.unwrap_or(0),
        };

        leagues_by_sport
            .entry(league.sport)
            .or_insert_with(Vec::new)
            .push(league_info);
    }

    // Build sports list with metadata
    let sports: Vec<SportInfo> = sports_data
        .iter()
        .map(|sport| {
            let (display_name, icon) = get_sport_metadata(&sport.sport);
            
            SportInfo {
                name: sport.sport.clone(),
                display_name,
                icon,
                event_count: sport.event_count.unwrap_or(0),
                leagues: leagues_by_sport
                    .get(&sport.sport)
                    .cloned()
                    .unwrap_or_default(),
                active: sport.upcoming_count.unwrap_or(0) > 0,
            }
        })
        .collect();

    let total_events: i64 = sports.iter().map(|s| s.event_count).sum();

    HttpResponse::Ok().json(SportsResponse {
        sports,
        total_events,
    })
}

/**
 * GET /api/v1/sports/categories
 * 
 * Get all bet categories/types
 */
pub async fn get_bet_categories() -> HttpResponse {
    let categories = vec![
        BetCategory {
            id: "moneyline".to_string(),
            name: "Moneyline".to_string(),
            description: "Bet on which team will win the game outright".to_string(),
            icon: "🎯".to_string(),
            example: "Chiefs -150 (bet $150 to win $100)".to_string(),
        },
        BetCategory {
            id: "spread".to_string(),
            name: "Point Spread".to_string(),
            description: "Bet on the margin of victory".to_string(),
            icon: "📊".to_string(),
            example: "Chiefs -7.5 at -110 (Chiefs must win by 8+)".to_string(),
        },
        BetCategory {
            id: "total".to_string(),
            name: "Over/Under".to_string(),
            description: "Bet on total combined points scored".to_string(),
            icon: "🔢".to_string(),
            example: "Over 47.5 at -110 (total points > 47.5)".to_string(),
        },
        BetCategory {
            id: "props".to_string(),
            name: "Player Props".to_string(),
            description: "Bet on individual player statistics".to_string(),
            icon: "⭐".to_string(),
            example: "Mahomes Over 2.5 TD passes".to_string(),
        },
        BetCategory {
            id: "futures".to_string(),
            name: "Futures".to_string(),
            description: "Bet on season-long outcomes".to_string(),
            icon: "🏆".to_string(),
            example: "Chiefs to win Super Bowl +600".to_string(),
        },
        BetCategory {
            id: "parlays".to_string(),
            name: "Parlays".to_string(),
            description: "Combine multiple bets for higher payouts".to_string(),
            icon: "🎲".to_string(),
            example: "3-team parlay: Chiefs ML + Over 47.5 + Lakers ML".to_string(),
        },
    ];

    HttpResponse::Ok().json(BetCategoriesResponse { categories })
}

/**
 * GET /api/v1/sports/:sport/leagues
 * 
 * Get leagues for a specific sport
 */
pub async fn get_sport_leagues(
    pool: web::Data<PgPool>,
    sport: web::Path<String>,
) -> HttpResponse {
    let sport_name = sport.into_inner();

    // Filter out expired events (event_date <= NOW())
    let leagues = sqlx::query!(
        r#"
        SELECT 
            league,
            COUNT(*) as event_count,
            COUNT(*) FILTER (WHERE status = 'UPCOMING') as upcoming_count,
            MIN(event_date) as next_event
        FROM events
        WHERE sport = $1 
        AND status IN ('UPCOMING', 'LIVE')
        AND event_date > NOW()
        GROUP BY league
        ORDER BY event_count DESC
        "#,
        sport_name
    )
    .fetch_all(pool.get_ref())
    .await;

    match leagues {
        Ok(data) => {
            let leagues: Vec<serde_json::Value> = data
                .iter()
                .map(|league| {
                    serde_json::json!({
                        "name": league.league,
                        "sport": sport_name,
                        "event_count": league.event_count.unwrap_or(0),
                        "upcoming_events": league.upcoming_count.unwrap_or(0),
                        "next_event": league.next_event,
                    })
                })
                .collect();

            HttpResponse::Ok().json(serde_json::json!({
                "sport": sport_name,
                "leagues": leagues,
            }))
        }
        Err(e) => {
            eprintln!("Database error fetching leagues: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to fetch leagues"
            }))
        }
    }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get display name and icon for a sport
 */
fn get_sport_metadata(sport: &str) -> (String, String) {
    match sport.to_uppercase().as_str() {
        "NFL" | "FOOTBALL" => ("NFL Football".to_string(), "🏈".to_string()),
        "NBA" | "BASKETBALL" => ("NBA Basketball".to_string(), "🏀".to_string()),
        "MLB" | "BASEBALL" => ("MLB Baseball".to_string(), "⚾".to_string()),
        "NHL" | "HOCKEY" => ("NHL Hockey".to_string(), "🏒".to_string()),
        "SOCCER" | "FOOTBALL_SOCCER" => ("Soccer".to_string(), "⚽".to_string()),
        "MMA" | "UFC" => ("MMA / UFC".to_string(), "🥊".to_string()),
        "BOXING" => ("Boxing".to_string(), "🥊".to_string()),
        "TENNIS" => ("Tennis".to_string(), "🎾".to_string()),
        "GOLF" => ("Golf".to_string(), "⛳".to_string()),
        "ESPORTS" => ("eSports".to_string(), "🎮".to_string()),
        _ => (sport.to_string(), "🏅".to_string()),
    }
}
