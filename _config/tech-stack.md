# Tech Stack — FootballHeritage

## Backend
- **Language:** Rust (latest stable)
- **Framework:** Actix-web
- **Database:** PostgreSQL (via SQLx)
- **Auth:** JWT-based authentication, bcrypt password hashing
- **Async Runtime:** Tokio

## Frontend
- **Language:** TypeScript / JavaScript
- **Framework:** React 18+
- **Build Tool:** Vite
- **State Management:** React Context + hooks
- **Routing:** React Router
- **Styling:** CSS Modules / Tailwind CSS (verify)
- **Testing:** Playwright (E2E), Vitest (unit)

## Data Pipeline
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **ETL:** Custom scrapers + pandas
- **ML:** scikit-learn, joblib (predictions)
- **Task Scheduling:** Custom scheduler (check pipeline/scheduler.py)
- **Data Sources:** Sports APIs (odds, scores), web scraping

## Chatbot
- **Language:** Node.js / TypeScript
- **Framework:** Genkit (Google AI)
- **LLM Integration:** Gemini or OpenAI (verify)
- **Memory:** Context window management, session handling

## Infrastructure
- **Containerization:** Docker
- **CI/CD:** GitHub Actions (from `.github/` in frontend)
- **Monitoring:** TBD (check for existing dashboard configs)
- **Hosting:** TBD — likely cloud VPS or container platform

## Data Flow
```
Sports APIs / Web Scrapers
    ↓
Pipeline (Python) — ETL + ML Predictions
    ↓ (REST / DB write)
Backend (Rust/Actix) — API Server
    ↓ (REST / WS)
Frontend (React) — Web UI
Chatbot (Genkit) — AI Assistant
```
