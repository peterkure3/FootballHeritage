"""Odds conversion, devigging, EV and arbitrage math shared by routers."""

from typing import Dict, Optional


def implied_probability_from_decimal(decimal_odds: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("decimal odds must be > 1")
    return 1.0 / decimal_odds


def devig_two_way(decimal_odds_a: float, decimal_odds_b: float) -> Dict[str, float]:
    p1 = implied_probability_from_decimal(decimal_odds_a)
    p2 = implied_probability_from_decimal(decimal_odds_b)
    p_total = p1 + p2
    if p_total <= 0:
        raise ValueError("invalid implied probabilities")
    fair_p1 = p1 / p_total
    fair_p2 = p2 / p_total
    vig = p_total - 1.0
    return {"fair_prob_a": fair_p1, "fair_prob_b": fair_p2, "vig": vig}


def win_profit_from_decimal(decimal_odds: float, stake: float) -> float:
    if decimal_odds <= 1.0:
        raise ValueError("decimal odds must be > 1")
    if stake <= 0:
        raise ValueError("stake must be > 0")
    return stake * (decimal_odds - 1.0)


def expected_value(true_probability: float, decimal_odds: float, stake: float) -> Dict[str, float]:
    if true_probability < 0 or true_probability > 1:
        raise ValueError("true_probability must be in [0, 1]")
    win_profit = win_profit_from_decimal(decimal_odds, stake)
    ev = (true_probability * win_profit) - ((1.0 - true_probability) * stake)
    ev_pct = ev / stake
    return {"expected_value": ev, "expected_value_pct": ev_pct}


def arbitrage_two_way(decimal_odds_a: float, decimal_odds_b: float, total_stake: float) -> Optional[Dict[str, float]]:
    if decimal_odds_a <= 1.0 or decimal_odds_b <= 1.0:
        raise ValueError("decimal odds must be > 1")
    if total_stake <= 0:
        raise ValueError("total_stake must be > 0")
    inv_a = 1.0 / decimal_odds_a
    inv_b = 1.0 / decimal_odds_b
    inv_sum = inv_a + inv_b
    if inv_sum >= 1.0:
        return None
    edge = 1.0 - inv_sum
    stake_a = total_stake * (inv_a / inv_sum)
    stake_b = total_stake * (inv_b / inv_sum)
    return {"arb_percentage": edge, "stake_a": stake_a, "stake_b": stake_b}



def american_to_decimal(american_odds: float) -> float:
    """Convert American odds to decimal odds."""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def decimal_to_american(decimal_odds: float) -> float:
    """Convert decimal odds to American odds."""
    if decimal_odds >= 2.0:
        return (decimal_odds - 1) * 100
    else:
        return -100 / (decimal_odds - 1)

