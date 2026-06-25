# Performance Report — Stage 04

## Backend API Latency (Estimated)
| Endpoint | Expected Latency | Notes |
|----------|-----------------|-------|
| `GET /health` | < 5ms | No DB query |
| `GET /api/v1/sports` | 10-20ms | Two aggregate queries with indexes |
| `GET /api/v1/betting/events` | 15-30ms | Indexed on sport + status |
| `GET /api/v1/betting/events/{id}` | < 5ms | Primary key lookup |
| `POST /api/v1/betting/bets` | 30-50ms | Transaction with multiple checks |
| `POST /api/v1/chat` | 100-500ms | Depends on Gemini + Redis cache |
| `GET /api/v1/player-props` | 10-20ms | Indexed on sport + is_active |

*Benchmarking requires production-level load testing (k6, locust, or similar).*

## Frontend Performance
| Metric | Current | Target |
|--------|---------|--------|
| JS bundle size | 663 KB (155 KB gzip) | < 200 KB gzip |
| CSS bundle size | 82 KB (12 KB gzip) | < 20 KB gzip |
| Build time | 39s | < 30s |

## Pipeline Throughput
| Stage | Current | Bottleneck |
|-------|---------|------------|
| Data fetch (per sport) | 1-3s | The Odds API rate limit (free tier) |
| Transform | 5-10s | Parquet I/O |
| Model training | 2-5 min | Stacking ensemble (4 base classifiers) |
| Prediction (batch) | 5-15s | Feature engineering + model inference |
| Intelligence compute | 10-30s | Devig/EV/arbitrage per match |

## RAG Chatbot Performance
| Metric | Current | Target |
|--------|---------|--------|
| Cached response | 15-18ms | < 20ms |
| Uncached response | 95-110ms | < 100ms |
| Cache hit rate | 65-70% | > 60% |
| Throughput | 120+ req/s | > 100 req/s |

## Recommendations
1. **Lazy load** non-critical routes in the frontend to reduce initial bundle size
2. **Add database connection pooling tuning** — current pool is 10-50 connections
3. **Benchmark player-props endpoint** under load once data is populated
4. **Consider Redis caching** for frequently queried endpoints (sports list, events)
