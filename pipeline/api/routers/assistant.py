"""Intent-routed smart assistant (no LLM)."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from config import LOG_LEVEL
from etl.utils import setup_logger
from api.db import get_db_connection

logger = setup_logger(__name__, LOG_LEVEL)

router = APIRouter()


# ============================================================================
# SMART ASSISTANT - Intent-based routing without LLM
# ============================================================================

class AssistantRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


class BetCard(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    competition: Optional[str] = None
    match_date: Optional[datetime] = None
    selection: str
    model_prob: float
    implied_prob: float
    edge_pct: float
    decimal_odds: float
    recommended_stake: float
    expected_value: float
    confidence: str


class PredictionCard(BaseModel):
    home_team: str
    away_team: str
    home_prob: float
    draw_prob: float
    away_prob: float
    winner: str
    confidence: str
    recommendation: str


class MatchCard(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    competition: Optional[str] = None
    match_date: Optional[datetime] = None
    status: Optional[str] = None


class AssistantResponse(BaseModel):
    intent: str
    message: str
    data: Optional[Dict[str, Any]] = None
    bets: Optional[List[BetCard]] = None
    predictions: Optional[List[PredictionCard]] = None
    matches: Optional[List[MatchCard]] = None
    suggestions: List[str] = []


# Intent patterns for smart routing
INTENT_PATTERNS = {
    "best_bets": [
        r"best\s*(value)?\s*bets?",
        r"top\s*picks?",
        r"what\s*(should|to)\s*bet",
        r"recommend(ations?)?",
        r"smart\s*picks?",
        r"good\s*bets?",
        r"where\s*(should|to)\s*bet",
        r"make\s*money",
        r"profitable",
        r"value\s*bets?",
        r"ev\s*bets?",
        r"\+ev",
    ],
    "predict_match": [
        r"predict\s+(.+?)\s*(?:vs?|versus|against)\s*(.+)",
        r"who\s*(?:will|would|gonna)?\s*win\s+(.+?)\s*(?:vs?|versus|against|or)\s*(.+)",
        r"(.+?)\s*(?:vs?|versus)\s*(.+?)\s*(?:prediction|odds|analysis)",
        r"analyze\s+(.+?)\s*(?:vs?|versus|against)\s*(.+)",
        r"(.+?)\s*(?:vs?|versus|against)\s*(.+)",
    ],
    "upcoming_matches": [
        r"(?:today'?s?|tonight'?s?|upcoming|next)\s*(?:games?|matches?|fixtures?)",
        r"what\s*(?:matches|games)\s*(?:are)?\s*(?:on|playing)?\s*(?:today|tonight|this\s*week)?",
        r"(?:show|list|get)\s*(?:me\s*)?(?:the\s*)?(?:games?|matches?|fixtures?)",
        r"matches\s*(?:on\s*)?today",
        r"today'?s?\s*(?:games?|matches?)",
        r"schedule",
        r"fixtures?",
    ],
    "team_analysis": [
        r"(?:how\s*is|analyze|analysis|stats?|statistics?|form)\s*(?:for\s*)?(.+)",
        r"(.+?)\s*(?:form|stats?|statistics?|performance|analysis)",
        r"tell\s*me\s*about\s*(.+)",
    ],
    "help": [
        r"help",
        r"what\s*can\s*you\s*do",
        r"commands?",
        r"how\s*(?:do|does)\s*(?:this|it)\s*work",
    ],
    "greeting": [
        r"^(?:hi|hello|hey|yo|sup|greetings?)(?:\s|$|!|\?)",
        r"^(?:good\s*)?(?:morning|afternoon|evening)",
    ],
}

# Team name aliases for better matching
TEAM_ALIASES = {
    "arsenal": ["arsenal", "gunners", "ars"],
    "chelsea": ["chelsea", "blues", "che"],
    "liverpool": ["liverpool", "reds", "lfc", "liv"],
    "man city": ["manchester city", "man city", "city", "mci", "mcfc"],
    "man united": ["manchester united", "man united", "man utd", "united", "manu", "mufc"],
    "tottenham": ["tottenham", "spurs", "tot", "thfc"],
    "barcelona": ["barcelona", "barca", "fcb"],
    "real madrid": ["real madrid", "real", "madrid", "rma"],
    "bayern": ["bayern munich", "bayern", "fcb munich"],
    "psg": ["paris saint-germain", "psg", "paris"],
    "juventus": ["juventus", "juve"],
    "inter": ["inter milan", "inter", "internazionale"],
    "milan": ["ac milan", "milan"],
    "dortmund": ["borussia dortmund", "dortmund", "bvb"],
    "newcastle": ["newcastle", "newcastle united", "magpies", "nufc"],
    "aston villa": ["aston villa", "villa", "avfc"],
    "west ham": ["west ham", "hammers", "whu"],
    "everton": ["everton", "toffees", "efc"],
    "wolves": ["wolverhampton", "wolves", "wwfc"],
    "brighton": ["brighton", "seagulls", "bha"],
    "crystal palace": ["crystal palace", "palace", "cpfc"],
    "brentford": ["brentford", "bees"],
    "fulham": ["fulham", "cottagers"],
    "bournemouth": ["bournemouth", "cherries", "afcb"],
    "nottingham forest": ["nottingham forest", "forest", "nffc"],
    "leeds": ["leeds", "leeds united", "lufc"],
}


def normalize_team_name(query: str) -> Optional[str]:
    """Try to match a team name from user input."""
    query_lower = query.lower().strip()
    for canonical, aliases in TEAM_ALIASES.items():
        for alias in aliases:
            if alias in query_lower:
                return canonical
    return query_lower


def detect_intent(query: str) -> tuple[str, dict]:
    """Detect user intent from query using pattern matching."""
    query_lower = query.lower().strip()
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                return intent, {"groups": match.groups() if match.groups() else []}
    
    return "unknown", {}


@router.post("/smart-assistant", response_model=AssistantResponse)
def smart_assistant(request: AssistantRequest):
    """
    Smart betting assistant with intent-based routing.
    No LLM required - uses pattern matching to understand queries
    and calls appropriate internal APIs.
    """
    query = request.query.strip()
    intent, context = detect_intent(query)
    
    try:
        if intent == "greeting":
            return AssistantResponse(
                intent=intent,
                message="👋 Hey! I'm your AI betting assistant. I can help you find value bets, predict matches, and analyze teams. What would you like to know?",
                suggestions=[
                    "Show me the best value bets",
                    "Predict Arsenal vs Liverpool",
                    "What matches are on today?",
                    "Analyze Manchester City's form",
                ]
            )
        
        elif intent == "help":
            return AssistantResponse(
                intent=intent,
                message="""🤖 **Here's what I can do:**

