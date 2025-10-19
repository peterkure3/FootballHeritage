# Deployment Checklist - SimpleBettingService

## Pre-Deployment Checklist

### 1. Code Review
- [ ] Review all changes in `betting_simple.rs`
- [ ] Verify transaction handling logic
- [ ] Check error handling paths
- [ ] Confirm logging statements are appropriate
- [ ] Review security measures (encryption, validation)

### 2. Database Verification
- [ ] Confirm schema matches `schema.sql` exactly
- [ ] Verify all indexes are in place
- [ ] Check event status values are UPPERCASE
- [ ] Verify bet_type CHECK constraints are UPPERCASE
- [ ] Verify selection CHECK constraints are UPPERCASE
- [ ] Confirm transactions table has all required fields:
  - [ ] wallet_id
  - [ ] balance_before
  - [ ] balance_after
  - [ ] description
  - [ ] metadata
  - [ ] is_fraud_flagged
- [ ] Test database migrations on staging

### 3. Testing
- [ ] Run all unit tests: `cargo test betting_simple`
- [ ] Run integration tests: `cargo test --test integration`
- [ ] Test bet placement with all bet types (MONEYLINE, SPREAD, TOTAL)
- [ ] Test bet placement with all selections (HOME, AWAY, OVER, UNDER)
- [ ] Test concurrent bet placement (10+ simultaneous)
- [ ] Test insufficient funds scenario
- [ ] Test bet limit exceeded scenario
- [ ] Test odds changed scenario
- [ ] Test self-exclusion enforcement
- [ ] Test transaction rollback on failures
- [ ] Verify wallet balance accuracy after multiple bets
- [ ] Test fraud detection triggers correctly

### 4. Performance Testing
- [ ] Load test with 100 concurrent users
- [ ] Load test with 500 bets/second
- [ ] Monitor database connection pool usage
- [ ] Check query execution times
- [ ] Verify no memory leaks
- [ ] Test under sustained load (10+ minutes)

### 5. Security Audit
- [ ] Verify wallet encryption works correctly
- [ ] Test that users can only see their own bets
- [ ] Confirm transaction audit trail is complete
- [ ] Verify input validation on all fields
- [ ] Test SQL injection prevention
- [ ] Confirm rate limiting is active
- [ ] Test CSRF protection

### 6. Configuration
- [ ] Set correct `DATABASE_URL` in production
- [ ] Set secure `JWT_SECRET` (32+ characters)
- [ ] Set secure `ENCRYPTION_KEY` (32 bytes)
- [ ] Configure connection pool size appropriately
- [ ] Set rate limiting thresholds
- [ ] Configure TLS/HTTPS for production
- [ ] Set appropriate log levels (INFO for production)

### 7. Documentation
- [ ] Review `BETTING_SERVICE_GUIDE.md`
- [ ] Review `TRANSACTION_FIXES.md`
- [ ] Review `SIMPLIFIED_BETTING_README.md`
- [ ] Update API documentation if needed
- [ ] Document any environment-specific configurations

## Deployment Steps

### Stage 1: Staging Deployment
- [ ] Deploy to staging environment
- [ ] Run smoke tests on staging
- [ ] Verify all bet types work
- [ ] Place test bets and verify database records
- [ ] Check logs for errors or warnings
- [ ] Verify fraud detection logs appear
- [ ] Test with production-like data volume
- [ ] Monitor for 24 hours

### Stage 2: Production Preparation
- [ ] Schedule deployment during low-traffic window
- [ ] Notify team of deployment timeline
- [ ] Prepare rollback plan
- [ ] Backup production database
- [ ] Create database snapshot/checkpoint
- [ ] Prepare monitoring dashboards
- [ ] Set up alerting thresholds

### Stage 3: Canary Deployment (10%)
- [ ] Deploy to 10% of production traffic
- [ ] Monitor error rates (should be <0.1%)
- [ ] Monitor latency (should be <150ms)
- [ ] Check database transaction success rate (should be >99.9%)
- [ ] Verify no user complaints
- [ ] Monitor for 2-4 hours

### Stage 4: Gradual Rollout
- [ ] Increase to 25% of traffic
- [ ] Monitor for 1 hour
- [ ] Increase to 50% of traffic
- [ ] Monitor for 1 hour
- [ ] Increase to 75% of traffic
- [ ] Monitor for 1 hour
- [ ] Deploy to 100% of traffic

### Stage 5: Post-Deployment
- [ ] Monitor error rates for 24 hours
- [ ] Review betting transaction logs
- [ ] Verify wallet balances are accurate
- [ ] Check fraud detection alerts
- [ ] Review database performance
- [ ] Collect user feedback
- [ ] Document any issues encountered

## Monitoring Metrics

### Critical Metrics (Check every 5 minutes)
- [ ] Error rate < 0.1%
- [ ] Average bet placement time < 150ms
- [ ] Database transaction success rate > 99.9%
- [ ] Database connection pool usage < 80%

