# Source schema inventory

Static declarations, not a live catalog. Repeated table declarations and
later ALTER statements must be interpreted in migration order.

## Versioned SQL

### `backend/migrations/20241019000001_initial_schema.sql`

```sql
CREATE TABLE users (
CREATE TABLE wallets (
CREATE TABLE transactions (
CREATE TABLE events (
CREATE TABLE bets (
CREATE TABLE gambling_limits (
CREATE TABLE user_activity (
CREATE TABLE betting_patterns (
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_wallets_user_id ON wallets(user_id);
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_events_sport ON events(sport);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_bets_user_id ON bets(user_id);
CREATE INDEX idx_bets_event_id ON bets(event_id);
CREATE INDEX idx_bets_status ON bets(status);
CREATE INDEX idx_bets_created_at ON bets(created_at);
CREATE INDEX idx_gambling_limits_user_id ON gambling_limits(user_id);
CREATE INDEX idx_user_activity_user_id ON user_activity(user_id);
CREATE INDEX idx_user_activity_timestamp ON user_activity(timestamp);
CREATE INDEX idx_user_activity_ip ON user_activity(ip_address);
```

### `backend/migrations/20251023150910_real_sports_data.sql`

```sql
```

### `backend/migrations/20251024000001_add_admin_system.sql`

```sql
ALTER TABLE users
CHECK (role IN ('user', 'admin', 'superadmin'));
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE TABLE IF NOT EXISTS admin_logs (
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action ON admin_logs(action);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target ON admin_logs(target_type, target_id);
CREATE TABLE IF NOT EXISTS platform_metrics (
CREATE INDEX IF NOT EXISTS idx_platform_metrics_date ON platform_metrics(date DESC);
CREATE TABLE IF NOT EXISTS fraud_alerts (
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_user_id ON fraud_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON fraud_alerts(status);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_severity ON fraud_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_created_at ON fraud_alerts(created_at DESC);
ALTER TABLE events
```

### `backend/migrations/20251025000001_add_external_tracking.sql`

```sql
ALTER TABLE events
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_external
ALTER TABLE bets
CREATE TABLE IF NOT EXISTS admin_logs (
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target ON admin_logs(target_type, target_id);
```

### `backend/migrations/20251027000001_add_parlay_calculator.sql`

```sql
CREATE TABLE IF NOT EXISTS parlays (
CREATE TABLE IF NOT EXISTS parlay_legs (
CREATE TABLE IF NOT EXISTS parlay_calculations (
CREATE INDEX IF NOT EXISTS idx_parlays_user_id ON parlays(user_id);
CREATE INDEX IF NOT EXISTS idx_parlays_status ON parlays(status);
CREATE INDEX IF NOT EXISTS idx_parlays_created_at ON parlays(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_parlay_legs_parlay_id ON parlay_legs(parlay_id);
CREATE INDEX IF NOT EXISTS idx_parlay_legs_event_id ON parlay_legs(event_id);
CREATE INDEX IF NOT EXISTS idx_parlay_calculations_user_id ON parlay_calculations(user_id);
CREATE INDEX IF NOT EXISTS idx_parlay_calculations_created_at ON parlay_calculations(created_at DESC);
```

### `backend/migrations/20251101000001_add_event_date_index.sql`

```sql
CREATE INDEX IF NOT EXISTS idx_events_event_date
CREATE INDEX IF NOT EXISTS idx_events_status_event_date
CREATE INDEX IF NOT EXISTS idx_events_sport_event_date
```

### `backend/migrations/20251104000001_add_nba_cup_support.sql`

```sql
ALTER TABLE events
CREATE INDEX IF NOT EXISTS idx_events_sport_league
CREATE INDEX IF NOT EXISTS idx_events_league_date
ALTER TABLE events
CHECK (league IN (
ALTER TABLE events DROP CONSTRAINT IF EXISTS events_league_check;
```

### `backend/migrations/20260124000001_add_betting_intelligence.sql`

```sql
CREATE TABLE IF NOT EXISTS devigged_odds (
CREATE INDEX IF NOT EXISTS idx_devigged_odds_event_id ON devigged_odds(event_id);
CREATE INDEX IF NOT EXISTS idx_devigged_odds_pipeline_match_id ON devigged_odds(pipeline_match_id);
CREATE INDEX IF NOT EXISTS idx_devigged_odds_book_market ON devigged_odds(bookmaker, market);
CREATE INDEX IF NOT EXISTS idx_devigged_odds_created_at ON devigged_odds(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_devigged_odds_snapshot
CREATE TABLE IF NOT EXISTS ev_bets (
CREATE INDEX IF NOT EXISTS idx_ev_bets_event_id ON ev_bets(event_id);
CREATE INDEX IF NOT EXISTS idx_ev_bets_pipeline_match_id ON ev_bets(pipeline_match_id);
CREATE INDEX IF NOT EXISTS idx_ev_bets_market ON ev_bets(market);
CREATE INDEX IF NOT EXISTS idx_ev_bets_ev_pct ON ev_bets(expected_value_pct DESC);
CREATE INDEX IF NOT EXISTS idx_ev_bets_created_at ON ev_bets(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ev_bets_snapshot
CREATE TABLE IF NOT EXISTS arbitrage (
CREATE INDEX IF NOT EXISTS idx_arbitrage_event_id ON arbitrage(event_id);
CREATE INDEX IF NOT EXISTS idx_arbitrage_pipeline_match_id ON arbitrage(pipeline_match_id);
CREATE INDEX IF NOT EXISTS idx_arbitrage_market ON arbitrage(market);
CREATE INDEX IF NOT EXISTS idx_arbitrage_edge ON arbitrage(arb_percentage DESC);
CREATE INDEX IF NOT EXISTS idx_arbitrage_created_at ON arbitrage(created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_arbitrage_snapshot
```

