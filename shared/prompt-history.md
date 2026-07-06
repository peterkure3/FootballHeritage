You are a senior quantitative engineer and full-stack developer building a professional sports betting platform.

Your task is to implement three core betting intelligence systems:

Devigging (true probability extraction)

Expected Value (EV) calculation

Arbitrage detection and stake allocation


🎯 GOAL

Create a production-ready betting intelligence layer that:

Converts bookmaker odds into true probabilities

Calculates expected value per bet

Detects cross-book arbitrage opportunities

Stores all outputs in Postgres

Exposes clean APIs for frontend dashboards

🧱 SYSTEM ARCHITECTURE RULES
Python (FastAPI) handles:

Odds normalization

Devigging math

Probability modeling

EV computation

Arbitrage detection

Writing computed outputs into PostgreSQL

Rust backend handles:

High-performance scanning

Business rules

Filtering thresholds

API endpoints for frontend consumption

No statistical modeling logic

React frontend handles:

Visualization only

No betting math

Reads computed values from backend APIs


📐 FEATURE 1 — DEVIGGING
Objective

Remove bookmaker margin and extract fair probabilities.

Required formulas
Convert American odds → Decimal

If odds > 0:

decimal = 1 + odds / 100


If odds < 0:

decimal = 1 + 100 / abs(odds)

Implied probability
P = 1 / decimal_odds

Remove vig
P_total = P1 + P2
Fair_P1 = P1 / P_total
Fair_P2 = P2 / P_total
Vig = P_total - 1

Required FastAPI functions

Convert American odds

Calculate implied probabilities

Remove vig proportionally

Return fair probabilities and margin

Required database table
devigged_odds
- id (uuid)
- match_id
- bookmaker
- odds_a
- odds_b
- fair_prob_a
- fair_prob_b
- vig
- created_at

📈 FEATURE 2 — EXPECTED VALUE (EV)
Objective

Determine long-term profitability of a bet.

Formula
EV = (P × W) − ((1 − P) × L)


Where:

P = true probability (from devigging or ML)

W = net profit if bet wins

L = stake amount

Win profit calculation

For +150 odds:

profit = stake × (odds / 100)


For −110 odds:

profit = stake × (100 / abs(odds))

Required FastAPI service

Input: probability, odds, stake

Output: expected value (float)

Support batch computation

Required database table
ev_bets
- id
- match_id
- market
- odds
- stake
- true_probability
- expected_value
- created_at

Rust backend rules

Expose EV values via API

Allow filtering:

EV > 0

EV > 2%

EV > 5%

EV > 10%

🔁 FEATURE 3 — ARBITRAGE
Objective

Detect guaranteed profit across bookmakers.

Arbitrage condition
(1 / odds_a) + (1 / odds_b) < 1


If true → arbitrage exists.

Arbitrage edge
edge = 1 - ((1 / odds_a) + (1 / odds_b))

Stake allocation formula
stake_a = total_stake × (1/odds_a) / inv_sum
stake_b = total_stake × (1/odds_b) / inv_sum

Required FastAPI logic

Compare odds across all bookmakers

Detect arbitrage opportunities

Compute stake distribution

Save results to database

Required database table
arbitrage
- id
- match_id
- book_a
- book_b
- odds_a
- odds_b
- arb_percentage
- stake_a
- stake_b
- created_at

Rust backend responsibilities

Extremely fast pairwise scanning

Ignore same-book comparisons

Persist arbitrage opportunities

Expose real-time arbitrage feed API

🖥 FRONTEND REQUIREMENTS
React dashboards must include:
Devigging view

Book odds

True probability

Book margin %

EV dashboard

Market

Odds

Model probability

Expected value

Positive EV highlighted

Arbitrage table

Match

Book A / Book B

Odds comparison

Guaranteed profit %

Stake split

⚠️ ENGINEERING RULES

No betting math inside React

No ML logic inside Rust

Python performs all calculations

Rust focuses on performance and safety

Postgres is the source of truth

All values must be reproducible

✅ DELIVERABLES

The implementation must include:

FastAPI services for devigging, EV, arbitrage

PostgreSQL schema and migrations

Rust API endpoints

Typed Rust models

React UI components using TailwindCSS

Clear separation of concerns

Production-ready folder structure

🚀 RESULT

After implementation, the platform must be able to:

Show true bookmaker probabilities

Identify profitable bets mathematically

Detect guaranteed arbitrage opportunities

Rank bets by edge

Power advanced betting strategies later