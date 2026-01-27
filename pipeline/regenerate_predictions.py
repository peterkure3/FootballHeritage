"""
Regenerate predictions for all upcoming matches using the v2 model.
This updates the predictions table in the database.
"""

import sys
from pathlib import Path
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

sys.path.append(str(Path(__file__).parent))

from config import DATABASE_URI, MODEL_DIR, LOG_LEVEL
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

MODEL_VERSION = "2.0.0"
ELO_K_FACTOR = 32
ELO_HOME_ADVANTAGE = 100
ELO_INITIAL = 1500


def get_elo_ratings(engine) -> dict:
    """Calculate ELO ratings from match history."""
    query = text("""
        SELECT home_team, away_team, result FROM matches
        WHERE result IS NOT NULL ORDER BY date ASC
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    elo = {}
    for _, row in df.iterrows():
        h, a, r = row["home_team"], row["away_team"], row["result"]
        h_elo = elo.get(h, ELO_INITIAL)
        a_elo = elo.get(a, ELO_INITIAL)
        h_exp = 1 / (1 + 10 ** ((a_elo - h_elo - ELO_HOME_ADVANTAGE) / 400))
        h_act = 1.0 if r == "home_win" else (0.5 if r == "draw" else 0.0)
        elo[h] = h_elo + ELO_K_FACTOR * (h_act - h_exp)
        elo[a] = a_elo + ELO_K_FACTOR * ((1 - h_act) - (1 - h_exp))
    
    return elo


def get_team_stats(engine, team_name: str, window: int = 10) -> dict:
    """Get team statistics."""
    query = text("""
        WITH recent_matches AS (
            SELECT 
                home_team, away_team, result, home_score, away_score,
                CASE WHEN home_team ILIKE :team THEN 'home' ELSE 'away' END as team_side
            FROM matches
            WHERE (home_team ILIKE :team OR away_team ILIKE :team)
                AND result IS NOT NULL AND home_score IS NOT NULL
            ORDER BY date DESC LIMIT :window
        )
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN (team_side='home' AND result='home_win') OR (team_side='away' AND result='away_win') THEN 1 END) as wins,
            COUNT(CASE WHEN result = 'draw' THEN 1 END) as draws,
            COUNT(CASE WHEN (team_side='home' AND result='away_win') OR (team_side='away' AND result='home_win') THEN 1 END) as losses,
            AVG(CASE WHEN team_side='home' THEN home_score - away_score ELSE away_score - home_score END) as avg_gd,
            AVG(CASE WHEN team_side='home' THEN home_score ELSE away_score END) as avg_goals_for,
            AVG(CASE WHEN team_side='home' THEN away_score ELSE home_score END) as avg_goals_against
        FROM recent_matches
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"team": f"%{team_name}%", "window": window}).fetchone()
    
    if result and result[0] > 0:
        total = result[0]
        return {
            'wins': result[1] or 0, 'draws': result[2] or 0, 'losses': result[3] or 0,
            'avg_gd': float(result[4] or 0.0),
            'avg_goals_for': float(result[5] or 1.5),
            'avg_goals_against': float(result[6] or 1.5),
            'win_rate': (result[1] or 0) / total,
            'form_points': ((result[1] or 0) * 3 + (result[2] or 0)) / (total * 3),
        }
    return {'wins': 0, 'draws': 0, 'losses': 0, 'avg_gd': 0.0, 
            'avg_goals_for': 1.5, 'avg_goals_against': 1.5, 'win_rate': 0.33, 'form_points': 0.33}


def get_venue_stats(engine, team_name: str, is_home: bool) -> dict:
    """Get venue-specific stats."""
    if is_home:
        query = text("""
            SELECT COUNT(*) as matches, COUNT(CASE WHEN result = 'home_win' THEN 1 END) as wins,
                   AVG(home_score) as avg_goals
            FROM matches WHERE home_team ILIKE :team AND result IS NOT NULL
        """)
    else:
        query = text("""
            SELECT COUNT(*) as matches, COUNT(CASE WHEN result = 'away_win' THEN 1 END) as wins,
                   AVG(away_score) as avg_goals
            FROM matches WHERE away_team ILIKE :team AND result IS NOT NULL
        """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"team": f"%{team_name}%"}).fetchone()
    
    if result and result[0] > 0:
        return {'win_rate': (result[1] or 0) / result[0], 'avg_goals': float(result[2] or 1.5)}
    return {'win_rate': 0.5 if is_home else 0.33, 'avg_goals': 1.5}


