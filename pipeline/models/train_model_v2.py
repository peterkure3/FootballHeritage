"""
Enhanced model training with:
- ELO ratings
- Head-to-head history
- Weighted form (exponential decay)
- Venue-specific stats
- Odds-derived features (stronger signals)
- Probability calibration (isotonic regression)
- Ensemble model (stacking classifier)
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    StackingClassifier,
    RandomForestClassifier,
    GradientBoostingClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
import xgboost as xgb
import lightgbm as lgb

sys.path.append(str(Path(__file__).parent.parent))

from config import (
    MODEL_DIR,
    PROCESSED_DATA_DIR,
    LOG_LEVEL,
)
from etl.utils import setup_logger, ensure_dir, save_json

logger = setup_logger(__name__, LOG_LEVEL)

MODEL_VERSION = "2.0.0"

# ELO Configuration
ELO_K_FACTOR = 32
ELO_HOME_ADVANTAGE = 100
ELO_INITIAL = 1500


def calculate_elo_ratings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate ELO ratings for all teams based on match history.
    
    Args:
        df: DataFrame with match data sorted by date
    
    Returns:
        DataFrame with ELO ratings added
    """
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)
    
    # Initialize ELO ratings
    elo_ratings: Dict[str, float] = {}
    
    # Add columns for ELO
    df["home_elo"] = ELO_INITIAL
    df["away_elo"] = ELO_INITIAL
    df["elo_diff"] = 0.0
    df["home_expected"] = 0.5
    
    for idx, row in df.iterrows():
        home_team = row["home_team"]
        away_team = row["away_team"]
        
        # Get current ELO (or initialize)
        home_elo = elo_ratings.get(home_team, ELO_INITIAL)
        away_elo = elo_ratings.get(away_team, ELO_INITIAL)
        
        # Store pre-match ELO
        df.at[idx, "home_elo"] = home_elo
        df.at[idx, "away_elo"] = away_elo
        df.at[idx, "elo_diff"] = home_elo - away_elo + ELO_HOME_ADVANTAGE
        
        # Calculate expected score (with home advantage)
        home_expected = 1 / (1 + 10 ** ((away_elo - home_elo - ELO_HOME_ADVANTAGE) / 400))
        df.at[idx, "home_expected"] = home_expected
        
        # Update ELO based on result
        result = row.get("result")
        if result is not None and pd.notna(result):
            if result == "home_win":
                home_actual = 1.0
            elif result == "draw":
                home_actual = 0.5
            else:  # away_win
                home_actual = 0.0
            
            # Update ratings
            home_new = home_elo + ELO_K_FACTOR * (home_actual - home_expected)
            away_new = away_elo + ELO_K_FACTOR * ((1 - home_actual) - (1 - home_expected))
            
            elo_ratings[home_team] = home_new
            elo_ratings[away_team] = away_new
    
    logger.info(f"Calculated ELO ratings for {len(elo_ratings)} teams")
    return df


def calculate_head_to_head(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
    """
    Calculate head-to-head statistics between teams.
    
    Args:
        df: DataFrame with match data
        window: Number of recent H2H matches to consider
    
    Returns:
        DataFrame with H2H features added
    """
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)
    
    df["h2h_home_wins"] = 0
    df["h2h_draws"] = 0
    df["h2h_away_wins"] = 0
    df["h2h_home_goals_avg"] = 0.0
    df["h2h_away_goals_avg"] = 0.0
    
    # Create matchup key (sorted to handle both directions)
    def get_matchup_key(home, away):
        return tuple(sorted([home, away]))
    
    # Track H2H history
    h2h_history: Dict[tuple, List[dict]] = {}
    
    for idx, row in df.iterrows():
        home_team = row["home_team"]
        away_team = row["away_team"]
        key = get_matchup_key(home_team, away_team)
        
        # Get previous H2H matches
        prev_matches = h2h_history.get(key, [])[-window:]
        
        if prev_matches:
            home_wins = sum(1 for m in prev_matches if 
                          (m["home"] == home_team and m["result"] == "home_win") or
                          (m["away"] == home_team and m["result"] == "away_win"))
            away_wins = sum(1 for m in prev_matches if 
                          (m["home"] == away_team and m["result"] == "home_win") or
                          (m["away"] == away_team and m["result"] == "away_win"))
            draws = sum(1 for m in prev_matches if m["result"] == "draw")
            
            home_goals = []
            away_goals = []
            for m in prev_matches:
                if m["home"] == home_team:
                    home_goals.append(m.get("home_score", 0) or 0)
                    away_goals.append(m.get("away_score", 0) or 0)
                else:
                    home_goals.append(m.get("away_score", 0) or 0)
                    away_goals.append(m.get("home_score", 0) or 0)
            
            df.at[idx, "h2h_home_wins"] = home_wins
            df.at[idx, "h2h_draws"] = draws
            df.at[idx, "h2h_away_wins"] = away_wins
            df.at[idx, "h2h_home_goals_avg"] = np.mean(home_goals) if home_goals else 0
            df.at[idx, "h2h_away_goals_avg"] = np.mean(away_goals) if away_goals else 0
        
        # Add current match to history
        if key not in h2h_history:
            h2h_history[key] = []
        
        h2h_history[key].append({
            "home": home_team,
            "away": away_team,
            "result": row.get("result"),
            "home_score": row.get("home_score"),
            "away_score": row.get("away_score"),
        })
    
    logger.info("Calculated head-to-head features")
    return df