**Find Value Bets** - I'll show you bets where our ML model finds positive edge
• "Show me the best bets"
• "What are today's value picks?"

**Predict Matches** - Get AI predictions for any matchup
• "Predict Arsenal vs Chelsea"
• "Who will win Liverpool vs Man City?"

**View Upcoming Matches** - See what's coming up
• "What matches are on today?"
• "Show me this week's fixtures"

**Analyze Teams** - Get team stats and form
• "How is Arsenal doing?"
• "Analyze Liverpool's form"

Just ask naturally and I'll help! 🎯""",
                suggestions=[
                    "Best value bets",
                    "Predict Arsenal vs Liverpool",
                    "Today's matches",
                ]
            )
        
        elif intent == "best_bets":
            return _handle_best_bets()
        
        elif intent == "predict_match":
            return _handle_predict_match(query, context)
        
        elif intent == "upcoming_matches":
            return _handle_upcoming_matches()
        
        elif intent == "team_analysis":
            return _handle_team_analysis(query, context)
        
        else:
            # Unknown intent - try to be helpful
            return AssistantResponse(
                intent="unknown",
                message=f"🤔 I'm not sure what you're asking about. Here are some things I can help with:",
                suggestions=[
                    "Show me the best value bets",
                    "Predict Arsenal vs Liverpool",
                    "What matches are on today?",
                    "How is Manchester City doing?",
                ]
            )
    
    except Exception as e:
        logger.error(f"Smart assistant error: {str(e)}")
        return AssistantResponse(
            intent="error",
            message=f"Sorry, I encountered an error: {str(e)}. Please try again.",
            suggestions=["Show me the best bets", "What matches are on today?"]
        )