def get_h2h_stats(engine, home: str, away: str) -> dict:
    """Get head-to-head stats."""
    query = text("""
        SELECT home_team, away_team, result, home_score, away_score
        FROM matches
        WHERE ((home_team ILIKE :home AND away_team ILIKE :away) OR
               (home_team ILIKE :away AND away_team ILIKE :home))
            AND result IS NOT NULL
        ORDER BY date DESC LIMIT 10
    """)
    
    with engine.connect() as conn:
        results = conn.execute(query, {"home": f"%{home}%", "away": f"%{away}%"}).fetchall()
    
    if not results:
        return {'home_wins': 0, 'draws': 0, 'away_wins': 0, 'home_goals_avg': 1.5, 'away_goals_avg': 1.5}
    
    home_wins, draws, away_wins = 0, 0, 0
    home_goals, away_goals = [], []
    
    for row in results:
        match_home, _, result, h_score, a_score = row
        if home.lower() in match_home.lower():
            home_goals.append(h_score or 0)
            away_goals.append(a_score or 0)
            if result == "home_win": home_wins += 1
            elif result == "draw": draws += 1
            else: away_wins += 1
        else:
            home_goals.append(a_score or 0)
            away_goals.append(h_score or 0)
            if result == "away_win": home_wins += 1
            elif result == "draw": draws += 1
            else: away_wins += 1
    
    return {
        'home_wins': home_wins, 'draws': draws, 'away_wins': away_wins,
        'home_goals_avg': np.mean(home_goals) if home_goals else 1.5,
        'away_goals_avg': np.mean(away_goals) if away_goals else 1.5,
    }


def build_features(match, engine, elo_ratings, feature_names, avg_odds) -> pd.DataFrame:
    """Build feature vector for a match."""
    home_team = match['home_team']
    away_team = match['away_team']
    
    home_stats = get_team_stats(engine, home_team)
    away_stats = get_team_stats(engine, away_team)
    home_venue = get_venue_stats(engine, home_team, is_home=True)
    away_venue = get_venue_stats(engine, away_team, is_home=False)
    h2h = get_h2h_stats(engine, home_team, away_team)
    
    home_elo = elo_ratings.get(home_team, ELO_INITIAL)
    away_elo = elo_ratings.get(away_team, ELO_INITIAL)
    elo_diff = home_elo - away_elo + ELO_HOME_ADVANTAGE
    home_expected = 1 / (1 + 10 ** ((away_elo - home_elo - ELO_HOME_ADVANTAGE) / 400))
    
    # Use match-specific odds if available, otherwise use averages
    home_odds = match.get('home_win_odds') or avg_odds['home']
    draw_odds = match.get('draw_odds') or avg_odds['draw']
    away_odds = match.get('away_win_odds') or avg_odds['away']
    
    # Calculate fair probabilities
    implied_home = 1 / home_odds if home_odds > 0 else 0.4
    implied_draw = 1 / draw_odds if draw_odds > 0 else 0.25
    implied_away = 1 / away_odds if away_odds > 0 else 0.35
    overround = implied_home + implied_draw + implied_away
    fair_home = implied_home / overround if overround > 0 else 0.4
    fair_draw = implied_draw / overround if overround > 0 else 0.25
    fair_away = implied_away / overround if overround > 0 else 0.35
    
    features = {
        'fair_home_prob': fair_home,
        'fair_draw_prob': fair_draw,
        'fair_away_prob': fair_away,
        'odds_ratio': home_odds / away_odds if away_odds > 0 else 1.0,
        'odds_spread': home_odds - away_odds,
        'log_home_odds': np.log(max(home_odds, 1.01)),
        'log_away_odds': np.log(max(away_odds, 1.01)),
        'log_draw_odds': np.log(max(draw_odds, 1.01)),
        'home_is_favorite': 1 if home_odds < away_odds else 0,
        'favorite_odds': min(home_odds, away_odds),
        'underdog_odds': max(home_odds, away_odds),
        'home_elo': home_elo,
        'away_elo': away_elo,
        'elo_diff': elo_diff,
        'home_expected': home_expected,
        'h2h_home_wins': h2h['home_wins'],
        'h2h_draws': h2h['draws'],
        'h2h_away_wins': h2h['away_wins'],
        'h2h_home_goals_avg': h2h['home_goals_avg'],
        'h2h_away_goals_avg': h2h['away_goals_avg'],
        'home_weighted_form': home_stats['form_points'] * 3,
        'away_weighted_form': away_stats['form_points'] * 3,
        'home_weighted_goals_for': home_stats['avg_goals_for'],
        'home_weighted_goals_against': home_stats['avg_goals_against'],
        'away_weighted_goals_for': away_stats['avg_goals_for'],
        'away_weighted_goals_against': away_stats['avg_goals_against'],
        'home_team_home_win_rate': home_venue['win_rate'],
        'home_team_home_goals_avg': home_venue['avg_goals'],
        'away_team_away_win_rate': away_venue['win_rate'],
        'away_team_away_goals_avg': away_venue['avg_goals'],
        'home_team_wins_last_n': home_stats['wins'],
        'home_team_draws_last_n': home_stats['draws'],
        'home_team_losses_last_n': home_stats['losses'],
        'away_team_wins_last_n': away_stats['wins'],
        'away_team_draws_last_n': away_stats['draws'],
        'away_team_losses_last_n': away_stats['losses'],
        'home_team_avg_gd_last_n': home_stats['avg_gd'],
        'away_team_avg_gd_last_n': away_stats['avg_gd'],
    }
    
    X = pd.DataFrame([{k: features.get(k, 0) for k in feature_names}])
    return X.fillna(0)


