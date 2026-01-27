from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

sys.path.append(str(Path(__file__).parent.parent))

from config import LOG_LEVEL
from heritage_config import DATABASE_URI as HERITAGE_DATABASE_URI
from etl.utils import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)


@dataclass(frozen=True)
class Offer:
    provider_event_id: str
    event_id: str
    book_key: str
    market: str
    selection: str
    line: Optional[float]
    odds: float
    source_updated_at: Optional[str]


def _implied_prob(decimal_odds: float) -> float:
    return 1.0 / decimal_odds


def _devig_two_way(odds_a: float, odds_b: float) -> Tuple[float, float, float]:
    p1 = _implied_prob(odds_a)
    p2 = _implied_prob(odds_b)
    total = p1 + p2
    if total <= 0:
        raise ValueError("invalid implied probabilities")
    return p1 / total, p2 / total, total - 1.0


def _expected_value(true_prob: float, decimal_odds: float, stake: float) -> Tuple[float, float]:
    win_profit = stake * (decimal_odds - 1.0)
    ev = (true_prob * win_profit) - ((1.0 - true_prob) * stake)
    return ev, ev / stake


def _arb_two_way(odds_a: float, odds_b: float, total_stake: float) -> Optional[Tuple[float, float, float]]:
    inv_a = 1.0 / odds_a
    inv_b = 1.0 / odds_b
    s = inv_a + inv_b
    if s >= 1.0:
        return None
    edge = 1.0 - s
    stake_a = total_stake * (inv_a / s)
    stake_b = total_stake * (inv_b / s)
    return edge, stake_a, stake_b


def _load_two_way_offer_groups(conn, limit_events: int = 200) -> Dict[Tuple[str, str, Optional[float], str], List[Offer]]:
    """Group offers into 2-way markets we can compute now.

    Key: (provider_event_id, market, line, book_key)
    Value: offers list (should contain exactly 2 selections for 2-way markets)

    We include:
    - totals: OVER/UNDER
    - spreads: HOME/AWAY
    - h2h: HOME/AWAY only (skip DRAW)
    """

    rows = conn.execute(
        text(
            """
            SELECT
                oo.provider_event_id,
                oo.event_id,
                oo.book_key,
                oo.market,
                oo.selection,
                oo.line,
                oo.odds_decimal,
                oo.source_updated_at
            FROM odds_offers oo
            WHERE oo.event_id IS NOT NULL
              AND oo.market IN ('totals', 'spreads', 'h2h')
              AND (
                    (oo.market = 'totals' AND oo.selection IN ('OVER','UNDER'))
                 OR (oo.market = 'spreads' AND oo.selection IN ('HOME','AWAY'))
                 OR (oo.market = 'h2h' AND oo.selection IN ('HOME','AWAY'))
              )
            ORDER BY oo.event_id, oo.market, oo.line, oo.book_key
            """
        )
    ).fetchall()

    groups: Dict[Tuple[str, str, Optional[float], str], List[Offer]] = {}
    for r in rows:
        offer = Offer(
            provider_event_id=r[0],
            event_id=str(r[1]),
            book_key=r[2],
            market=r[3],
            selection=r[4],
            line=r[5],
            odds=float(r[6]),
            source_updated_at=r[7].isoformat() if hasattr(r[7], "isoformat") and r[7] else (str(r[7]) if r[7] else None),
        )
        key = (offer.provider_event_id, offer.market, offer.line, offer.book_key)
        groups.setdefault(key, []).append(offer)

    # Trim to most recent N events by event_date (to keep compute bounded)
    # We do it by collecting distinct event_ids from groups.
    event_ids = sorted({g[0] for g in groups.keys()})
    if limit_events and len(event_ids) > limit_events:
        allowed = set(event_ids[:limit_events])
        groups = {k: v for k, v in groups.items() if k[0] in allowed}

    return groups


