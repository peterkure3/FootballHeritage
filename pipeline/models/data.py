"""Canonical football fixtures and timestamped prematch odds."""

from pathlib import Path
import unicodedata

import numpy as np
import pandas as pd

ODDS_COLUMNS = ["home_win", "draw", "away_win"]
TEAM_ALIASES = {
    "man city": "manchester city", "manchester city fc": "manchester city",
    "man united": "manchester united", "manchester united fc": "manchester united",
    "tottenham hotspur fc": "tottenham", "tottenham hotspur": "tottenham",
    "wolverhampton wanderers fc": "wolves", "wolverhampton wanderers": "wolves",
    "west ham united fc": "west ham", "west ham united": "west ham",
    "brighton & hove albion fc": "brighton", "brighton and hove albion": "brighton",
    "newcastle united fc": "newcastle", "newcastle united": "newcastle",
    "nottingham forest fc": "nott'm forest", "nottingham forest": "nott'm forest",
}


def team_key(value: str) -> str:
    """Use explicit aliases, never substring matching between teams."""
    key = " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())
    key = TEAM_ALIASES.get(key, key)
    if key.endswith(" fc"):
        key = key[:-3]
    return TEAM_ALIASES.get(key, key)


def parse_dates(values: pd.Series) -> pd.Series:
    # Only slash-separated dates are day-first; ISO timestamps keep their meaning.
    slash = values.astype(str).str.contains("/", regex=False)
    result = pd.to_datetime(values.where(~slash), format="mixed", utc=True, errors="coerce")
    result.loc[slash] = pd.to_datetime(values.loc[slash], dayfirst=True, format="mixed",
                                     utc=True, errors="coerce")
    return result