def calculate_weighted_form(df: pd.DataFrame, window: int = 10, decay: float = 0.9) -> pd.DataFrame:
    """
    Calculate exponentially weighted form (recent matches weighted more).
    
    Args:
        df: DataFrame with match data
        window: Number of recent matches
        decay: Exponential decay factor (0.9 = 10% decay per match)
    
    Returns:
        DataFrame with weighted form features
    """
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)
    
    df["home_weighted_form"] = 0.0
    df["away_weighted_form"] = 0.0
    df["home_weighted_goals_for"] = 0.0
    df["home_weighted_goals_against"] = 0.0
    df["away_weighted_goals_for"] = 0.0
    df["away_weighted_goals_against"] = 0.0
    
    # Track team history
    team_history: Dict[str, List[dict]] = {}
    
    for idx, row in df.iterrows():
        for team_type in ["home", "away"]:
            team = row[f"{team_type}_team"]
            
            # Get previous matches
            prev_matches = team_history.get(team, [])[-window:]
            
            if prev_matches:
                weights = [decay ** i for i in range(len(prev_matches) - 1, -1, -1)]
                total_weight = sum(weights)
                
                # Calculate weighted form (3 for win, 1 for draw, 0 for loss)
                form_values = []
                goals_for = []
                goals_against = []
                
                for m in prev_matches:
                    if m["is_home"]:
                        if m["result"] == "home_win":
                            form_values.append(3)
                        elif m["result"] == "draw":
                            form_values.append(1)
                        else:
                            form_values.append(0)
                        goals_for.append(m.get("home_score", 0) or 0)
                        goals_against.append(m.get("away_score", 0) or 0)
                    else:
                        if m["result"] == "away_win":
                            form_values.append(3)
                        elif m["result"] == "draw":
                            form_values.append(1)
                        else:
                            form_values.append(0)
                        goals_for.append(m.get("away_score", 0) or 0)
                        goals_against.append(m.get("home_score", 0) or 0)
                
                weighted_form = sum(w * v for w, v in zip(weights, form_values)) / total_weight
                weighted_gf = sum(w * v for w, v in zip(weights, goals_for)) / total_weight
                weighted_ga = sum(w * v for w, v in zip(weights, goals_against)) / total_weight
                
                df.at[idx, f"{team_type}_weighted_form"] = weighted_form
                df.at[idx, f"{team_type}_weighted_goals_for"] = weighted_gf
                df.at[idx, f"{team_type}_weighted_goals_against"] = weighted_ga
        
        # Add current match to history for both teams
        for team_type in ["home", "away"]:
            team = row[f"{team_type}_team"]
            if team not in team_history:
                team_history[team] = []
            
            team_history[team].append({
                "is_home": team_type == "home",
                "result": row.get("result"),
                "home_score": row.get("home_score"),
                "away_score": row.get("away_score"),
            })
    
    logger.info("Calculated weighted form features")
    return df


