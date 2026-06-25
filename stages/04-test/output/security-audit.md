# Security Audit — Stage 04

## Scope
Audit of existing security controls across the FootballHeritage platform.

## Authentication & Authorization
| Control | Status | Notes |
|---------|--------|-------|
| JWT authentication | ✅ Implemented | Token-based with refresh, stored in sessionStorage |
| Session management | ✅ Implemented | In-memory DashMap with 15-min timeout, activity reset |
| Role-based access | ✅ Implemented | user / admin / superadmin roles with middleware guards |
| Account lockout | ✅ Implemented | After failed login attempts, configurable duration |
| Email verification | ✅ Implemented | Middleware check on sensitive operations |

## Data Protection
| Control | Status | Notes |
|---------|--------|-------|
| Wallet encryption | ✅ AES-256-GCM | Encrypted balance + IV stored per wallet |
| Password hashing | ✅ Argon2id / bcrypt | Via zxcvbn strength check |
| Environment secrets | ✅ .env files | API keys, JWT secret, DB passwords in .env |
| SQL injection | ✅ Parameterized queries | All queries use sqlx bind parameters |
| XSS protection | ✅ React + security headers | React auto-escapes, CSP headers in middleware |

## Rate Limiting
| Endpoint | Limit | Status |
|----------|-------|--------|
| Bet placement | 5/min per user | ✅ |
| Login | 10/min per IP | ✅ |
| Register | 5/hr per IP | ✅ |
| Deposit | 10/hr per user | ✅ |
| Withdraw | 5/hr per user | ✅ |
| General API | 100/min per IP | ✅ |
| Chatbot | 12/min per user | ✅ |

## Dependency Security
| Risk | Status | Notes |
|------|--------|-------|
| Known CVEs | ⚠️ Not scanned | No automated CVE scanning in CI |
| Supply chain | ⚠️ No lockfile audit | No `cargo audit` or `npm audit` in CI pipeline |
| Python deps | ⚠️ Not audited | No automated pip audit |

## Network Security
| Control | Status | Notes |
|---------|--------|-------|
| HTTPS | ✅ Configured | Dev certs via generate_dev_tls.ps1, TLS in main.rs |
| Security headers | ✅ Middleware | HSTS, CSP, X-Frame-Options, X-Content-Type-Options |
| CORS | ✅ Configured | Whitelist via ALLOWED_ORIGINS env var |
| CSRF | ✅ Implemented | Token-based CSRF protection in auth service |

## Responsible Gambling Controls
| Feature | Status | Notes |
|---------|--------|-------|
| Daily/weekly/monthly bet limits | ✅ Implemented | Per-user configurable limits |
| Daily/weekly/monthly loss limits | ✅ Implemented | Checked before bet placement |
| Session time limits | ✅ Implemented | Configurable duration |
| Self-exclusion | ✅ Implemented | Configurable exclusion period |
| Age verification (21+) | ✅ Implemented | Date-of-birth check on registration |
| Reality check reminders | ⚠️ Not implemented | No periodic session reminders |

## Fraud Detection
| Feature | Status | Notes |
|---------|--------|-------|
| Rapid betting detection | ✅ | Flags high-frequency placement |
| Unusually large bets | ✅ | Configurable threshold |
| Pattern analysis | ✅ | `betting_patterns` table with JSONB data |
| Fraud alerts dashboard | ✅ | Admin monitoring endpoint |

## Findings Summary
| Severity | Count | Items |
|----------|-------|-------|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | 2 | No CVE scanning, no npm/cargo audit in CI |
| LOW | 2 | Reality check reminders not implemented, minor frontend port mismatch |

## Remediation Plan
1. Add `cargo audit` to CI workflow (Medium)
2. Add `npm audit` and `pip audit` to CI (Medium)
3. Implement reality check modal after configurable session duration (Low)
4. Standardize .env port configuration (Low)
