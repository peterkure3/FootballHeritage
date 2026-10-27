//! Existing Python AI-pick selection rules over published model outputs.
use serde_json::{json, Value};
use std::cmp::Ordering;

fn number(value: &Value) -> Option<f64> {
    value.as_f64().or_else(|| value.as_str()?.parse().ok())
}

struct Quote<'a> {
    edge: f64,
    expected_value: f64,
    index: usize,
    odds: f64,
    quote: &'a Value,
}

fn quote_order(left: &Quote<'_>, right: &Quote<'_>) -> Ordering {
    left.edge
        .total_cmp(&right.edge)
        .then_with(|| left.expected_value.total_cmp(&right.expected_value))
        .then(left.index.cmp(&right.index))
}

fn pick_order(left: &Value, right: &Value) -> Ordering {
    let left_value = left["pick_type"] == "value";
    let right_value = right["pick_type"] == "value";
    left_value
        .cmp(&right_value)
        .then_with(|| {
            number(&left[if left_value { "edge" } else { "model_prob" }])
                .unwrap_or(0.0)
                .total_cmp(
                    &number(&right[if right_value { "edge" } else { "model_prob" }]).unwrap_or(0.0),
                )
        })
        .then_with(|| {
            number(&left["model_prob"])
                .unwrap_or(0.0)
                .total_cmp(&number(&right["model_prob"]).unwrap_or(0.0))
        })
}

pub fn rank(mut picks: Vec<Value>, limit: usize) -> Vec<Value> {
    // Stable sort retains input order for ties, matching Python's sorted().
    picks.sort_by(|left, right| pick_order(right, left));
    picks.truncate(limit);
    picks
}

pub fn build_picks(rows: &[Value], limit: usize) -> Vec<Value> {
    let mut picks = Vec::new();
    for row in rows {
        let probabilities: Option<Vec<f64>> = ["home_prob", "draw_prob", "away_prob"]
            .iter()
            .map(|key| number(&row[*key]))
            .collect();
        let Some(probabilities) = probabilities else {
            continue;
        };
        if !probabilities
            .iter()
            .all(|p| p.is_finite() && (0.0..=1.0).contains(p))
            || (probabilities.iter().sum::<f64>() - 1.0).abs() > 0.01
        {
            continue;
        }
        let (Some(home), Some(away)) = (row["home_team"].as_str(), row["away_team"].as_str())
        else {
            continue;
        };
        let names = [
            format!("{home} (Home Win)"),
            "Draw".to_string(),
            format!("{away} (Away Win)"),
        ];
        let mut candidates = Vec::new();
        if let Some(quotes) = row["quotes"].as_array() {
            for quote in quotes {
                for (index, key) in ["home_win", "draw", "away_win"].iter().enumerate() {
                    let Some(odds) = number(&quote[*key]).filter(|v| v.is_finite() && *v > 1.0)
                    else {
                        continue;
                    };
                    candidates.push(Quote {
                        edge: probabilities[index] - 1.0 / odds,
                        expected_value: probabilities[index] * odds - 1.0,
                        index,
                        odds,
                        quote,
                    });
                }
            }
        }
        let best = candidates
            .iter()
            .fold(None, |best: Option<&Quote<'_>>, candidate| {
                if best.is_none_or(|old| quote_order(candidate, old).is_gt()) {
                    Some(candidate)
                } else {
                    best
                }
            });
        let is_value = best.is_some_and(|candidate| candidate.edge >= 0.05);
        let index = if is_value {
            best.unwrap().index
        } else {
            (1..3).fold(0, |old, index| {
                if probabilities[index] > probabilities[old] {
                    index
                } else {
                    old
                }
            })
        };
        let selected = if is_value {
            best
        } else {
            candidates
                .iter()
                .filter(|candidate| candidate.index == index)
                .fold(None, |best: Option<&Quote<'_>>, candidate| {
                    if best.is_none_or(|old| quote_order(candidate, old).is_gt()) {
                        Some(candidate)
                    } else {
                        best
                    }
                })
        };
        let probability = probabilities[index];
        let mut pick = json!({});
        for key in [
            "match_id",
            "home_team",
            "away_team",
            "competition",
            "match_date",
            "model_version",
            "prediction_created_at",
        ] {
            pick[key] = row[key].clone();
        }
        pick["selection"] = json!(names[index]);
        pick["pick_type"] = json!(if is_value { "value" } else { "prediction" });
        pick["model_prob"] = json!(probability);
        for (index, key) in ["home_prob", "draw_prob", "away_prob"].iter().enumerate() {
            pick[*key] = json!(probabilities[index]);
        }
        pick["implied_prob"] = json!(selected.map(|value| 1.0 / value.odds));
        pick["decimal_odds"] = json!(selected.map(|value| value.odds));
        pick["edge"] = json!(selected.map(|value| value.edge));
        pick["edge_pct"] = json!(selected.map(|value| value.edge * 100.0));
        pick["expected_value"] = json!(selected.map(|value| probability * value.odds - 1.0));
        pick["recommended_stake"] = json!(selected.map(|_| 1.0));
        pick["bookmaker"] = selected.map_or(Value::Null, |value| value.quote["bookmaker"].clone());
        pick["odds_updated_at"] =
            selected.map_or(Value::Null, |value| value.quote["updated_at"].clone());
        pick["explanation"] = json!(if is_value {
            "Model probability exceeds the quoted odds-implied probability by at least five percentage points."
        } else if selected.is_some() {
            "The model's most likely result. No qualifying value edge is available from current bookmaker quotes."
        } else {
            "The model's most likely result. No recent bookmaker quote is available, so odds and value cannot be calculated."
        });
        picks.push(pick);
    }
    rank(picks, limit)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn equivalent(actual: &Value, expected: &Value, path: &str) {
        match (actual, expected) {
            (Value::Number(a), Value::Number(b)) => assert!(
                (a.as_f64().unwrap() - b.as_f64().unwrap()).abs() < 1e-12,
                "{path}"
            ),
            (Value::Array(a), Value::Array(b)) => {
                assert_eq!(a.len(), b.len(), "{path}");
                for (index, (a, b)) in a.iter().zip(b).enumerate() {
                    equivalent(a, b, &format!("{path}[{index}]"));
                }
            }
            (Value::Object(a), Value::Object(b)) => {
                assert_eq!(a.len(), b.len(), "{path}");
                for (key, value) in b {
                    equivalent(&a[key], value, &format!("{path}.{key}"));
                }
            }
            _ => assert_eq!(actual, expected, "{path}"),
        }
    }

    #[test]
    fn preserves_frozen_python_ranking_contract() {
        let contract: Value = serde_json::from_str(include_str!(
            "../tests/fixtures/ai_pick_selection_contract.json"
        ))
        .unwrap();
        for case in contract["cases"].as_array().unwrap() {
            let actual = build_picks(
                case["rows"].as_array().unwrap(),
                case["limit"].as_u64().unwrap() as usize,
            );
            equivalent(
                &json!(actual),
                &case["expected"],
                case["name"].as_str().unwrap(),
            );
        }
    }
}