def _handle_best_bets() -> AssistantResponse:
    """Handle best bets intent."""
    db = get_db_connection()
    
    date_filter = " AND m.date >= NOW()"
    status_filter = " AND (m.status IS NULL OR m.status NOT IN ('FINISHED', 'CANCELLED', 'POSTPONED'))"
    
    query = text(f"""
        SELECT 
            m.match_id, m.home_team, m.away_team, m.competition, m.date, m.status,
            p.home_prob, p.draw_prob, p.away_prob, p.model_version,
            COALESCE(AVG(o.home_win), 2.5) as home_odds,
            COALESCE(AVG(o.draw), 3.2) as draw_odds,
            COALESCE(AVG(o.away_win), 2.8) as away_odds
        FROM matches m
        INNER JOIN predictions p ON m.match_id = p.match_id
        LEFT JOIN odds o ON m.match_id = o.match_id
        WHERE m.home_team IS NOT NULL AND m.away_team IS NOT NULL AND p.home_prob IS NOT NULL
            {date_filter} {status_filter}
        GROUP BY m.match_id, m.home_team, m.away_team, m.competition, m.date, m.status,
                 p.home_prob, p.draw_prob, p.away_prob, p.model_version
        ORDER BY m.date ASC NULLS LAST
        LIMIT 50
    """)
    
    with db.connect() as conn:
        results = conn.execute(query).fetchall()
    
    bets = []
    min_edge = 0.05
    bankroll = 1000
    kelly_fraction = 0.25
    
    for row in results:
        home_prob, draw_prob, away_prob = float(row[6]), float(row[7]), float(row[8])
        home_odds, draw_odds, away_odds = float(row[10]), float(row[11]), float(row[12])
        
        home_implied = 1 / home_odds if home_odds > 1 else 0.4
        draw_implied = 1 / draw_odds if draw_odds > 1 else 0.25
        away_implied = 1 / away_odds if away_odds > 1 else 0.35
        
        outcomes = [
            ("Home Win", row[1], home_prob, home_implied, home_odds),
            ("Draw", "Draw", draw_prob, draw_implied, draw_odds),
            ("Away Win", row[2], away_prob, away_implied, away_odds),
        ]
        
        for outcome_name, selection, model_prob, implied_prob, decimal_odds in outcomes:
            edge = model_prob - implied_prob
            if edge >= min_edge and decimal_odds > 1.0:
                b = decimal_odds - 1
                kelly_full = (b * model_prob - (1 - model_prob)) / b if b > 0 else 0
                kelly_stake_pct = max(0, kelly_full * kelly_fraction)
                recommended_stake = round(bankroll * kelly_stake_pct, 2)
                win_profit = recommended_stake * (decimal_odds - 1)
                ev = (model_prob * win_profit) - ((1 - model_prob) * recommended_stake)
                
                confidence = "High" if edge > 0.15 else "Medium" if edge > 0.08 else "Low"
                
                bets.append(BetCard(
                    match_id=row[0],
                    home_team=row[1],
                    away_team=row[2],
                    competition=row[3],
                    match_date=row[4],
                    selection=f"{selection} ({outcome_name})",
                    model_prob=round(model_prob, 4),
                    implied_prob=round(implied_prob, 4),
                    edge_pct=round(edge * 100, 2),
                    decimal_odds=round(decimal_odds, 3),
                    recommended_stake=recommended_stake,
                    expected_value=round(ev, 2),
                    confidence=confidence,
                ))
    
    bets.sort(key=lambda x: x.edge_pct, reverse=True)
    top_bets = bets[:10]
    
    if not top_bets:
        return AssistantResponse(
            intent="best_bets",
            message="📊 No value bets found right now with 5%+ edge. Try checking back later when more matches are available.",
            bets=[],
            suggestions=["What matches are on today?", "Predict Arsenal vs Liverpool"]
        )
    
    total_ev = sum(b.expected_value for b in top_bets)
    avg_edge = sum(b.edge_pct for b in top_bets) / len(top_bets)
    
    message = f"""🎯 **Found {len(top_bets)} Value Bets!**

Our ML model identified these bets with positive edge:
• **Average Edge:** +{avg_edge:.1f}%
• **Total Expected Value:** ${total_ev:.2f}

⚠️ Remember: These are model predictions, not guarantees. Bet responsibly!"""
    
    return AssistantResponse(
        intent="best_bets",
        message=message,
        bets=top_bets,
        suggestions=["Show me more details", "Predict a specific match", "How does the model work?"]
    )