def normalize_matches(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    mapping = {"Date": "date", "HomeTeam": "home_team", "AwayTeam": "away_team",
               "FTHG": "home_score", "FTAG": "away_score", "FTR": "ftr",
               "B365H": "home_win", "B365D": "draw", "B365A": "away_win"}
    for raw, canonical in mapping.items():
        if raw in df:
            if canonical == "date" and canonical in df:
                df[canonical] = parse_dates(df[canonical]).combine_first(parse_dates(df[raw]))
            else:
                df[canonical] = df[canonical].combine_first(df[raw]) if canonical in df else df[raw]
            df = df.drop(columns=[raw])
    if not {"date", "home_team", "away_team"}.issubset(df.columns):
        return pd.DataFrame()
    df["date"] = parse_dates(df["date"])
    df = df.dropna(subset=["date", "home_team", "away_team"])
    for side in ["home", "away"]:
        df[f"{side}_key"] = df[f"{side}_team"].map(team_key)
        col = f"{side}_score"
        df[col] = pd.to_numeric(df[col], errors="coerce") if col in df else np.nan
    if "result" not in df:
        df["result"] = None
    if "ftr" in df:
        df["result"] = df["result"].combine_first(df["ftr"].map({"H": "home_win", "D": "draw", "A": "away_win"}))
    complete = df.home_score.notna() & df.away_score.notna()
    complete &= (df.home_score >= 0) & (df.away_score >= 0)
    if "status" in df:
        complete &= df.status.isna() | df.status.eq("FINISHED")
    expected = pd.Series(np.where(df.home_score > df.away_score, "home_win",
                        np.where(df.home_score < df.away_score, "away_win", "draw")), index=df.index)
    conflict = complete & df.result.notna() & df.result.ne(expected)
    if conflict.any():
        raise ValueError(f"{int(conflict.sum())} result labels disagree with final scores")
    df["result"] = expected.where(complete)
    for col in ODDS_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce") if col in df else np.nan
        df[col] = df[col].where(np.isfinite(df[col]) & df[col].gt(1))
    df["fixture_day"] = df.date.dt.normalize()
    return df


def canonical_matches(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Newest/most authoritative sources come last; retain complementary values."""
    normalized = [normalize_matches(f) for f in frames]
    normalized = [f for f in normalized if not f.empty]
    if not normalized:
        raise ValueError("No valid football fixtures available")
    df = pd.concat(normalized, ignore_index=True)
    if "data_source" in df:
        df = df[~df.data_source.fillna("").str.contains("sample|synthetic", case=False, regex=True)]
    # Outcome conflicts across sources must not disappear during deduplication.
    keys = ["fixture_day", "home_key", "away_key"]
    conflicts = df.groupby(keys)["result"].nunique().gt(1)
    if conflicts.any():
        raise ValueError(f"{int(conflicts.sum())} fixtures have conflicting results across sources")
    df = df.iloc[::-1].assign(_completed=df.result.notna())
    df = df.sort_values("_completed", ascending=False, kind="stable")
    df = df.groupby(keys, sort=False, as_index=False).first().drop(columns=["_completed"])
    if "status" in df:
        df.loc[df.result.notna(), "status"] = "FINISHED"
    return df.sort_values(["date", "home_key", "away_key"]).reset_index(drop=True)


def historical_frames(directory: Path) -> list[pd.DataFrame]:
    frames = []
    for path in sorted(directory.glob("*.csv")):
        if "sample" in path.stem.casefold() or "synthetic" in path.stem.casefold():
            continue
        if path.name.startswith("normalized_") and (directory / path.name[11:]).exists():
            continue
        df = pd.read_csv(path)
        if "data_source" not in df:
            df["data_source"] = "historical_csv"
        if "competition" not in df:
            df["competition"] = path.stem.removeprefix("normalized_").rsplit("_", 1)[0]
        # Normalized files used recycled per-file integer IDs. They are not provider IDs.
        df = df.drop(columns=["match_id"], errors="ignore")
        frames.append(df)
    return frames


def match_odds_to_fixtures(matches: pd.DataFrame, odds: pd.DataFrame,
                           exact_kickoff: bool = False) -> pd.DataFrame:
    """Attach offers only to an unambiguous team pair on the same UTC fixture day."""
    if odds.empty or "commence_time" not in odds:
        return pd.DataFrame()
    fixtures = normalize_matches(matches)
    offers = odds.drop(columns=["match_id"], errors="ignore").copy()
    offers["commence_time"] = parse_dates(offers.commence_time)
    offers["fixture_day"] = offers.commence_time.dt.normalize()
    for side in ["home", "away"]:
        names = offers[f"{side}_team"]
        canonical = f"canonical_{side}_team"
        if canonical in offers:
            names = offers[canonical].combine_first(names)
        offers[f"{side}_key"] = names.map(team_key)
    keys = ["fixture_day", "home_key", "away_key"]
    unique = fixtures[~fixtures.duplicated(keys, keep=False)]
    columns = keys + ["date"] + (["match_id"] if "match_id" in unique else [])
    joined = offers.merge(unique[columns], on=keys, how="inner", validate="many_to_one")
    return joined[joined.commence_time.eq(joined.date)] if exact_kickoff else joined


def merge_prematch_odds(matches: pd.DataFrame, odds: pd.DataFrame,
                        exact_kickoff: bool = False) -> pd.DataFrame:
    df = normalize_matches(matches)
    joined = match_odds_to_fixtures(df, odds, exact_kickoff=exact_kickoff)
    if joined.empty:
        return df
    joined["updated_at"] = parse_dates(joined.updated_at)
    joined = joined[joined.updated_at.notna() & (joined.updated_at < joined.date)]
    keys = ["fixture_day", "home_key", "away_key"]
    joined = joined.sort_values("updated_at").drop_duplicates(keys + ["bookmaker"], keep="last")
    for col in ODDS_COLUMNS:
        joined[col] = pd.to_numeric(joined[col], errors="coerce") if col in joined else np.nan
        joined[col] = joined[col].where(np.isfinite(joined[col]) & joined[col].gt(1))
    joined = joined.dropna(subset=ODDS_COLUMNS)
    avg = joined.groupby(keys)[ODDS_COLUMNS].mean()
    merged = df.merge(avg, on=keys, how="left", suffixes=("", "_offer"), validate="many_to_one")
    for col in ODDS_COLUMNS:
        merged[col] = merged[col + "_offer"].combine_first(merged[col])
    return merged.drop(columns=[c + "_offer" for c in ODDS_COLUMNS])
