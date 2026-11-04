# Soccer event data and Monte Carlo simulation feasibility

Verified 22 October 2026. Scope: source discovery and a bounded acquisition pilot.
No simulator has been trained, no Monte Carlo forecast has been produced, and no
production model, database, API or scheduler has been changed.

## Decision

Yes: public soccer event streams can support a stochastic simulator of possessions,
actions, goals and player/team match statistics. Start with a stateful possession
model and derive the score and statistics from each generated match. Continuous
movement of all players and the ball requires tracking data; event streams alone
cannot reconstruct the actual physical match or establish tactical counterfactuals.

Recommend Wyscout's published historical archive as the initial training candidate
because its dataset metadata explicitly identifies CC BY 4.0. Use StatsBomb Open
Data for a separate research prototype, subject to its restrictive public-data
agreement. Current-season coverage and player histories need a separate inventory;
these archives do not establish that every upcoming fixture can be modeled well.

## Sources and R packages

| Source/tool | Verified availability and detail | Recommended role / limitation |
|---|---|---|
| [Wyscout public archive](https://figshare.com/collections/Soccer_match_event_dataset/4415000) | Author paper describes 2017/18 top-five European leagues, Euro 2016 and World Cup 2018: 1,941 matches. Events contain period-relative seconds, player/team IDs, event/subevent, positions and tags. | Initial historical event-model dataset. Old teams/rosters are unsuitable as current player form. Events/Matches/Players/Teams metadata each explicitly lists CC BY 4.0. |
| [StatsBomb Open Data](https://github.com/hudl/open-data) | Direct JSON: competitions, matches, events, lineups; 360 files for selected matches. Live inventory contained 80 competition-season records and 51 Euro 2024 matches. Competition presence does not imply complete-season coverage. | Rich research event source, including passes, carries, pressures, shots/xG and substitutions. Public agreement restricts commercial exploitation of data and derived analysis. |
| [StatsBombR](https://github.com/hudl/StatsBombR) | Official R wrapper, README updated April 2026; `FreeCompetitions()`, `FreeMatches()`, `get.matchFree()`, cleaning helpers. Paid API also supported. | Best verified R starting point for detailed public events. Wrapper availability does not change dataset rights or extend coverage. |
| [worldfootballR](https://github.com/JaseZiv/worldfootballR) | GitHub says archived 18 September 2025. Wrapper for FBref, Transfermarkt and Understat. | Supplementary historical summaries/shot data only after route checks; unsuitable as the primary event ingestion dependency. Shot-only data cannot fit full possession transitions. |
| [soccermatics](https://github.com/JoGall/soccermatics) | R visualisation/analysis tools for event and tracking data, with sample datasets. | Useful event QA, shot maps and spatial plots; not a broad current match feed or a complete simulator. |
| [Metrica sample data](https://github.com/metrica-sports/sample-data) | Three sample games; synchronized tracking/events, earlier games anonymized. | Test spatial/tracking ingestion. Too small and anonymized for broad named-player forecasts; README acknowledgement request is not a blanket commercial license. |
| [OpenSTARLab Event](https://github.com/open-starlab/Event) | Python framework for training, inference and simulation of soccer event models, including Seq2Event and related baselines. | Research benchmark and later comparison. Inspect preprocessing, supported outputs and rollout behavior before integration; next-event metrics do not prove full-match calibration. Code license is separate from training-data rights. |

R is optional: download the published JSON directly and use Python for the existing
pipeline, or acquire/inspect in R and export a shared Arrow/Parquet schema. A package
is a client, not a data license. Prefer published downloads to scraping rendered
match pages. Commentary feeds covering only major incidents are insufficient.

### License evidence

Scrapling fetched the original Figshare collection API and individual dataset
metadata, not a third-party license summary:

- Players: `https://api.figshare.com/v2/articles/7765196`
- Teams: `https://api.figshare.com/v2/articles/7765310`
- Matches: `https://api.figshare.com/v2/articles/7770599`
- Events: `https://api.figshare.com/v2/articles/7770422`

All four return `license.name = CC BY 4.0`. The events ZIP is 77,323,413 bytes;
the matches ZIP is 645,097 bytes. These ZIPs were **not** downloaded in this pilot.
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) permits commercial
adaptation with attribution, a license link and change notices; preserve the
dataset citation and provider provenance in derived assets.

The downloaded [StatsBomb public agreement](https://github.com/hudl/open-data/blob/master/LICENSE.pdf),
last updated 8 September 2023, prohibits commercial exploitation of data and
derived analysis in section 1.2.2 and restricts redistribution in 1.2.1. Section
1.4 requires its logo on publications. Do not promote this research capture or
models derived from it into FootballHeritage's commercial product without
appropriate separate rights. Local raw data and CSV projections remain ignored.

## Acquisition pilot and verification

Run from repository root using the existing Scrapling environment:

```powershell
.\pipeline\.venv-scrapling\Scripts\python.exe stages/01-discovery/output/probe-soccer-events-20261022.py
```

The collector reuses `pipeline/etl/scrapling_transport.py`: robots-policy checks,
bounded HTTP requests and preserved response bytes. It captures source URLs,
retrieval timestamps and SHA-256 hashes in a local manifest. A mutable branch URL
is not a pinned release; the checksums identify these particular captured bytes.

| Match | Date | Events | Reconstructed score | Result |
|---|---|---:|---|---|
| Germany–Scotland, 3930158 | 2024-06-14 | 3,372 | 5–1 | All five checks pass |
| Hungary–Switzerland, 3930159 | 2024-06-15 | 3,370 | 1–3 | All five checks pass |
| Spain–Croatia, 3930160 | 2024-06-15 | 3,793 | 3–0 | All five checks pass |
| Total | | 10,535 | | 15/15 checks |

Checks: unique event IDs, strictly increasing source indices, lineup teams matching
fixture teams, both regulation periods ending, and event-derived goals matching
match metadata. Own goals are counted once using `Own Goal Against`, avoiding the
paired `Own Goal For` duplicate. Period 5 shootouts are excluded from match goals.

Dates, teams and scores were independently corroborated against
[UEFA's official Euro 2024 results](https://www.uefa.com/uefaeuro/history/news/0275-151eb1c333ea-d30deec67b13-1000--uefa-euro-2024-results-when-and-where-were-the-matches/).
Individual passes, timestamps and player actions have not been independently
verified against video or a second event provider. This is provider-attributed
event data with integrity checks, not a claim that every action is ground truth.

Local files are in `soccer-events-pilot-20261022/`: raw JSON, lineup JSON, projected
event CSVs, license, Figshare metadata and `manifest.json`. The CSV projection is
for discovery only; nested raw qualifiers, related event IDs, substitution
replacements, duration and shot details remain necessary for the eventual dataset.

## Dataset contract for implementation

Preserve raw input immutably; version normalisation independently. Recommended tables:

| Table | Required content |
|---|---|
| source_manifest | Provider, URL, retrieval/version/hash, agreement/citation, coverage scope |
| matches | Provider IDs, competition/season, date/kickoff, home/away IDs, regulation result, extra-time result, shootout result, status |
| players_and_lineups | Stable provider IDs, role, starting/substitute status, substitutions, dismissals and active intervals |
| events | Match/event ID, source order, period and period clock, actor/team, action/subtype, possession, locations, outcome and qualifiers |
| states | Score **before** action, active players, possession side, field zone, clock, restart/open play, previous actions |

Do not merge providers on display names alone. Preserve original coordinate systems
and direction semantics; add a documented canonical transform. StatsBomb's 120x80
coordinates are provider units, not measured metres. Period clocks must retain
stoppage time without overlapping the next half; simultaneous/paired events cannot
be treated as sequential independent decisions. Provider definitions of tackles,
assists, duels and shots on target differ: publish definitions with every output.

Required ingestion gates: complete period coverage, source deduplication, roster
membership/active-player checks, valid coordinates and clocks, reconciled goals,
quarantined incomplete fixtures, and explicit known missing fields. Distinguish
missing from zero. Add a provider-specific action adapter that coalesces paired
events before fitting; raw event rows are not one-to-one simulation decisions.

## Simulation design

Start with a hierarchical semi-Markov model: the next action and time to that
action depend on current match state and recent history. Use regularized team,
role and player effects, pooled toward competition priors when history is sparse.

1. Sample lineup/minutes scenarios from information available at prediction time.
2. Initialize kickoff, score, ball zone, possession and active-player state.
3. Sample elapsed time, actor, action, destination and outcome conditional on state.
4. Update possession, location, score, restarts, cards and active players. Model
   substitutions and dismissal consequences; sample stoppage time. Rule out
   impossible actors/actions and apply competition-specific extra-time/shootout rules.
5. Derive goals, shots, shots on target, passes/completions, assists and keeper saves
   from those same events using explicit definitions. Add cards/corners only when
   event coverage and reconstruction checks support them.
6. Repeat for each eligible scheduled fixture with reproducible independent seeds;
   retain prediction-time inputs, dataset/model version and simulation count.

Outputs per fixture: scoreline probability matrix, home/draw/away probabilities,
goal-difference and total-goal distributions, both-teams-to-score probabilities,
and player/team count distributions with quantiles and correlations. Keep 90-minute,
extra-time and qualification outcomes separate. A player goal must increment the
team score; an own goal follows its separate attribution rule.

Use 10,000 runs for development and test 50,000 against a convergence threshold.
For a probability near 50%, 50,000 independent runs give approximately +/-0.44
percentage points of 95% Monte Carlo sampling uncertainty, **not** model uncertainty.
Sample parameter uncertainty separately. More runs cannot repair biased transitions.
Monte Carlo approximates an outcome distribution; it cannot enumerate every possible
event sequence, guarantee rare-outcome coverage or reproduce the future actual game.

Train on earlier matches; validate/test on later whole matches. Never randomly split
events from the same match between train and test. Historical replay must use only
pre-kickoff information for that fixture; exclude its observed shots/xG, actual
substitutions and future roster information from pre-match inputs.

Validation must cover next-action/time calibration **and** free-running full-match
rollouts: goals/shots/pass/possession/minutes distributions, score dependence, player
count dispersion, interval coverage and football-rule invariants. Use log loss/Brier
for outcomes and proper count-distribution scores. Compare against goal-model and
possession-resampling baselines on the same chronological holdout. Expected-threat
or VAEP action values alone do not define a generative simulator.

## Project fit, gaps and next deliverable

Repository-wide text search found NFL play-by-play ingestion in
`etl/fetch_gridiron_sources.py` and causal efficiency features in
`models/gridiron_efficiency.py`; no matching soccer event collector or Monte Carlo
simulator was found. These are search findings, not a full dependency audit.
Fallow was attempted with `npx --no-install fallow --summary`, but no installed
package was available; no current Fallow analysis is claimed. The workspace had
extensive pre-existing changes, which were preserved. Rscript was not on PATH;
the R snippet below was checked against official documentation but not executed.

The next build deliverable is a Wyscout archive collector/normaliser with a complete
coverage manifest and score/player-interval validation, followed by the fitted
possession baseline and held-out rollout report. Only after that evidence should
we integrate per-fixture simulation jobs and API distributions. Current squad and
event-source coverage is a prerequisite for credible current player forecasts.

Discovery findings are ready for the project discovery gate; implementation and
model quality remain unproven. This feasibility investigation does not satisfy the
larger production simulation goal.

## R starting example (research only; not executed)

```r
# Follow the official StatsBombR installation and data-use agreement first.
library(StatsBombR)
competitions <- FreeCompetitions()
euro <- subset(competitions, competition_id == 55 & season_id == 282)
matches <- FreeMatches(euro)
events <- get.matchFree(matches[1, , drop = FALSE])
# Preserve raw qualifiers and source IDs before any cleaning/export.
```

Official package documentation: https://github.com/hudl/StatsBombR
Wyscout author paper: https://doi.org/10.1038/s41597-019-0247-7
Python public-archive loader: https://socceraction.readthedocs.io/en/stable/documentation/data/wyscout.html