def _handle_predict_match(query: str, context: dict) -> AssistantResponse:
    """Handle match prediction intent."""
    groups = context.get("groups", [])
    
    # Try to extract team names from the query
    home_team = None
    away_team = None
    
    if groups and len(groups) >= 2:
        home_team = groups[0].strip() if groups[0] else None
        away_team = groups[1].strip() if groups[1] else None
    
    if not home_team or not away_team:
        # Try to find team names in query
        query_lower = query.lower()
        found_teams = []
        for canonical, aliases in TEAM_ALIASES.items():
            for alias in aliases:
                if alias in query_lower and canonical not in found_teams:
                    found_teams.append(canonical)
                    break
        
        if len(found_teams) >= 2:
            home_team, away_team = found_teams[0], found_teams[1]
        elif len(found_teams) == 1:
            return AssistantResponse(
                intent="predict_match",
                message=f"I found {found_teams[0].title()}, but I need two teams to make a prediction. Who are they playing against?",
                suggestions=[
                    f"Predict {found_teams[0].title()} vs Arsenal",
                    f"Predict {found_teams[0].title()} vs Liverpool",
                    f"Predict {found_teams[0].title()} vs Chelsea",
                ]
            )
        else:
            return AssistantResponse(
                intent="predict_match",
                message="I couldn't identify the teams. Please specify both teams, like 'Predict Arsenal vs Liverpool'.",
                suggestions=[
                    "Predict Arsenal vs Liverpool",
                    "Predict Barcelona vs Real Madrid",
                    "Predict Man City vs Chelsea",
                ]
            )
    
    # Get prediction from database or model
    db = get_db_connection()
    
    # Search for matching teams in database
    search_query = text("""
        SELECT m.match_id, m.home_team, m.away_team, m.competition, m.date,
               p.home_prob, p.draw_prob, p.away_prob, p.winner
        FROM matches m
        LEFT JOIN predictions p ON m.match_id = p.match_id
        WHERE (LOWER(m.home_team) LIKE :home OR LOWER(m.away_team) LIKE :home)
          AND (LOWER(m.home_team) LIKE :away OR LOWER(m.away_team) LIKE :away)
          AND m.date >= NOW()
        ORDER BY m.date ASC
        LIMIT 1
    """)
    
    with db.connect() as conn:
        result = conn.execute(search_query, {
            "home": f"%{home_team}%",
            "away": f"%{away_team}%"
        }).fetchone()
    
    if result and result[5]:  # Has prediction
        home_prob, draw_prob, away_prob = float(result[5]), float(result[6]), float(result[7])
        winner = result[8]
        actual_home = result[1]
        actual_away = result[2]
        
        confidence = "High" if max(home_prob, draw_prob, away_prob) > 0.6 else "Medium" if max(home_prob, draw_prob, away_prob) > 0.45 else "Low"
        
        if winner == "home_win":
            prediction_text = f"**{actual_home}** to win"
        elif winner == "away_win":
            prediction_text = f"**{actual_away}** to win"
        else:
            prediction_text = "**Draw**"
        
        message = f"""⚽ **{actual_home} vs {actual_away}**
📅 {result[4].strftime('%b %d, %Y %H:%M') if result[4] else 'TBD'}
🏆 {result[3] or 'Football'}

**Prediction:** {prediction_text}

**Probabilities:**
• {actual_home}: **{home_prob*100:.1f}%**
• Draw: **{draw_prob*100:.1f}%**
• {actual_away}: **{away_prob*100:.1f}%**

**Confidence:** {confidence}"""
        
        return AssistantResponse(
            intent="predict_match",
            message=message,
            predictions=[PredictionCard(
                home_team=actual_home,
                away_team=actual_away,
                home_prob=home_prob,
                draw_prob=draw_prob,
                away_prob=away_prob,
                winner=winner,
                confidence=confidence,
                recommendation=f"Model predicts {prediction_text}"
            )],
            suggestions=[
                f"Is there value betting on {actual_home}?",
                "Show me the best bets",
                "What other matches are on?"
            ]
        )
    
    # No match found - provide general response
    return AssistantResponse(
        intent="predict_match",
        message=f"I couldn't find an upcoming match between {home_team.title()} and {away_team.title()} in our database. Try checking the upcoming matches or use the What-If predictor on the Predictions page.",
        suggestions=[
            "What matches are on today?",
            "Show me the best bets",
        ]
    )