### `backend/migrations/20260127000001_intelligence_odds_decimal.sql`

```sql
ALTER TABLE devigged_odds
ALTER TABLE devigged_odds
ALTER TABLE ev_bets
ALTER TABLE devigged_odds
ALTER TABLE ev_bets
CREATE UNIQUE INDEX IF NOT EXISTS uq_devigged_odds_snapshot
CREATE UNIQUE INDEX IF NOT EXISTS uq_ev_bets_snapshot
```

### `backend/migrations/20260127000002_add_sportsbook_registry_and_offers.sql`

```sql
CREATE TABLE IF NOT EXISTS sportsbook_registry (
CREATE INDEX IF NOT EXISTS idx_sportsbook_registry_enabled_region
CREATE INDEX IF NOT EXISTS idx_sportsbook_registry_provider
CREATE INDEX IF NOT EXISTS idx_sportsbook_registry_priority
CREATE TABLE IF NOT EXISTS provider_events (
CREATE UNIQUE INDEX IF NOT EXISTS uq_provider_events
CREATE INDEX IF NOT EXISTS idx_provider_events_event_id
CREATE INDEX IF NOT EXISTS idx_provider_events_commence_time
CREATE TABLE IF NOT EXISTS odds_offers (
CREATE INDEX IF NOT EXISTS idx_odds_offers_provider_event
CREATE INDEX IF NOT EXISTS idx_odds_offers_event_id
CREATE INDEX IF NOT EXISTS idx_odds_offers_book_market
CREATE INDEX IF NOT EXISTS idx_odds_offers_created_at
CREATE UNIQUE INDEX IF NOT EXISTS uq_odds_offers_snapshot
```

### `backend/migrations/20260209000001_add_devigged_odds_archive.sql`

```sql
CREATE TABLE IF NOT EXISTS devigged_odds_archive (
CREATE INDEX IF NOT EXISTS idx_devigged_archive_event_id ON devigged_odds_archive(event_id);
CREATE INDEX IF NOT EXISTS idx_devigged_archive_pipeline_match_id ON devigged_odds_archive(pipeline_match_id);
CREATE INDEX IF NOT EXISTS idx_devigged_archive_bookmaker ON devigged_odds_archive(bookmaker);
CREATE INDEX IF NOT EXISTS idx_devigged_archive_archived_at ON devigged_odds_archive(archived_at DESC);
CREATE INDEX IF NOT EXISTS idx_devigged_archive_source_updated ON devigged_odds_archive(source_updated_at);
```

### `backend/migrations/20260210000001_add_player_props.sql`

```sql
CREATE TABLE IF NOT EXISTS player_props (
CREATE INDEX idx_player_props_event ON player_props(event_id);
CREATE INDEX idx_player_props_market ON player_props(sport, market);
CREATE INDEX idx_player_props_player ON player_props(player_name);
CREATE INDEX idx_player_props_active ON player_props(event_id, is_active) WHERE is_active = true;
```

### `backend/migrations/20260210000002_add_enhanced_parlays.sql`

```sql
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS parlay_type VARCHAR(20) DEFAULT 'STANDARD'
CHECK (parlay_type IN ('STANDARD', 'SYSTEM_2_3', 'SYSTEM_3_4', 'SYSTEM_2_4', 'SYSTEM_3_5', 'TEASER', 'PLEASER'));
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS system_min_legs INTEGER
CHECK (system_min_legs IS NULL OR system_min_legs > 0);
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS total_combinations INTEGER;
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS combined_edge DECIMAL(10,4);
ALTER TABLE parlays ADD COLUMN IF NOT EXISTS correlation_score DECIMAL(5,4) DEFAULT 0;
CREATE TABLE IF NOT EXISTS parlay_correlation_warnings (
CREATE INDEX IF NOT EXISTS idx_parlay_correlation_parlay ON parlay_correlation_warnings(parlay_id);
CREATE TABLE IF NOT EXISTS parlay_system_results (
CREATE INDEX IF NOT EXISTS idx_parlay_system_parlay ON parlay_system_results(parlay_id);
```

### `backend/migrations/20260706000001_add_transaction_status.sql`