def compute_and_store_intelligence(stake: float = 100.0) -> Dict[str, int]:
    engine = create_engine(HERITAGE_DATABASE_URI)

    devig_rows = 0
    ev_rows = 0
    arb_rows = 0

    try:
        with engine.begin() as conn:
            groups = _load_two_way_offer_groups(conn)

            # Reference books for true probability baseline
            ref_books = ["pinnacle", "betfair"]

            insert_devig = text(
                """
                INSERT INTO devigged_odds (
                    event_id, pipeline_match_id, bookmaker, market,
                    outcome_a, outcome_b,
                    odds_a, odds_b,
                    fair_prob_a, fair_prob_b, vig,
                    source_updated_at
                ) VALUES (
                    :event_id, :pipeline_match_id, :bookmaker, :market,
                    :outcome_a, :outcome_b,
                    :odds_a, :odds_b,
                    :fair_prob_a, :fair_prob_b, :vig,
                    :source_updated_at
                )
                ON CONFLICT DO NOTHING
                """
            )

            insert_ev = text(
                """
                INSERT INTO ev_bets (
                    event_id, pipeline_match_id, bookmaker, market, selection,
                    odds, stake, true_probability, expected_value, expected_value_pct,
                    source_updated_at
                ) VALUES (
                    :event_id, :pipeline_match_id, :bookmaker, :market, :selection,
                    :odds, :stake, :true_probability, :expected_value, :expected_value_pct,
                    :source_updated_at
                )
                ON CONFLICT DO NOTHING
                """
            )

            insert_arb = text(
                """
                INSERT INTO arbitrage (
                    event_id, pipeline_match_id, market, selection_a, selection_b,
                    book_a, book_b, odds_a, odds_b,
                    arb_percentage, total_stake, stake_a, stake_b,
                    source_updated_at
                ) VALUES (
                    :event_id, :pipeline_match_id, :market, :selection_a, :selection_b,
                    :book_a, :book_b, :odds_a, :odds_b,
                    :arb_percentage, :total_stake, :stake_a, :stake_b,
                    :source_updated_at
                )
                ON CONFLICT DO NOTHING
                """
            )

            # Precompute devig per group
            devig_cache: Dict[Tuple[str, str, Optional[float], str], Tuple[Offer, Offer, float, float, float]] = {}

            for key, offers in groups.items():
                if len(offers) != 2:
                    continue

                # Sort stable so outcome_a/outcome_b consistent
                offers_sorted = sorted(offers, key=lambda o: o.selection)
                a, b = offers_sorted[0], offers_sorted[1]

                try:
                    fair_a, fair_b, vig = _devig_two_way(a.odds, b.odds)
                except Exception:
                    continue

                devig_cache[key] = (a, b, fair_a, fair_b, vig)

                conn.execute(
                    insert_devig,
                    {
                        "event_id": a.event_id,
                        "pipeline_match_id": a.provider_event_id,
                        "bookmaker": a.book_key,
                        "market": a.market,
                        "outcome_a": a.selection,
                        "outcome_b": b.selection,
                        "odds_a": a.odds,
                        "odds_b": b.odds,
                        "fair_prob_a": fair_a,
                        "fair_prob_b": fair_b,
                        "vig": vig,
                        "source_updated_at": a.source_updated_at,
                    },
                )
                devig_rows += 1

            # Compute a simple true-prob baseline per (provider_event_id, market, line)
            baseline: Dict[Tuple[str, str, Optional[float], str], float] = {}
            # key: (provider_event_id, market, line, selection)

            # Prefer reference books, else average devig across books
            by_market_line: Dict[Tuple[str, str, Optional[float]], List[Tuple[str, Tuple[Offer, Offer, float, float, float]]]] = {}
            for key, v in devig_cache.items():
                provider_event_id, market, line, book_key = key
                by_market_line.setdefault((provider_event_id, market, line), []).append((book_key, v))

            for ml_key, items in by_market_line.items():
                provider_event_id, market, line = ml_key

                ref_item = None
                for book_key, v in items:
                    if book_key in ref_books:
                        ref_item = v
                        break

                if ref_item is not None:
                    a, b, fair_a, fair_b, _vig = ref_item
                    baseline[(provider_event_id, market, line, a.selection)] = fair_a
                    baseline[(provider_event_id, market, line, b.selection)] = fair_b
                    continue

                # average across books
                accum: Dict[str, float] = {}
                counts: Dict[str, int] = {}
                for _book_key, v in items:
                    a, b, fair_a, fair_b, _vig = v
                    accum[a.selection] = accum.get(a.selection, 0.0) + fair_a
                    accum[b.selection] = accum.get(b.selection, 0.0) + fair_b
                    counts[a.selection] = counts.get(a.selection, 0) + 1
                    counts[b.selection] = counts.get(b.selection, 0) + 1

                for sel, total in accum.items():
                    baseline[(provider_event_id, market, line, sel)] = total / max(1, counts.get(sel, 1))

            # EV rows for every offer we can baseline
            for key, offers in groups.items():
                provider_event_id, market, line, book_key = key
                for offer in offers:
                    true_p = baseline.get((provider_event_id, market, line, offer.selection))
                    if true_p is None:
                        continue
                    if true_p <= 0 or true_p >= 1:
                        continue

                    ev, ev_pct = _expected_value(true_p, offer.odds, stake)
                    conn.execute(
                        insert_ev,
                        {
                            "event_id": offer.event_id,
                            "pipeline_match_id": offer.provider_event_id,
                            "bookmaker": offer.book_key,
                            "market": offer.market,
                            "selection": offer.selection,
                            "odds": offer.odds,
                            "stake": Decimal(str(stake)),
                            "true_probability": true_p,
                            "expected_value": ev,
                            "expected_value_pct": ev_pct,
                            "source_updated_at": offer.source_updated_at,
                        },
                    )
                    ev_rows += 1

            # Arbitrage: best odds per selection per (provider_event_id, market, line)
            for ml_key, items in by_market_line.items():
                provider_event_id, market, line = ml_key

                best_by_sel: Dict[str, Tuple[str, float, str]] = {}
                # selection -> (book_key, odds, event_id)
                for book_key, v in items:
                    a, b, _fa, _fb, _vig = v
                    for offer in (a, b):
                        curr = best_by_sel.get(offer.selection)
                        if curr is None or offer.odds > curr[1]:
                            best_by_sel[offer.selection] = (offer.book_key, offer.odds, offer.event_id)

                if len(best_by_sel) != 2:
                    continue

                sels = sorted(best_by_sel.keys())
                sel_a, sel_b = sels[0], sels[1]
                book_a, odds_a, event_id = best_by_sel[sel_a]
                book_b, odds_b, _event_id2 = best_by_sel[sel_b]

                arb = _arb_two_way(odds_a, odds_b, stake)
                if arb is None:
                    continue

                edge, stake_a, stake_b = arb
                conn.execute(
                    insert_arb,
                    {
                        "event_id": event_id,
                        "pipeline_match_id": provider_event_id,
                        "market": market,
                        "selection_a": sel_a,
                        "selection_b": sel_b,
                        "book_a": book_a,
                        "book_b": book_b,
                        "odds_a": odds_a,
                        "odds_b": odds_b,
                        "arb_percentage": edge,
                        "total_stake": Decimal(str(stake)),
                        "stake_a": Decimal(str(stake_a)),
                        "stake_b": Decimal(str(stake_b)),
                        "source_updated_at": None,
                    },
                )
                arb_rows += 1

    except SQLAlchemyError as e:
        logger.error("Compute intelligence failed: %s", str(e), exc_info=True)
        raise

    logger.info(
        "Computed intelligence rows: devig=%s ev=%s arb=%s",
        devig_rows,
        ev_rows,
        arb_rows,
    )

    return {"devig_rows": devig_rows, "ev_rows": ev_rows, "arb_rows": arb_rows}


def main():
    compute_and_store_intelligence(stake=100.0)


if __name__ == "__main__":
    main()