def _handle_upcoming_matches() -> AssistantResponse:
    """Handle upcoming matches intent."""
    db = get_db_connection()
    
    query = text("""
        SELECT match_id, home_team, away_team, competition, date, status
        FROM matches
        WHERE date >= NOW() 
          AND (status IS NULL OR status NOT IN ('FINISHED', 'CANCELLED'))
        ORDER BY date ASC
        LIMIT 15
    """)
    
    with db.connect() as conn:
        results = conn.execute(query).fetchall()
    
    if not results:
        return AssistantResponse(
            intent="upcoming_matches",
            message="📅 No upcoming matches found in the database. Try refreshing the data or check back later.",
            matches=[],
            suggestions=["Show me the best bets", "How does the model work?"]
        )
    
    matches = [
        MatchCard(
            match_id=row[0],
            home_team=row[1],
            away_team=row[2],
            competition=row[3],
            match_date=row[4],
            status=row[5]
        )
        for row in results
    ]
    
    # Group by date
    today = datetime.now().date()
    today_matches = [m for m in matches if m.match_date and m.match_date.date() == today]
    tomorrow_matches = [m for m in matches if m.match_date and m.match_date.date() == today + timedelta(days=1)]
    later_matches = [m for m in matches if m not in today_matches and m not in tomorrow_matches]
    
    message_parts = ["📅 **Upcoming Matches**\n"]
    
    if today_matches:
        message_parts.append(f"**Today ({len(today_matches)} matches):**")
        for m in today_matches[:5]:
            time_str = m.match_date.strftime('%H:%M') if m.match_date else 'TBD'
            message_parts.append(f"• {m.home_team} vs {m.away_team} ({time_str})")
    
    if tomorrow_matches:
        message_parts.append(f"\n**Tomorrow ({len(tomorrow_matches)} matches):**")
        for m in tomorrow_matches[:5]:
            time_str = m.match_date.strftime('%H:%M') if m.match_date else 'TBD'
            message_parts.append(f"• {m.home_team} vs {m.away_team} ({time_str})")
    
    if later_matches and not today_matches and not tomorrow_matches:
        message_parts.append(f"**Coming Up ({len(later_matches)} matches):**")
        for m in later_matches[:5]:
            date_str = m.match_date.strftime('%b %d %H:%M') if m.match_date else 'TBD'
            message_parts.append(f"• {m.home_team} vs {m.away_team} ({date_str})")
    
    message = "\n".join(message_parts)
    
    # Create suggestions based on matches
    suggestions = ["Show me the best value bets"]
    if matches:
        suggestions.append(f"Predict {matches[0].home_team} vs {matches[0].away_team}")
    
    return AssistantResponse(
        intent="upcoming_matches",
        message=message,
        matches=matches,
        suggestions=suggestions
    )


