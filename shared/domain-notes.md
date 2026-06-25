# Domain Notes — FootballHeritage

## Sports Coverage
- **Primary:** Football (soccer) — European leagues, international competitions
- **Secondary:** Basketball (NBA, college), potentially extending to additional sports
- **Data Sources:** Public sports APIs, web scraping from bookmakers and stats sites

## Prediction Models
- Models generate probability estimates for match outcomes
- Features include: team form, head-to-head history, player injuries, ELO ratings, market odds
- Model retraining cadence: weekly (aligned with matchweek schedules)
- Accuracy tracked and reported in pipeline monitoring

## Responsible Gambling
- Core platform feature — not an afterthought
- Features: deposit limits, loss limits, session timeouts, self-exclusion, reality checks
- All features must work cross-session (user cannot bypass by logging out/in)
- Compliance with relevant gambling regulations (UKGC, MGA, or local equivalent)

## Integration Points
- Pipeline writes predictions and odds data to shared database
- Backend serves as the single API gateway for frontend and chatbot
- Chatbot accesses prediction data via backend API
- Frontend consumes REST APIs and WebSocket for real-time odds updates
