# Stage 01: Discovery

## Inputs
| Source | What to Load |
|--------|--------------|
| `00-intake/output/scope-document.md` | Agreed scope, goals, constraints |
| `_config/glossary.md` | Domain vocabulary for consistent terminology |
| `shared/domain-notes.md` | Existing domain knowledge and data source context |
| `pipeline/` | Existing ETL jobs, scraper configs, data models |
| `backend/src/` | Existing API structure, database schema |

## Process
1. Deep-dive into each sports data source: APIs (odds, scores, stats), web scrapers, historical data
2. Analyze existing pipeline architecture — identify bottlenecks, data quality issues, missing coverage
3. Research prediction modeling approaches — evaluate current models and competitor approaches
4. Map user journeys: bettor seeking advice, admin managing platform, analyst reviewing predictions
5. Document findings as a discovery dossier with actionable recommendations
6. Validate critical assumptions with stakeholders (data availability, model accuracy targets, scale)

## Outputs
| File | Description |
|------|-------------|
| `output/discovery-dossier.md` | Domain analysis, competitor landscape, data source evaluation, user journeys |
| `output/data-source-catalog.md` | All data sources: endpoints, refresh cadence, licensing, quality notes |
| `output/_blockers.md` | Data access blockers, licensing issues, technical risks |

## Gate
Discovery dossier reviewed and approved by engineering lead and product owner. Critical assumptions validated before architecture work begins.