def _handle_team_analysis(query: str, context: dict) -> AssistantResponse:
    """Handle team analysis intent."""
    groups = context.get("groups", [])
    
    team_name = None
    if groups and groups[0]:
        team_name = groups[0].strip()
    
    if not team_name:
        # Try to find team in query
        query_lower = query.lower()
        for canonical, aliases in TEAM_ALIASES.items():
            for alias in aliases:
                if alias in query_lower:
                    team_name = canonical
                    break
            if team_name:
                break
    
    if not team_name:
        return AssistantResponse(
            intent="team_analysis",
            message="Which team would you like me to analyze?",
            suggestions=[
                "Analyze Arsenal",
                "How is Liverpool doing?",
                "Manchester City form",
            ]
        )
    
    db = get_db_connection()
    
    # Get team stats
    stats_query = text("""
        WITH recent AS (
            SELECT result, home_score, away_score, date,
                   CASE WHEN home_team ILIKE :team THEN 'home' ELSE 'away' END as venue
            FROM matches
            WHERE (home_team ILIKE :team OR away_team ILIKE :team)
              AND result IS NOT NULL
            ORDER BY date DESC
            LIMIT 10
        )
        SELECT 
            COUNT(*) as matches,
            COUNT(CASE WHEN (venue = 'home' AND result = 'home_win') OR (venue = 'away' AND result = 'away_win') THEN 1 END) as wins,
            COUNT(CASE WHEN result = 'draw' THEN 1 END) as draws,
            COUNT(CASE WHEN (venue = 'home' AND result = 'away_win') OR (venue = 'away' AND result = 'home_win') THEN 1 END) as losses,
            AVG(CASE WHEN venue = 'home' THEN home_score ELSE away_score END) as goals_for,
            AVG(CASE WHEN venue = 'home' THEN away_score ELSE home_score END) as goals_against
        FROM recent
    """)
    
    with db.connect() as conn:
        result = conn.execute(stats_query, {"team": f"%{team_name}%"}).fetchone()
    
    if not result or result[0] == 0:
        return AssistantResponse(
            intent="team_analysis",
            message=f"I couldn't find recent match data for {team_name.title()}. They might not be in our database.",
            suggestions=["What matches are on today?", "Show me the best bets"]
        )
    
    matches, wins, draws, losses = result[0], result[1] or 0, result[2] or 0, result[3] or 0
    goals_for = float(result[4] or 0)
    goals_against = float(result[5] or 0)
    
    # Determine form
    win_rate = wins / matches if matches > 0 else 0
    if win_rate >= 0.6:
        form_emoji = "🔥"
        form_text = "Excellent form"
    elif win_rate >= 0.4:
        form_emoji = "✅"
        form_text = "Good form"
    elif win_rate >= 0.2:
        form_emoji = "😐"
        form_text = "Mixed form"
    else:
        form_emoji = "📉"
        form_text = "Poor form"
    
    message = f"""📊 **{team_name.title()} - Last {matches} Matches**

{form_emoji} **Form:** {form_text}

**Record:** {wins}W - {draws}D - {losses}L
**Win Rate:** {win_rate*100:.0f}%
**Goals For:** {goals_for:.1f} per game
**Goals Against:** {goals_against:.1f} per game
**Goal Difference:** {goals_for - goals_against:+.1f} per game"""
    
    return AssistantResponse(
        intent="team_analysis",
        message=message,
        suggestions=[
            f"Predict {team_name.title()} vs Arsenal",
            "Show me the best bets",
            "What matches are on today?"
        ]
    )


