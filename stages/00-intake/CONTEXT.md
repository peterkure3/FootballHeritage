# Stage 00: Intake

## Inputs
| Source | What to Load |
|--------|--------------|
| `_config/glossary.md` | Domain vocabulary for consistent terminology |
| `README.md` | Existing project overview and setup instructions |
| `PROMPT.MD` | Any prior project briefs or context documents |
| `CODEBASE_INDEX.md` | Existing codebase index for asset inventory |

## Process
1. Interview stakeholders (product owner, engineers, domain experts) to capture goals, constraints, and risks
2. Inventory all existing code assets: backend API scope, frontend features, pipeline ETL jobs, chatbot capabilities
3. Document external data sources (sports APIs, scraping targets) and their access requirements
4. Capture regulatory and compliance requirements (gambling license, responsible gambling, data privacy)
5. Write the scope document and stakeholder map
6. Identify gaps between current state and desired outcomes

## Outputs
| File | Description |
|------|-------------|
| `output/scope-document.md` | Project goals, in-scope/out-of-scope features, constraints, risks |
| `output/stakeholder-map.md` | Stakeholders, their roles, and communication preferences |
| `output/_blockers.md` | Any immediate blockers discovered during intake |

## Gate
Stakeholder review and sign-off on the scope document. All parties must agree on in-scope and out-of-scope boundaries before proceeding.