def regenerate_predictions():
    """Regenerate predictions for all matches."""
    logger.info("Starting prediction regeneration with v2 model")
    
    # Load model
    model_path = MODEL_DIR / f"model_v{MODEL_VERSION}.pkl"
    features_path = MODEL_DIR / f"features_v{MODEL_VERSION}.pkl"
    encoder_path = MODEL_DIR / f"label_encoder_v{MODEL_VERSION}.pkl"
    
    if not model_path.exists():
        logger.error(f"Model not found: {model_path}")
        return
    
    model = joblib.load(model_path)
    feature_names = joblib.load(features_path)
    label_encoder = joblib.load(encoder_path)
    
    logger.info(f"Loaded model v{MODEL_VERSION} with {len(feature_names)} features")
    
    engine = create_engine(DATABASE_URI)
    
    # Get ELO ratings
    logger.info("Calculating ELO ratings...")
    elo_ratings = get_elo_ratings(engine)
    logger.info(f"Calculated ELO for {len(elo_ratings)} teams")
    
    # Get average odds
    with engine.connect() as conn:
        odds_result = conn.execute(text(
            "SELECT AVG(home_win), AVG(draw), AVG(away_win) FROM odds WHERE home_win IS NOT NULL"
        )).fetchone()
    
    avg_odds = {
        'home': float(odds_result[0]) if odds_result and odds_result[0] else 2.5,
        'draw': float(odds_result[1]) if odds_result and odds_result[1] else 3.2,
        'away': float(odds_result[2]) if odds_result and odds_result[2] else 2.8,
    }
    
    # Get all matches (join with odds if available)
    with engine.connect() as conn:
        matches = pd.read_sql(text("""
            SELECT m.match_id, m.home_team, m.away_team,
                   AVG(o.home_win) as home_win_odds,
                   AVG(o.draw) as draw_odds,
                   AVG(o.away_win) as away_win_odds
            FROM matches m
            LEFT JOIN odds o ON m.match_id = o.match_id
            WHERE m.home_team IS NOT NULL AND m.away_team IS NOT NULL
            GROUP BY m.match_id, m.home_team, m.away_team
        """), conn)
    
    logger.info(f"Processing {len(matches)} matches...")
    
    predictions = []
    for idx, match in matches.iterrows():
        try:
            X = build_features(match, engine, elo_ratings, feature_names, avg_odds)
            
            probs = model.predict_proba(X)[0]
            pred_class = model.predict(X)[0]
            winner = label_encoder.inverse_transform([pred_class])[0]
            
            prob_dict = dict(zip(label_encoder.classes_, probs))
            
            predictions.append({
                'match_id': match['match_id'],
                'model_version': MODEL_VERSION,
                'winner': winner,
                'home_prob': float(prob_dict.get('home_win', 0.0)),
                'draw_prob': float(prob_dict.get('draw', 0.0)),
                'away_prob': float(prob_dict.get('away_win', 0.0)),
                'created_at': datetime.now(),
            })
            
            if (idx + 1) % 50 == 0:
                logger.info(f"Processed {idx + 1}/{len(matches)} matches")
                
        except Exception as e:
            logger.warning(f"Failed to predict match {match['match_id']}: {e}")
    
    if not predictions:
        logger.error("No predictions generated")
        return
    
    # Save to database
    logger.info(f"Saving {len(predictions)} predictions to database...")
    predictions_df = pd.DataFrame(predictions)
    
    with engine.begin() as conn:
        # Delete old predictions
        conn.execute(text("DELETE FROM predictions"))
        
        # Insert new predictions
        predictions_df.to_sql('predictions', conn, if_exists='append', index=False)
    
    logger.info("Prediction regeneration complete!")
    
    # Show sample of predictions
    sample = predictions_df.sample(min(5, len(predictions_df)))
    logger.info(f"Sample predictions:\n{sample[['match_id', 'winner', 'home_prob', 'draw_prob', 'away_prob']]}")
    
    # Show probability distribution
    logger.info(f"Home prob range: {predictions_df['home_prob'].min():.3f} - {predictions_df['home_prob'].max():.3f}")
    logger.info(f"Away prob range: {predictions_df['away_prob'].min():.3f} - {predictions_df['away_prob'].max():.3f}")
    logger.info(f"Draw prob range: {predictions_df['draw_prob'].min():.3f} - {predictions_df['draw_prob'].max():.3f}")


if __name__ == "__main__":
    regenerate_predictions()