def calculate_venue_stats(df: pd.DataFrame, min_matches: int = 5) -> pd.DataFrame:
    """
    Calculate home/away performance statistics for each team.
    
    Args:
        df: DataFrame with match data
        min_matches: Minimum matches required for stats
    
    Returns:
        DataFrame with venue-specific features
    """
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)
    
    df["home_team_home_win_rate"] = 0.5
    df["home_team_home_goals_avg"] = 1.5
    df["away_team_away_win_rate"] = 0.33
    df["away_team_away_goals_avg"] = 1.0
    
    # Track venue-specific history
    home_stats: Dict[str, List[dict]] = {}
    away_stats: Dict[str, List[dict]] = {}
    
    for idx, row in df.iterrows():
        home_team = row["home_team"]
        away_team = row["away_team"]
        
        # Calculate home team's home record
        home_history = home_stats.get(home_team, [])
        if len(home_history) >= min_matches:
            wins = sum(1 for m in home_history if m["result"] == "home_win")
            goals = [m.get("home_score", 0) or 0 for m in home_history]
            df.at[idx, "home_team_home_win_rate"] = wins / len(home_history)
            df.at[idx, "home_team_home_goals_avg"] = np.mean(goals)
        
        # Calculate away team's away record
        away_history = away_stats.get(away_team, [])
        if len(away_history) >= min_matches:
            wins = sum(1 for m in away_history if m["result"] == "away_win")
            goals = [m.get("away_score", 0) or 0 for m in away_history]
            df.at[idx, "away_team_away_win_rate"] = wins / len(away_history)
            df.at[idx, "away_team_away_goals_avg"] = np.mean(goals)
        
        # Update history
        if home_team not in home_stats:
            home_stats[home_team] = []
        home_stats[home_team].append({
            "result": row.get("result"),
            "home_score": row.get("home_score"),
        })
        
        if away_team not in away_stats:
            away_stats[away_team] = []
        away_stats[away_team].append({
            "result": row.get("result"),
            "away_score": row.get("away_score"),
        })
    
    logger.info("Calculated venue-specific features")
    return df


