"""What-if matchup prediction endpoint."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))


from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import LOG_LEVEL
from etl.utils import setup_logger
from api.db import get_db_connection

logger = setup_logger(__name__, LOG_LEVEL)

router = APIRouter()


class WhatIfPredictionResponse(BaseModel):
    home_team: str
    away_team: str
    winner: str
    home_prob: float
    draw_prob: float
    away_prob: float
    model_version: str
    confidence: str
    recommendation: str

@router.get("/predict-matchup", response_model=WhatIfPredictionResponse)
def predict_matchup(
    home_team: str = Query(..., description="Home team name"),
    away_team: str = Query(..., description="Away team name")
):
    """
    Predict outcome for any two teams (What-If scenario).
    
    Uses enhanced v2 model with:
    - ELO ratings
    - Head-to-head history
    - Weighted form
    - Venue-specific stats
    - Odds-derived features
    - Probability calibration
    - Ensemble model (stacking)
    
    Args:
        home_team: Name of the home team
        away_team: Name of the away team
    
    Returns:
        Prediction with probabilities and recommendation
    
    Example:
        /api/v1/predict-matchup?home_team=Arsenal&away_team=Chelsea
    """
    try:
        import joblib
        import pandas as pd
        import numpy as np
        from pathlib import Path
        
        model_dir = Path(__file__).parent.parent / "models" / "model_store"
        
        # Try v2 model first, fallback to v1
        model_version = "2.0.0"
        model_path = model_dir / f"model_v{model_version}.pkl"
        if not model_path.exists():
            model_version = "1.0.0"
            model_path = model_dir / f"model_v{model_version}.pkl"
        
        features_path = model_dir / f"features_v{model_version}.pkl"
        label_encoder_path = model_dir / f"label_encoder_v{model_version}.pkl"
        
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail="Model not trained yet. Please run: python -m models.train_model_v2"
            )
        
        model = joblib.load(model_path)
        feature_names = joblib.load(features_path)
        label_encoder = joblib.load(label_encoder_path)
        
        engine = get_db_connection()
        
        # Enhanced team stats with more metrics
        def get_team_stats(team_name, window=10):
            query = text("""
                WITH recent_matches AS (
                    SELECT 
                        home_team, away_team, result, home_score, away_score, date,
                        CASE WHEN home_team ILIKE :team THEN 'home' ELSE 'away' END as team_side
                    FROM matches
                    WHERE (home_team ILIKE :team OR away_team ILIKE :team)
                        AND result IS NOT NULL
                        AND home_score IS NOT NULL
                    ORDER BY date DESC
                    LIMIT :window
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
                    'wins': result[1] or 0,
                    'draws': result[2] or 0,
                    'losses': result[3] or 0,
                    'avg_gd': float(result[4] or 0.0),
                    'avg_goals_for': float(result[5] or 1.5),
                    'avg_goals_against': float(result[6] or 1.5),
                    'win_rate': (result[1] or 0) / total,
                    'form_points': ((result[1] or 0) * 3 + (result[2] or 0)) / (total * 3),
                }
            return {'wins': 0, 'draws': 0, 'losses': 0, 'avg_gd': 0.0, 
                    'avg_goals_for': 1.5, 'avg_goals_against': 1.5, 'win_rate': 0.33, 'form_points': 0.33}
        
        # Get venue-specific stats
        def get_venue_stats(team_name, is_home, window=20):
            if is_home:
                query = text("""
                    WITH recent AS (
                        SELECT result, home_score FROM matches 
                        WHERE home_team ILIKE :team AND result IS NOT NULL
                        ORDER BY date DESC LIMIT :window
                    )
                    SELECT COUNT(*) as matches,
                           COUNT(CASE WHEN result = 'home_win' THEN 1 END) as wins,
                           AVG(home_score) as avg_goals
                    FROM recent
                """)
            else:
                query = text("""
                    WITH recent AS (
                        SELECT result, away_score FROM matches 
                        WHERE away_team ILIKE :team AND result IS NOT NULL
                        ORDER BY date DESC LIMIT :window
                    )
                    SELECT COUNT(*) as matches,
                           COUNT(CASE WHEN result = 'away_win' THEN 1 END) as wins,
                           AVG(away_score) as avg_goals
                    FROM recent
                """)
            
            with engine.connect() as conn:
                result = conn.execute(query, {"team": f"%{team_name}%", "window": window}).fetchone()
            
            if result and result[0] > 0:
                return {'win_rate': (result[1] or 0) / result[0], 'avg_goals': float(result[2] or 1.5)}
            return {'win_rate': 0.5 if is_home else 0.33, 'avg_goals': 1.5}
        
        # Get head-to-head stats
        def get_h2h_stats(home, away, window=10):
            query = text("""
                SELECT home_team, away_team, result, home_score, away_score
                FROM matches
                WHERE ((home_team ILIKE :home AND away_team ILIKE :away) OR
                       (home_team ILIKE :away AND away_team ILIKE :home))
                    AND result IS NOT NULL
                ORDER BY date DESC LIMIT :window
            """)
            
            with engine.connect() as conn:
                results = conn.execute(query, {"home": f"%{home}%", "away": f"%{away}%", "window": window}).fetchall()
            
            if not results:
                return {'home_wins': 0, 'draws': 0, 'away_wins': 0, 'home_goals_avg': 1.5, 'away_goals_avg': 1.5}
            
            home_wins, draws, away_wins = 0, 0, 0
            home_goals, away_goals = [], []
            
            for row in results:
                match_home, match_away, result, h_score, a_score = row
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
        
        # Calculate ELO ratings
        def get_elo_ratings():
            query = text("""
                SELECT home_team, away_team, result FROM matches
                WHERE result IS NOT NULL ORDER BY date ASC
            """)
            
            with engine.connect() as conn:
                df = pd.read_sql(query, conn)
            
            elo = {}
            K, HOME_ADV, INIT = 32, 100, 1500
            
            for _, row in df.iterrows():
                h, a, r = row["home_team"], row["away_team"], row["result"]
                h_elo = elo.get(h, INIT)
                a_elo = elo.get(a, INIT)
                h_exp = 1 / (1 + 10 ** ((a_elo - h_elo - HOME_ADV) / 400))
                h_act = 1.0 if r == "home_win" else (0.5 if r == "draw" else 0.0)
                elo[h] = h_elo + K * (h_act - h_exp)
                elo[a] = a_elo + K * ((1 - h_act) - (1 - h_exp))
            
            return elo
        
        # Gather all stats
        home_stats = get_team_stats(home_team)
        away_stats = get_team_stats(away_team)
        home_venue = get_venue_stats(home_team, is_home=True)
        away_venue = get_venue_stats(away_team, is_home=False)
        h2h = get_h2h_stats(home_team, away_team)
        elo_ratings = get_elo_ratings()
        
        home_elo = elo_ratings.get(home_team, 1500)
        away_elo = elo_ratings.get(away_team, 1500)
        elo_diff = home_elo - away_elo + 100
        home_expected = 1 / (1 + 10 ** ((away_elo - home_elo - 100) / 400))
        
        # Get odds (try to find specific or use averages)
        odds_query = text("""
            SELECT AVG(home_win), AVG(draw), AVG(away_win) FROM odds WHERE home_win IS NOT NULL
        """)
        with engine.connect() as conn:
            odds_result = conn.execute(odds_query).fetchone()
        
        home_odds = float(odds_result[0]) if odds_result and odds_result[0] else 2.5
        draw_odds = float(odds_result[1]) if odds_result and odds_result[1] else 3.2
        away_odds = float(odds_result[2]) if odds_result and odds_result[2] else 2.8
        
        # Calculate odds-derived features
        implied_home = 1 / home_odds
        implied_draw = 1 / draw_odds
        implied_away = 1 / away_odds
        overround = implied_home + implied_draw + implied_away
        fair_home = implied_home / overround
        fair_draw = implied_draw / overround
        fair_away = implied_away / overround
        
        # Build comprehensive feature vector
        features = {
            # Odds-derived (strongest signals)
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
            # ELO
            'home_elo': home_elo,
            'away_elo': away_elo,
            'elo_diff': elo_diff,
            'home_expected': home_expected,
            # H2H
            'h2h_home_wins': h2h['home_wins'],
            'h2h_draws': h2h['draws'],
            'h2h_away_wins': h2h['away_wins'],
            'h2h_home_goals_avg': h2h['home_goals_avg'],
            'h2h_away_goals_avg': h2h['away_goals_avg'],
            # Weighted form
            'home_weighted_form': home_stats['form_points'] * 3,
            'away_weighted_form': away_stats['form_points'] * 3,
            'home_weighted_goals_for': home_stats['avg_goals_for'],
            'home_weighted_goals_against': home_stats['avg_goals_against'],
            'away_weighted_goals_for': away_stats['avg_goals_for'],
            'away_weighted_goals_against': away_stats['avg_goals_against'],
            # Venue
            'home_team_home_win_rate': home_venue['win_rate'],
            'home_team_home_goals_avg': home_venue['avg_goals'],
            'away_team_away_win_rate': away_venue['win_rate'],
            'away_team_away_goals_avg': away_venue['avg_goals'],
            # Original form
            'home_team_wins_last_n': home_stats['wins'],
            'home_team_draws_last_n': home_stats['draws'],
            'home_team_losses_last_n': home_stats['losses'],
            'away_team_wins_last_n': away_stats['wins'],
            'away_team_draws_last_n': away_stats['draws'],
            'away_team_losses_last_n': away_stats['losses'],
            'home_team_avg_gd_last_n': home_stats['avg_gd'],
            'away_team_avg_gd_last_n': away_stats['avg_gd'],
            'home_win': home_odds,
            'draw': draw_odds,
            'away_win': away_odds,
        }
        
        # Create DataFrame with correct feature order
        X = pd.DataFrame([{k: features.get(k, 0) for k in feature_names}])
        X = X.fillna(0)
        
        # Make prediction
        probabilities = model.predict_proba(X)[0]
        predicted_class = model.predict(X)[0]
        winner = label_encoder.inverse_transform([predicted_class])[0]
        
        prob_dict = dict(zip(label_encoder.classes_, probabilities))
        home_prob = prob_dict.get('home_win', 0.0)
        draw_prob = prob_dict.get('draw', 0.0)
        away_prob = prob_dict.get('away_win', 0.0)
        
        # Confidence based on probability spread
        max_prob = max(home_prob, draw_prob, away_prob)
        if max_prob > 0.55:
            confidence = "High"
        elif max_prob > 0.42:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        # Generate detailed recommendation
        if winner == 'home_win':
            recommendation = f"{home_team} is favored to win at home ({home_prob*100:.1f}%)"
        elif winner == 'away_win':
            recommendation = f"{away_team} is favored to win away ({away_prob*100:.1f}%)"
        else:
            recommendation = f"Match likely to end in a draw ({draw_prob*100:.1f}%)"
        
        # Add ELO context
        if abs(home_elo - away_elo) > 100:
            stronger = home_team if home_elo > away_elo else away_team
            recommendation += f". {stronger} has a significant ELO advantage."
        
        # Add form context
        if home_stats['wins'] >= 4:
            recommendation += f" {home_team} is in excellent form ({home_stats['wins']} wins in last 10)."
        elif home_stats['losses'] >= 4:
            recommendation += f" {home_team} is struggling ({home_stats['losses']} losses in last 10)."
        
        if away_stats['wins'] >= 4:
            recommendation += f" {away_team} is in great form ({away_stats['wins']} wins in last 10)."
        elif away_stats['losses'] >= 4:
            recommendation += f" {away_team} has been losing ({away_stats['losses']} losses in last 10)."
        
        # Add H2H context
        if h2h['home_wins'] + h2h['draws'] + h2h['away_wins'] >= 3:
            if h2h['home_wins'] > h2h['away_wins']:
                recommendation += f" H2H favors {home_team} ({h2h['home_wins']}-{h2h['draws']}-{h2h['away_wins']})."
            elif h2h['away_wins'] > h2h['home_wins']:
                recommendation += f" H2H favors {away_team} ({h2h['away_wins']}-{h2h['draws']}-{h2h['home_wins']})."
        
        return WhatIfPredictionResponse(
            home_team=home_team,
            away_team=away_team,
            winner=winner,
            home_prob=float(home_prob),
            draw_prob=float(draw_prob),
            away_prob=float(away_prob),
            model_version=model_version,
            confidence=confidence,
            recommendation=recommendation
        )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model files not found. Please train the model first."
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