### Important Metrics (Check hourly)
- [ ] Total bets placed
- [ ] Average bet amount
- [ ] Fraud detection alerts
- [ ] Self-exclusion violations (should be 0)
- [ ] Odds change rejections

### Health Checks
- [ ] `/health` endpoint responding
- [ ] Database connectivity
- [ ] Encryption service operational
- [ ] Rate limiting functional

## Rollback Procedure

### If Critical Issues Detected
1. [ ] Stop deployment immediately
2. [ ] Revert to previous version:
   ```rust
   // Change import back to original
   use crate::betting::BettingService;
   ```
3. [ ] Deploy rollback to all servers
4. [ ] Verify original service working
5. [ ] Investigate root cause
6. [ ] Document issue and resolution
7. [ ] Fix and retest before retry

### Rollback Triggers
- Error rate > 1%
- Average response time > 500ms
- Database transaction failure rate > 1%
- Any data corruption detected
- Critical security issue discovered

## Validation Tests (Post-Deployment)

### Functional Tests
- [ ] Place MONEYLINE bet - should succeed
- [ ] Place SPREAD bet - should succeed
- [ ] Place TOTAL bet - should succeed
- [ ] Place bet with insufficient funds - should fail gracefully
- [ ] Place bet on non-UPCOMING event - should fail
- [ ] Place bet exceeding daily limit - should fail
- [ ] Fetch bet history - should return correct data
- [ ] Fetch event list - should return all events

### Data Integrity Tests
- [ ] Check wallet balances match transaction history
- [ ] Verify bet amounts sum correctly
- [ ] Confirm transaction audit trail is complete
- [ ] Validate encrypted balances can be decrypted
- [ ] Ensure no orphaned records

### Performance Tests
- [ ] Place 100 bets sequentially - should complete in < 15 seconds
- [ ] Place 10 concurrent bets - should all succeed or fail gracefully
- [ ] Fetch 1000 bets with pagination - should be fast

## Known Issues and Mitigations

### Issue: Windows Build (aws-lc-sys)
**Status:** Known build issue on Windows
**Mitigation:** Build on Linux/macOS or use alternative TLS stack
**Impact:** Build-time only, not runtime

### Issue: Odds Rapid Changes
**Status:** 5% tolerance may need adjustment
**Mitigation:** Monitor odds change rejection rate
**Impact:** User experience (may need to refresh)

### Issue: Concurrent Self-Exclusion
**Status:** Rare edge case
**Mitigation:** Transaction handles this correctly
**Impact:** None (working as intended)

## Success Criteria

### Must Have (Required for Go-Live)
- ✅ Zero data corruption
- ✅ Error rate < 0.1%
- ✅ All transactions atomic
- ✅ Wallet encryption working
- ✅ Audit trail complete

### Should Have (Important but not blocking)
- ✅ Response time < 150ms
- ✅ Fraud detection active
- ✅ Comprehensive logging
- ✅ Monitoring dashboards

### Nice to Have (Future improvements)
- ⏳ Sub-100ms response time
- ⏳ ML-based fraud detection
- ⏳ Real-time odds updates
- ⏳ Parlay bet support

## Team Contacts

### On-Call During Deployment
- **Backend Lead:** [Name] - [Contact]
- **Database Admin:** [Name] - [Contact]
- **DevOps:** [Name] - [Contact]
- **Security:** [Name] - [Contact]

### Escalation Path
1. Backend Lead
2. Engineering Manager
3. CTO

## Communication Plan

### Pre-Deployment
- [ ] Send deployment notice 24 hours before
- [ ] Brief team on changes and rollback plan
- [ ] Confirm all stakeholders are available

### During Deployment
- [ ] Post status updates every 30 minutes
- [ ] Alert team of any issues immediately
- [ ] Log all decisions and actions

### Post-Deployment
- [ ] Send completion notice with metrics
- [ ] Schedule retrospective meeting
- [ ] Document lessons learned

## Emergency Procedures

### If Database Corruption Detected
1. **IMMEDIATELY** stop all betting operations
2. Restore from latest backup
3. Investigate root cause
4. Fix and retest thoroughly

### If Security Breach Detected
1. **IMMEDIATELY** disable betting service
2. Rotate all keys and secrets
3. Audit all transactions
4. Notify security team and management

### If Major Bug Found
1. Assess severity and impact
2. If critical: rollback immediately
3. If minor: log and fix in next release
4. Document and create ticket

## Final Sign-Off

### Before Production Deployment
- [ ] Backend Lead approval
- [ ] Database Admin approval
- [ ] Security team approval
- [ ] Product Owner approval

### Deployment Authorization
**Date:** _______________
**Time:** _______________
**Authorized by:** _______________
**Signature:** _______________

---

## Notes

- Keep this checklist updated with any new items discovered
- Document any deviations from the checklist
- Review and update after each deployment
- Share learnings with the team

**Remember:** Safety first. If in doubt, don't deploy. Better to delay than to cause downtime.

---

**Last Updated:** [Date]
**Version:** 1.0
**Owner:** Backend Team