def engineer_odds_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer powerful features from betting odds.
    Odds are the strongest predictors - this extracts maximum signal.
    
    Args:
        df: DataFrame with odds columns
    
    Returns:
        DataFrame with odds-derived features
    """
    df = df.copy()
    
    # Ensure odds columns exist
    for col in ["home_win", "draw", "away_win"]:
        if col not in df.columns:
            df[col] = np.nan
    
    # Convert odds to implied probabilities (removing vig)
    df["implied_home_prob"] = 1 / df["home_win"]
    df["implied_draw_prob"] = 1 / df["draw"]
    df["implied_away_prob"] = 1 / df["away_win"]
    
    # Calculate overround (vig)
    df["overround"] = df["implied_home_prob"] + df["implied_draw_prob"] + df["implied_away_prob"]
    
    # Normalize to true probabilities (remove vig)
    df["fair_home_prob"] = df["implied_home_prob"] / df["overround"]
    df["fair_draw_prob"] = df["implied_draw_prob"] / df["overround"]
    df["fair_away_prob"] = df["implied_away_prob"] / df["overround"]
    
    # Odds-based features (strong signals)
    df["odds_ratio"] = df["home_win"] / df["away_win"]
    df["odds_spread"] = df["home_win"] - df["away_win"]
    df["odds_total"] = df["home_win"] + df["draw"] + df["away_win"]
    
    # Log odds (better for linear models)
    df["log_home_odds"] = np.log(df["home_win"].clip(lower=1.01))
    df["log_away_odds"] = np.log(df["away_win"].clip(lower=1.01))
    df["log_draw_odds"] = np.log(df["draw"].clip(lower=1.01))
    
    # Favorite indicator
    df["home_is_favorite"] = (df["home_win"] < df["away_win"]).astype(int)
    df["favorite_odds"] = df[["home_win", "away_win"]].min(axis=1)
    df["underdog_odds"] = df[["home_win", "away_win"]].max(axis=1)
    
    # Fill NaN with neutral values
    df["implied_home_prob"] = df["implied_home_prob"].fillna(0.4)
    df["implied_draw_prob"] = df["implied_draw_prob"].fillna(0.25)
    df["implied_away_prob"] = df["implied_away_prob"].fillna(0.35)
    df["fair_home_prob"] = df["fair_home_prob"].fillna(0.4)
    df["fair_draw_prob"] = df["fair_draw_prob"].fillna(0.25)
    df["fair_away_prob"] = df["fair_away_prob"].fillna(0.35)
    df["odds_ratio"] = df["odds_ratio"].fillna(1.0)
    df["odds_spread"] = df["odds_spread"].fillna(0.0)
    df["log_home_odds"] = df["log_home_odds"].fillna(np.log(2.5))
    df["log_away_odds"] = df["log_away_odds"].fillna(np.log(2.8))
    df["log_draw_odds"] = df["log_draw_odds"].fillna(np.log(3.2))
    df["home_is_favorite"] = df["home_is_favorite"].fillna(0)
    df["favorite_odds"] = df["favorite_odds"].fillna(2.0)
    df["underdog_odds"] = df["underdog_odds"].fillna(3.0)
    
    logger.info("Engineered odds-based features")
    return df


def load_training_data() -> pd.DataFrame:
    """Load and combine all processed data files and historical CSVs."""
    from pathlib import Path
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    historical_dir = base_dir / "data" / "raw" / "historical"
    
    dfs = []
    
    # Load processed parquet files
    parquet_files = list(PROCESSED_DATA_DIR.glob("matches_*.parquet"))
    for file in parquet_files:
        try:
            df = pd.read_parquet(file)
            dfs.append(df)
        except Exception as e:
            logger.warning(f"Failed to load {file}: {e}")
    
    logger.info(f"Loaded {len(dfs)} parquet files")
    
    # Load historical CSV files (these have the bulk of training data)
    csv_files = list(historical_dir.glob("*.csv"))
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            
            # Normalize column names from historical format
            column_mapping = {
                'Date': 'date',
                'HomeTeam': 'home_team',
                'AwayTeam': 'away_team',
                'FTHG': 'home_score',  # Full Time Home Goals
                'FTAG': 'away_score',  # Full Time Away Goals
                'FTR': 'ftr',          # Full Time Result (H/D/A)
                'B365H': 'home_win',   # Bet365 Home odds
                'B365D': 'draw',       # Bet365 Draw odds
                'B365A': 'away_win',   # Bet365 Away odds
                'BWH': 'bw_home',      # Betway Home
                'BWD': 'bw_draw',
                'BWA': 'bw_away',
                'PSH': 'ps_home',      # Pinnacle Home
                'PSD': 'ps_draw',
                'PSA': 'ps_away',
            }
            
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            # Convert FTR to result
            if 'ftr' in df.columns:
                result_map = {'H': 'home_win', 'D': 'draw', 'A': 'away_win'}
                df['result'] = df['ftr'].map(result_map)
            
            # Use average of available odds if B365 not present
            if 'home_win' not in df.columns or df['home_win'].isna().all():
                odds_cols = [c for c in df.columns if c.endswith('_home') and c != 'home_win']
                if odds_cols:
                    df['home_win'] = df[odds_cols].mean(axis=1)
            
            if 'draw' not in df.columns or df['draw'].isna().all():
                odds_cols = [c for c in df.columns if c.endswith('_draw') and c != 'draw']
                if odds_cols:
                    df['draw'] = df[odds_cols].mean(axis=1)
            
            if 'away_win' not in df.columns or df['away_win'].isna().all():
                odds_cols = [c for c in df.columns if c.endswith('_away') and c != 'away_win']
                if odds_cols:
                    df['away_win'] = df[odds_cols].mean(axis=1)
            
            # Add source info
            df['data_source'] = 'historical_csv'
            df['competition'] = csv_file.stem.replace('_', ' ')
            
            dfs.append(df)
            
        except Exception as e:
            logger.warning(f"Failed to load {csv_file}: {e}")
    
    logger.info(f"Loaded {len(csv_files)} historical CSV files")
    
    if not dfs:
        raise ValueError("No data files found for training")
    
    combined = pd.concat(dfs, ignore_index=True)
    
    # Remove duplicates based on key fields
    key_cols = ['date', 'home_team', 'away_team']
    available_keys = [c for c in key_cols if c in combined.columns]
    if available_keys:
        combined = combined.drop_duplicates(subset=available_keys, keep="last")
    
    logger.info(f"Loaded {len(combined)} total matches from all sources")
    return combined


def prepare_enhanced_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Prepare enhanced feature set for training.
    
    Returns:
        Tuple of (features DataFrame, target Series, feature names)
    """
    # Filter to matches with results
    df = df[df["result"].notna()].copy()
    
    # Convert date
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.tz_localize(None)
    
    logger.info(f"Processing {len(df)} matches with results")
    
    # Calculate all enhanced features
    logger.info("Calculating ELO ratings...")
    df = calculate_elo_ratings(df)
    
    logger.info("Calculating head-to-head stats...")
    df = calculate_head_to_head(df)
    
    logger.info("Calculating weighted form...")
    df = calculate_weighted_form(df)
    
    logger.info("Calculating venue stats...")
    df = calculate_venue_stats(df)
    
    logger.info("Engineering odds features...")
    df = engineer_odds_features(df)
    
    # Define feature columns (prioritizing odds-based features)
    feature_cols = [
        # Odds-derived features (STRONGEST SIGNALS)
        "fair_home_prob",
        "fair_draw_prob",
        "fair_away_prob",
        "odds_ratio",
        "odds_spread",
        "log_home_odds",
        "log_away_odds",
        "log_draw_odds",
        "home_is_favorite",
        "favorite_odds",
        "underdog_odds",
        
        # ELO features
        "home_elo",
        "away_elo",
        "elo_diff",
        "home_expected",
        
        # Head-to-head features
        "h2h_home_wins",
        "h2h_draws",
        "h2h_away_wins",
        "h2h_home_goals_avg",
        "h2h_away_goals_avg",
        
        # Weighted form features
        "home_weighted_form",
        "away_weighted_form",
        "home_weighted_goals_for",
        "home_weighted_goals_against",
        "away_weighted_goals_for",
        "away_weighted_goals_against",
        
        # Venue-specific features
        "home_team_home_win_rate",
        "home_team_home_goals_avg",
        "away_team_away_win_rate",
        "away_team_away_goals_avg",
        
        # Original form features (keep for compatibility)
        "home_team_wins_last_n",
        "home_team_draws_last_n",
        "home_team_losses_last_n",
        "away_team_wins_last_n",
        "away_team_draws_last_n",
        "away_team_losses_last_n",
        "home_team_avg_gd_last_n",
        "away_team_avg_gd_last_n",
    ]
    
    # Filter to available features
    available_features = [col for col in feature_cols if col in df.columns]
    
    logger.info(f"Using {len(available_features)} features")
    
    # Create feature matrix
    X = df[available_features].copy()
    X = X.fillna(0)
    
    # Create target
    y = df["result"].copy()
    
    logger.info(f"Prepared {len(X)} samples")
    logger.info(f"Target distribution:\n{y.value_counts()}")
    
    return X, y, available_features


