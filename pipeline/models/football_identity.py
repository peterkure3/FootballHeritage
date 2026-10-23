"""Reviewed provider identities without rewriting frozen football feature keys."""

from models.data import team_key

ALIASES = {
    "brighton & hove albion": "brighton",
    "sunderland": "sunderland afc",
    "hull city": "hull city afc",
    "bournemouth": "afc bournemouth",
}


def football_identity_key(name: str) -> str:
    key = team_key(name)
    return ALIASES.get(key, key)


def football_history_key(name: str, known: set[str]) -> str:
    key = team_key(name)
    if key in known:
        return key
    resolved = football_identity_key(name)
    if resolved not in known:
        raise ValueError("Teams lack training history")
    return resolved
