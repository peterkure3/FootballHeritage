# Stage 04: Test

## Inputs
| Source | What to Load |
|--------|--------------|
| `03-build/output/changelog.md` | Features built and changes made |
| `03-build/output/build-artifacts.md` | Build outputs and configuration |
| `_config/conventions.md` | Testing standards and quality gates |
| `_config/tech-stack.md` | Testing framework preferences |

## Process
1. Run full test suite — unit, integration, and end-to-end tests across all four codebases
2. Validate prediction model accuracy against holdout data — compare actual vs predicted outcomes
3. Run security audit — dependency CVEs, API auth, SQL injection, XSS, rate limiting
4. Performance test — API latency under load, pipeline throughput, frontend Lighthouse scores
5. Validate responsible gambling features — deposit limits, self-exclusion, reality checks
6. Document all test results, known issues, and regression risks

## Outputs
| File | Description |
|------|-------------|
| `output/test-report.md` | Test results, coverage metrics, accuracy analysis |
| `output/security-audit.md` | Vulnerability findings, severity, remediation plan |
| `output/perf-report.md` | Load test results, latency percentiles, bottlenecks |
| `output/_blockers.md` | Test failures, security issues requiring fix, perf blockers |

## Gate
All critical and high-severity issues resolved. Test pass rate ≥ 90%. Prediction accuracy meets agreed thresholds. Security audit clean or with acceptable low-risk findings only.