def create_ensemble_model() -> StackingClassifier:
    """
    Create a stacking ensemble with multiple base models.
    
    Returns:
        StackingClassifier with calibrated predictions
    """
    # Base models with different strengths
    base_models = [
        ("xgb", xgb.XGBClassifier(
            objective="multi:softprob",
            num_class=3,
            max_depth=6,
            learning_rate=0.05,
            n_estimators=200,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            use_label_encoder=False,
            eval_metric="mlogloss",
        )),
        ("lgb", lgb.LGBMClassifier(
            objective="multiclass",
            num_class=3,
            max_depth=6,
            learning_rate=0.05,
            n_estimators=200,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )),
        ("rf", RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1,
        )),
        ("gb", GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
        )),
    ]
    
    # Meta-learner (logistic regression works well for stacking)
    meta_learner = LogisticRegression(
        multi_class="multinomial",
        solver="lbfgs",
        max_iter=1000,
        random_state=42,
    )
    
    # Create stacking classifier
    stacking = StackingClassifier(
        estimators=base_models,
        final_estimator=meta_learner,
        cv=5,
        stack_method="predict_proba",
        n_jobs=-1,
        passthrough=True,  # Include original features
    )
    
    return stacking


def train_calibrated_ensemble(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    label_encoder: LabelEncoder,
) -> Tuple[CalibratedClassifierCV, Dict]:
    """
    Train ensemble model with probability calibration.
    
    Returns:
        Tuple of (calibrated model, metrics dict)
    """
    y_train_encoded = label_encoder.transform(y_train)
    y_val_encoded = label_encoder.transform(y_val)
    
    logger.info("Creating ensemble model...")
    ensemble = create_ensemble_model()
    
    logger.info("Training ensemble (this may take a while)...")
    ensemble.fit(X_train, y_train_encoded)
    
    # Evaluate base ensemble
    train_acc = ensemble.score(X_train, y_train_encoded)
    val_acc = ensemble.score(X_val, y_val_encoded)
    logger.info(f"Ensemble - Train accuracy: {train_acc:.4f}, Val accuracy: {val_acc:.4f}")
    
    # Apply probability calibration (isotonic regression)
    logger.info("Calibrating probabilities with isotonic regression...")
    calibrated = CalibratedClassifierCV(
        ensemble,
        method="isotonic",
        cv="prefit",  # Already fitted
    )
    calibrated.fit(X_val, y_val_encoded)
    
    # Evaluate calibrated model
    y_pred = calibrated.predict(X_val)
    y_pred_proba = calibrated.predict_proba(X_val)
    
    cal_acc = accuracy_score(y_val_encoded, y_pred)
    cal_logloss = log_loss(y_val_encoded, y_pred_proba)
    
    # Calculate Brier score for each class
    brier_scores = {}
    for i, class_name in enumerate(label_encoder.classes_):
        y_true_binary = (y_val_encoded == i).astype(int)
        brier_scores[class_name] = brier_score_loss(y_true_binary, y_pred_proba[:, i])
    
    logger.info(f"Calibrated - Accuracy: {cal_acc:.4f}, Log Loss: {cal_logloss:.4f}")
    logger.info(f"Brier scores: {brier_scores}")
    
    # Check probability distribution
    mean_probs = y_pred_proba.mean(axis=0)
    logger.info(f"Mean predicted probabilities: {dict(zip(label_encoder.classes_, mean_probs))}")
    
    metrics = {
        "model_version": MODEL_VERSION,
        "model_type": "calibrated_stacking_ensemble",
        "train_accuracy": float(train_acc),
        "val_accuracy": float(val_acc),
        "calibrated_accuracy": float(cal_acc),
        "log_loss": float(cal_logloss),
        "brier_scores": {k: float(v) for k, v in brier_scores.items()},
        "mean_probabilities": {k: float(v) for k, v in zip(label_encoder.classes_, mean_probs)},
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "classes": list(label_encoder.classes_),
        "trained_at": datetime.now().isoformat(),
    }
    
    return calibrated, metrics