```sql
ALTER TABLE transactions
CHECK (status IN ('pending', 'completed', 'failed', 'cancelled'));
ALTER TABLE transactions ALTER COLUMN status SET NOT NULL;
```

### `backend/migrations/20261007000001_add_ai_picks.sql`

```sql
CREATE TABLE IF NOT EXISTS ai_pick_runs (
CREATE INDEX IF NOT EXISTS idx_ai_pick_runs_user_created ON ai_pick_runs(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS ai_conversations (
CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_updated ON ai_conversations(user_id, updated_at DESC);
CREATE TABLE IF NOT EXISTS ai_messages (
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation_created ON ai_messages(conversation_id, created_at ASC);
```

### `backend/migrations/20261008000001_add_rust_rag_chat.sql`

```sql
ALTER TABLE ai_messages ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE ai_messages ADD COLUMN sequence BIGSERIAL NOT NULL;
CREATE INDEX idx_ai_messages_sequence ON ai_messages(conversation_id, sequence);
CREATE TABLE ai_chat_requests (
CREATE TABLE ai_rag_documents (
CREATE INDEX idx_ai_rag_documents_search ON ai_rag_documents USING GIN(search_vector);
```

### `backend/migrations/20261022000001_feature_management.sql`

```sql
CREATE TABLE feature_flags (
CREATE TABLE user_feature_overrides (
CREATE TABLE role_feature_rules (
CREATE TABLE feature_audit_logs (
CREATE INDEX feature_audit_logs_created ON feature_audit_logs(created_at DESC, id DESC);
```

### `backend/migrations/20261023000001_unique_wallet_owner.sql`

```sql
CREATE UNIQUE INDEX wallets_unique_user_id ON wallets(user_id);
```

### `backend/migrations/20261026000001_published_data.sql`

```sql
CREATE TABLE published.sources (
CREATE TABLE published.records (
CREATE TABLE published.receipts (
CREATE INDEX published_receipts_stream ON published.receipts(stream_id,committed_at);
```

### `backend/migrations/20261026000002_persistent_auth_sessions.sql`

```sql
CREATE TABLE auth_sessions (
CHECK (expires_at >= created_at)
CREATE INDEX auth_sessions_active_user ON auth_sessions(user_id,expires_at)
```

### `pipeline/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS matches (
CREATE TABLE IF NOT EXISTS odds (
CREATE TABLE IF NOT EXISTS predictions (
CREATE TABLE IF NOT EXISTS prediction_history (
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_home_team ON matches(home_team);
CREATE INDEX IF NOT EXISTS idx_matches_away_team ON matches(away_team);
CREATE INDEX IF NOT EXISTS idx_odds_match_id ON odds(match_id);
CREATE INDEX IF NOT EXISTS idx_odds_bookmaker ON odds(bookmaker);
CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at);
CREATE INDEX IF NOT EXISTS idx_prediction_history_match_id ON prediction_history(match_id);
CREATE INDEX IF NOT EXISTS idx_prediction_history_locked_at ON prediction_history(locked_at);
```

### `pipeline/migrations/001_add_prediction_history.sql`

```sql
CREATE TABLE IF NOT EXISTS prediction_history (
CREATE INDEX IF NOT EXISTS idx_prediction_history_match_id ON prediction_history(match_id);
CREATE INDEX IF NOT EXISTS idx_prediction_history_locked_at ON prediction_history(locked_at);
```

### `pipeline/migrations/002_publication_outbox.sql`

```sql
CREATE TABLE fh_sync.identity (
CREATE TABLE fh_sync.records (
CREATE TABLE fh_sync.outbox (
CREATE INDEX fh_sync_pending ON fh_sync.outbox(available_at, id)
CREATE TABLE fh_sync.status (
```

### `pipeline/migrations/003_football_publication_capture.sql`

```sql
CREATE TABLE fh_sync.dirty_fixtures (
```

## Python-managed schema declarations

```text
pipeline/etl/backtesting.py:474 backtest_results
pipeline/etl/elo_model.py:322 conn.execute
pipeline/etl/elo_model.py:324 team_elo_ratings
pipeline/etl/load_to_db.py:135 matches
pipeline/etl/load_to_db.py:176 odds
pipeline/etl/load_to_db.py:188 predictions
pipeline/etl/load_to_db.py:200 nba_games
pipeline/etl/load_to_db.py:504 nba_games
pipeline/load_to_heritage_db.py:70 matches
pipeline/load_to_heritage_db.py:99 odds
pipeline/load_to_heritage_db.py:113 predictions
pipeline/tests/test_backend_sync.py:50 matches
pipeline/tests/test_backend_sync.py:54 odds
pipeline/tests/test_backend_sync.py:57 nba_games
pipeline/tests/test_nullable_fixture_load.py:23 matches
pipeline/tests/test_publication_sync.py:151 public.matches
pipeline/tests/test_publication_sync.py:155 public.predictions
pipeline/tests/test_publication_sync.py:158 public.odds
```
