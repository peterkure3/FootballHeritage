"""Freeze the existing Rust intelligence list contracts over their local producer DB."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

SELECTS = {
    "intelligence/devigged-odds": (
        "d",
        "devigged_odds",
        "d.id,d.event_id,d.pipeline_match_id,e.home_team AS event_home_team,e.away_team AS event_away_team,e.event_date,d.bookmaker,d.market,d.outcome_a,d.outcome_b,d.odds_a,d.odds_b,d.fair_prob_a,d.fair_prob_b,d.vig,d.source_updated_at,d.created_at",
        "d.created_at DESC",
    ),
    "intelligence/ev-bets": (
        "b",
        "ev_bets",
        "b.id,b.event_id,b.pipeline_match_id,e.home_team AS event_home_team,e.away_team AS event_away_team,e.event_date,e.league,b.bookmaker,b.market,b.selection,b.odds,b.stake,b.true_probability,b.expected_value,b.expected_value_pct,b.source_updated_at,b.created_at",
        "b.expected_value_pct DESC,b.created_at DESC",
    ),
    "intelligence/arbitrage": (
        "a",
        "arbitrage",
        "a.id,a.event_id,a.pipeline_match_id,e.home_team AS event_home_team,e.away_team AS event_away_team,e.event_date,a.market,a.selection_a,a.selection_b,a.book_a,a.book_b,a.odds_a,a.odds_b,a.arb_percentage,a.total_stake,a.stake_a,a.stake_b,a.source_updated_at,a.created_at",
        "a.arb_percentage DESC,a.created_at DESC",
    ),
}


def wire(value, field=None):
    if isinstance(value, datetime):
        value = (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )
        precision = (
            "seconds"
            if not value.microsecond
            else "milliseconds"
            if value.microsecond % 1000 == 0
            else "microseconds"
        )
        return value.isoformat(timespec=precision).replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return (
            str(value)
            if field in {"stake", "total_stake", "stake_a", "stake_b"}
            else float(value)
        )
    if isinstance(value, UUID):
        return str(value)
    return value


def read(envelope):
    from api.db import get_heritage_db_connection
    from sqlalchemy import text

    alias, table, columns, ordering = SELECTS[envelope["path"]]
    query = dict(envelope["query"])
    allowed = {
        "event_id": f"{alias}.event_id",
        "pipeline_match_id": f"{alias}.pipeline_match_id",
        "market": f"{alias}.market",
    }
    if alias != "a":
        allowed["bookmaker"] = f"{alias}.bookmaker"
    if alias == "b":
        allowed["league"] = "e.league"
    conditions = []
    params = {"limit": min(2000, max(1, int(query.get("limit", "200"))))}
    for key, column in allowed.items():
        if key in query:
            params[key] = str(UUID(query[key])) if key == "event_id" else query[key]
            conditions.append(f"{column}=:{key}")
    for key, column in (
        ("min_ev_pct", "b.expected_value_pct"),
        ("min_arb_pct", "a.arb_percentage"),
    ):
        if key in query and (
            (alias == "b" and key == "min_ev_pct")
            or (alias == "a" and key == "min_arb_pct")
        ):
            params[key] = float(query[key])
            conditions.append(f"{column}>=:{key}")
    statement = f"SELECT {columns} FROM {table} {alias} LEFT JOIN events e ON e.id={alias}.event_id"
    if conditions:
        statement += " WHERE " + " AND ".join(conditions)
    statement += f" ORDER BY {ordering} LIMIT :limit"
    with get_heritage_db_connection().connect() as connection:
        rows = connection.execute(text(statement), params).mappings().all()
    return {
        "status": 200,
        "body": [{key: wire(value, key) for key, value in row.items()} for row in rows],
    }