def save_model_artifacts(
    model,
    label_encoder: LabelEncoder,
    scaler: Optional[StandardScaler],
    metrics: Dict,
    feature_names: List[str],
) -> None:
    """Save all model artifacts."""
    ensure_dir(MODEL_DIR)
    
    # Save model
    model_path = MODEL_DIR / f"model_v{MODEL_VERSION}.pkl"
    joblib.dump(model, model_path)
    logger.info(f"Saved model to {model_path}")
    
    # Save label encoder
    encoder_path = MODEL_DIR / f"label_encoder_v{MODEL_VERSION}.pkl"
    joblib.dump(label_encoder, encoder_path)
    logger.info(f"Saved label encoder to {encoder_path}")
    
    # Save scaler if used
    if scaler is not None:
        scaler_path = MODEL_DIR / f"scaler_v{MODEL_VERSION}.pkl"
        joblib.dump(scaler, scaler_path)
        logger.info(f"Saved scaler to {scaler_path}")
    
    # Save feature names
    features_path = MODEL_DIR / f"features_v{MODEL_VERSION}.pkl"
    joblib.dump(feature_names, features_path)
    logger.info(f"Saved feature names to {features_path}")
    
    # Save metrics
    metrics["features"] = feature_names
    metrics_path = MODEL_DIR / f"metrics_v{MODEL_VERSION}.json"
    save_json(metrics, metrics_path)
    logger.info(f"Saved metrics to {metrics_path}")


def train_model() -> None:
    """Main training pipeline."""
    logger.info("=" * 60)
    logger.info(f"Starting enhanced model training v{MODEL_VERSION}")
    logger.info("=" * 60)
    
    # Load data
    df = load_training_data()
    
    # Prepare enhanced features
    X, y, feature_names = prepare_enhanced_features(df)
    
    if len(X) < 1000:
        raise ValueError(f"Insufficient data: {len(X)} samples (need at least 1000)")
    
    # Encode labels
    label_encoder = LabelEncoder()
    label_encoder.fit(y)
    logger.info(f"Classes: {list(label_encoder.classes_)}")
    
    # Split data (stratified)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"Train set: {len(X_train)} samples")
    logger.info(f"Validation set: {len(X_val)} samples")
    
    # Train calibrated ensemble
    model, metrics = train_calibrated_ensemble(
        X_train, y_train, X_val, y_val, label_encoder
    )
    
    # Save artifacts
    save_model_artifacts(model, label_encoder, None, metrics, feature_names)
    
    logger.info("=" * 60)
    logger.info("Model training completed successfully!")
    logger.info(f"Final validation accuracy: {metrics['calibrated_accuracy']:.4f}")
    logger.info(f"Log loss: {metrics['log_loss']:.4f}")
    logger.info("=" * 60)


def main() -> None:
    """Main entry point."""
    try:
        train_model()
    except Exception as e:
        logger.error(f"Model training failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
