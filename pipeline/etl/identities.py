"""Resolve repeated provider observations before creating processed fixtures."""

import pandas as pd


def latest_fixtures(frame: pd.DataFrame, identity: str) -> pd.DataFrame:
    """Keep the latest observation; reject IDs shared by different teams."""
    if frame.empty:
        return frame
    if frame[identity].isna().any():
        raise ValueError(f"Missing {identity}")
    for column in ("home_team", "away_team"):
        if column in frame and frame.groupby(identity)[column].nunique().gt(1).any():
            raise ValueError(f"Conflicting teams for {identity}")
    result = frame.copy()
    order = []
    for column in ("observed_at", "last_update"):
        if column in result:
            key = f"_identity_{column}"
            result[key] = pd.to_datetime(result[column], utc=True, errors="coerce")
            order.append(key)
    if order:
        result = result.sort_values(order, kind="stable", na_position="first")
    return result.drop_duplicates(identity, keep="last").drop(columns=order).reset_index(drop=True)
