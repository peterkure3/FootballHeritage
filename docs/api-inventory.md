# API and source inventory

Generated from the working tree by `py -3 scripts/architecture_inventory.py`.
This is static registration evidence, not proof of reachable deployed routes.
Rust paths below are registration fragments: compose scopes from `main.rs`
and the domain configure functions. Commented-out routes are excluded.

## Rust registration sites

| File:line | Registration |
|---|---|
| `backend/src/feature_tests.rs:87` | `SCOPE / see source /api/v1/admin ` |
| `backend/src/feature_tests.rs:92` | `GET /whoami |req: HttpRequest| async move {
                            HttpResponse::Ok(` |
| `backend/src/feature_tests.rs:102` | `GET /api/v1/me/features effective` |
| `backend/src/feature_tests.rs:103` | `POST /api/v1/wallet/deposit || async { HttpResponse::Ok(` |
| `backend/src/feature_tests.rs:107` | `POST /api/v1/ai-picks/chat || async { HttpResponse::Ok(` |
| `backend/src/feature_tests.rs:111` | `POST /api/v1/auth/logout crate::handlers::auth::logout` |
| `backend/src/feature_tests.rs:394` | `POST /logout crate::handlers::auth::logout` |
| `backend/src/features.rs:497` | `GET /features list` |
| `backend/src/features.rs:498` | `GET /features/audit audit` |
| `backend/src/features.rs:499` | `PATCH /features/{key} patch_flag` |
| `backend/src/features.rs:500` | `PATCH /features/{key}/roles/{role} patch_role` |
| `backend/src/features.rs:501` | `GET /users/{id}/features user_features` |
| `backend/src/features.rs:502` | `PATCH /users/{id}/features/{key} patch_user` |
| `backend/src/financial_tests.rs:63` | `SCOPE / see source /api/v1/wallet ` |
| `backend/src/financial_tests.rs:65` | `GET /balance wallet::get_balance` |
| `backend/src/financial_tests.rs:66` | `POST /deposit wallet::deposit` |
| `backend/src/financial_tests.rs:67` | `POST /withdraw wallet::withdraw` |
| `backend/src/handlers/ai_picks.rs:541` | `SCOPE / see source /ai-picks ` |
| `backend/src/handlers/ai_picks.rs:543` | `POST /generate generate` |
| `backend/src/handlers/ai_picks.rs:544` | `POST /chat chat` |
| `backend/src/handlers/ai_picks.rs:545` | `GET /conversations conversations` |
| `backend/src/handlers/ai_picks.rs:546` | `GET /conversations/{id} conversation` |
| `backend/src/handlers/ai_picks.rs:547` | `GET  list` |
| `backend/src/handlers/ai_picks.rs:548` | `GET /{id} get` |
| `backend/src/main.rs:236` | `SCOPE / see source /api/v1 ` |
| `backend/src/main.rs:237` | `GET /predictions/{match_id} published::prediction` |
| `backend/src/main.rs:241` | `GET /me/features features::effective` |
| `backend/src/main.rs:242` | `ROUTE /pipeline/{tail:.*} pipeline_gateway::proxy` |
| `backend/src/main.rs:247` | `SCOPE / see source /auth ` |
| `backend/src/main.rs:248` | `POST /register handlers::auth::register` |
| `backend/src/main.rs:249` | `POST /login handlers::auth::login` |
| `backend/src/main.rs:250` | `POST /logout handlers::auth::logout` |
| `backend/src/main.rs:251` | `POST /refresh handlers::auth::refresh` |
| `backend/src/main.rs:252` | `POST /verify-email handlers::auth::verify_email` |
| `backend/src/main.rs:261` | `SCOPE / see source /intelligence ` |
| `backend/src/main.rs:262` | `GET /devigged-odds handlers::intelligence::get_devigged_odds` |
| `backend/src/main.rs:266` | `GET /ev-bets handlers::intelligence::get_ev_bets` |
| `backend/src/main.rs:270` | `GET /arbitrage handlers::intelligence::get_arbitrage` |
| `backend/src/main.rs:274` | `POST /refresh handlers::intelligence::refresh_intelligence` |
| `backend/src/main.rs:280` | `SCOPE / see source /wallet ` |
| `backend/src/main.rs:284` | `GET /balance handlers::wallet::get_balance` |
| `backend/src/main.rs:285` | `POST /deposit handlers::wallet::deposit` |
| `backend/src/main.rs:286` | `POST /withdraw handlers::wallet::withdraw` |
| `backend/src/main.rs:287` | `GET /transactions handlers::wallet::get_transactions` |
| `backend/src/main.rs:293` | `SCOPE / see source /betting ` |
| `backend/src/main.rs:294` | `GET /events handlers::betting::get_events` |
| `backend/src/main.rs:295` | `GET /events/{id} handlers::betting::get_event` |
| `backend/src/main.rs:297` | `SCOPE / see source  ` |
| `backend/src/main.rs:301` | `POST /bets handlers::betting::place_bet` |
| `backend/src/main.rs:302` | `GET /bets handlers::betting::get_user_bets` |
| `backend/src/main.rs:303` | `GET /bets/{id} handlers::betting::get_bet` |
| `backend/src/main.rs:307` | `SCOPE / see source /limits ` |
| `backend/src/main.rs:311` | `GET / handlers::limits::get_limits` |
| `backend/src/main.rs:312` | `PUT / handlers::limits::update_limits` |
| `backend/src/main.rs:313` | `POST /self-exclude handlers::limits::self_exclude` |
| `backend/src/main.rs:319` | `SCOPE / see source /user ` |
| `backend/src/main.rs:323` | `GET /profile handlers::user::get_profile` |
| `backend/src/main.rs:324` | `PUT /profile handlers::user::update_profile` |
| `backend/src/main.rs:325` | `GET /activity handlers::user::get_activity` |
| `backend/src/main.rs:326` | `PUT /password handlers::user::change_password` |
| `backend/src/main.rs:329` | `SCOPE / see source /chat ` |
| `backend/src/main.rs:330` | `POST  handlers::chat::chat` |
| `backend/src/main.rs:331` | `GET /health handlers::chat::chat_health` |
| `backend/src/main.rs:334` | `SCOPE / see source /sports ` |
| `backend/src/main.rs:335` | `GET  handlers::sports::get_sports` |
| `backend/src/main.rs:336` | `GET /categories handlers::sports::get_bet_categories` |
| `backend/src/main.rs:340` | `GET /{sport}/leagues handlers::sports::get_sport_leagues` |
| `backend/src/main.rs:346` | `SCOPE / see source /player-props ` |
| `backend/src/main.rs:347` | `GET  handlers::player_props::get_player_props` |
| `backend/src/main.rs:348` | `GET /event/{id} handlers::player_props::get_player_props_by_event` |
| `backend/src/main.rs:354` | `SCOPE / see source /parlay ` |
| `backend/src/main.rs:355` | `POST /calculate handlers::parlay::calculate_parlay` |
| `backend/src/main.rs:359` | `POST /save handlers::parlay::save_parlay` |
| `backend/src/main.rs:360` | `GET /saved handlers::parlay::get_saved_parlays` |
| `backend/src/main.rs:361` | `GET /history handlers::parlay::get_calculation_history` |
| `backend/src/main.rs:365` | `GET /{id} handlers::parlay::get_parlay` |
| `backend/src/main.rs:366` | `DELETE /{id} handlers::parlay::delete_parlay` |
| `backend/src/main.rs:369` | `SCOPE / see source /admin ` |
| `backend/src/main.rs:375` | `GET /users handlers::admin::users::list_users` |
| `backend/src/main.rs:376` | `GET /users/{id} handlers::admin::users::get_user_details` |
| `backend/src/main.rs:380` | `PUT /users/{id}/status handlers::admin::users::update_user_status` |
| `backend/src/main.rs:384` | `PUT /users/{id}/verify handlers::admin::users::verify_user` |
| `backend/src/main.rs:389` | `GET /events handlers::admin::events::get_all_events` |
| `backend/src/main.rs:393` | `POST /events handlers::admin::events::create_event` |
| `backend/src/main.rs:397` | `GET /events/{id} handlers::admin::events::get_event` |
| `backend/src/main.rs:401` | `PUT /events/{id} handlers::admin::events::update_event` |
| `backend/src/main.rs:405` | `DELETE /events/{id} handlers::admin::events::delete_event` |
| `backend/src/main.rs:409` | `PUT /events/{id}/status handlers::admin::events::update_event_status` |
| `backend/src/main.rs:420` | `GET /analytics/dashboard handlers::admin::analytics::get_dashboard_metrics` |
| `backend/src/main.rs:425` | `GET /monitoring/fraud-alerts handlers::admin::monitoring::get_fraud_alerts` |
| `backend/src/main.rs:429` | `GET /monitoring/audit-logs handlers::admin::monitoring::get_audit_logs` |
| `backend/src/main.rs:435` | `GET /health handlers::health::health_check` |
| `backend/src/main.rs:436` | `GET /ready handlers::health::readiness` |
| `backend/src/main.rs:437` | `GET /metrics handlers::monitoring::metrics` |
| `backend/src/session_tests.rs:46` | `SCOPE / see source /protected ` |
| `backend/src/session_tests.rs:48` | `GET  || async { HttpResponse::Ok(` |
| `backend/src/session_tests.rs:50` | `POST /logout crate::handlers::auth::logout` |
| `backend/src/session_tests.rs:193` | `SCOPE / see source /admin ` |
| `backend/src/session_tests.rs:197` | `GET  || async { HttpResponse::Ok(` |
| `backend/src/session_tests.rs:200` | `SCOPE / see source /super ` |
| `backend/src/session_tests.rs:204` | `GET  || async { HttpResponse::Ok(` |

## Python route declarations

All domain routes receive `/api/v1` in `api/main.py`; browser access
currently uses the Rust `/api/v1/pipeline` prefix.

| Method | Path | Handler | Source | Classification |
|---|---|---|---|---|
| GET | `/ai-picks` | `generate_ai_picks` | `pipeline/api/routers/ai_picks.py:17` | published read / Rust migration |
| POST | `/smart-assistant` | `smart_assistant` | `pipeline/api/routers/assistant.py:183` | request computation; port supported rules or use published outputs |
| GET | `/betting-intel` | `overview` | `pipeline/api/routers/betting_intel.py:32` | published read / Rust migration |
| GET | `/betting-intel/{sport}` | `sport_intelligence` | `pipeline/api/routers/betting_intel.py:44` | published read / Rust migration |
| GET | `/matches` | `get_matches` | `pipeline/api/routers/core.py:45` | published read / Rust migration |
| GET | `/health` | `health_check` | `pipeline/api/routers/core.py:128` | published read / Rust migration |
| POST | `/fpl/team/evaluate` | `evaluate_fpl_team` | `pipeline/api/routers/fpl.py:64` | request computation; port supported rules or use published outputs |
| GET | `/fpl/advice` | `get_fpl_advice` | `pipeline/api/routers/fpl.py:95` | published read / Rust migration |
| GET | `/fpl/players` | `get_fpl_players` | `pipeline/api/routers/fpl.py:128` | published read / Rust migration |
| GET | `/fpl/fixtures` | `get_fpl_fixtures` | `pipeline/api/routers/fpl.py:191` | published read / Rust migration |
| POST | `/fpl/refresh` | `refresh_fpl_data` | `pipeline/api/routers/fpl.py:239` | local operational tooling; preserve internally |
| POST | `/intelligence/devig` | `devig_endpoint` | `pipeline/api/routers/intelligence.py:112` | request computation; port supported rules or use published outputs |
| POST | `/intelligence/ev` | `ev_endpoint` | `pipeline/api/routers/intelligence.py:179` | request computation; port supported rules or use published outputs |
| POST | `/intelligence/ev/batch` | `ev_batch_endpoint` | `pipeline/api/routers/intelligence.py:242` | request computation; port supported rules or use published outputs |
| POST | `/intelligence/arbitrage/scan` | `arbitrage_scan` | `pipeline/api/routers/intelligence.py:311` | request computation; port supported rules or use published outputs |
| GET | `/best-value-bets` | `get_best_value_bets` | `pipeline/api/routers/intelligence.py:405` | published read / Rust migration |
| GET | `/predict-matchup` | `predict_matchup` | `pipeline/api/routers/matchup.py:29` | request computation; port supported rules or use published outputs |
| GET | `/ncaab/bracket` | `get_march_madness_bracket` | `pipeline/api/routers/ncaab.py:21` | published read / Rust migration |
| GET | `/ncaab/predictions` | `get_ncaab_predictions` | `pipeline/api/routers/ncaab.py:39` | published read / Rust migration |
| GET | `/ncaab/odds` | `get_ncaab_odds` | `pipeline/api/routers/ncaab.py:72` | published read / Rust migration |
| GET | `/ncaab/games` | `get_ncaab_games` | `pipeline/api/routers/ncaab.py:147` | published read / Rust migration |
| POST | `/ncaab/refresh` | `refresh_ncaab_data` | `pipeline/api/routers/ncaab.py:323` | local operational tooling; preserve internally |
| POST | `/parlay/enrich` | `enrich_parlay_legs` | `pipeline/api/routers/parlay.py:73` | request computation; port supported rules or use published outputs |
| GET | `/suggested-parlays` | `get_suggested_parlays` | `pipeline/api/routers/parlay.py:272` | published read / Rust migration |
| GET | `/prediction-dashboard/operations` | `operations_overview` | `pipeline/api/routers/prediction_dashboard.py:13` | published read / Rust migration |
| GET | `/prediction-dashboard/paper-trials` | `paper_trials` | `pipeline/api/routers/prediction_dashboard.py:22` | published read / Rust migration |
| GET | `/prediction-dashboard/fixtures` | `fixture_feed` | `pipeline/api/routers/prediction_dashboard.py:31` | published read / Rust migration |
| GET | `/predictions/history-data` | `get_prediction_history` | `pipeline/api/routers/predictions.py:123` | published read / Rust migration |
| POST | `/predictions/update-results` | `update_prediction_results` | `pipeline/api/routers/predictions.py:140` | local operational tooling; preserve internally |
| GET | `/predictions/accuracy-data` | `get_prediction_accuracy` | `pipeline/api/routers/predictions.py:163` | published read / Rust migration |
| GET | `/predictions/versions` | `get_prediction_versions` | `pipeline/api/routers/predictions.py:193` | published read / Rust migration |
| GET | `/predictions/validate-data` | `validate_prediction_data` | `pipeline/api/routers/predictions.py:319` | local operational tooling; preserve internally |
| GET | `/predictions/elo-ratings` | `get_elo_ratings` | `pipeline/api/routers/predictions.py:350` | published read / Rust migration |
| POST | `/predictions/update-elo` | `update_elo_ratings` | `pipeline/api/routers/predictions.py:374` | local operational tooling; preserve internally |
| GET | `/predictions/upcoming` | `get_upcoming_predictions` | `pipeline/api/routers/predictions.py:395` | published read / Rust migration |
| GET | `/predictions/backtest` | `get_backtest_results` | `pipeline/api/routers/predictions.py:413` | local operational tooling; preserve internally |
| GET | `/predictions/value-bets` | `get_enhanced_value_bets` | `pipeline/api/routers/predictions.py:431` | published read / Rust migration |
| POST | `/predictions/run-pipeline` | `run_enhanced_pipeline` | `pipeline/api/routers/predictions.py:460` | local operational tooling; preserve internally |
| GET | `/predictions/{match_id}` | `get_prediction` | `pipeline/api/routers/predictions.py:478` | published read / Rust migration |
| GET | `/sport-models` | `sport_models` | `pipeline/api/routers/sport_models.py:27` | published read / Rust migration |
| POST | `/sport-models/preview` | `sport_model_preview` | `pipeline/api/routers/sport_models.py:32` | request computation; port supported rules or use published outputs |
| GET | `/sport-models/teams` | `sport_model_teams` | `pipeline/api/routers/sport_models.py:43` | published read / Rust migration |

## Rust module / handler / middleware inventory

| Source | Public functions and services |
|---|---|
| `backend/src/auth.rs` | `AuthService`, `SessionInfo`, `new`, `with_database`, `create_persistent_session`, `validate_request_token`, `create_session_in_transaction`, `revoke_request_session`, `generate_token`, `validate_token`, `extract_token_from_header`, `create_session`, `get_session`, `update_session_activity`, `invalidate_session`, `cleanup_expired_sessions`, `has_active_sessions`, `invalidate_user_sessions`, `get_user_session_count`, `detect_suspicious_login`, `generate_refresh_token`, `validate_refresh_token`, `is_user_verified`, `is_account_locked`, `has_exceeded_max_attempts`, `calculate_lock_duration`, `generate_password_reset_token`, `validate_password_reset_token`, `generate_email_verification_token`, `validate_email_verification_token`, `JwtMiddleware`, `new`, `authenticate` |
| `backend/src/betting_simple.rs` | `SimpleBettingService`, `new`, `place_bet`, `get_user_bets`, `get_bet_by_id`, `get_events`, `get_event` |
| `backend/src/bin/init_admin.rs` |  |
| `backend/src/bin/init_wallets.rs` |  |
| `backend/src/bin/migrate.rs` |  |
| `backend/src/bin/reset_wallets.rs` |  |
| `backend/src/config.rs` | `AppConfig`, `from_env`, `is_development`, `validate_jwt_secret`, `validate_encryption_key` |
| `backend/src/crypto.rs` | `CryptoService`, `new`, `from_key`, `from_string`, `hash_password`, `verify_password`, `encrypt_balance`, `decrypt_balance`, `generate_csrf_token`, `verify_csrf_token`, `generate_session_token`, `create_hmac`, `verify_hmac`, `generate_random_bytes`, `derive_key`, `check_password_strength`, `generate_api_key`, `obfuscate_email`, `obfuscate_card` |
| `backend/src/errors.rs` | `AppError`, `is_fraud_related`, `requires_logging`, `client_safe_message`, `handle_postgres_error`, `validation_error`, `ApiError` |
| `backend/src/feature_tests.rs` | `config`, `user` |
| `backend/src/features.rs` | `FeatureGate`, `FeatureGateService`, `FeatureError`, `Feature`, `identity`, `administrator`, `route_features`, `check_request`, `effective`, `list`, `user_features`, `Change`, `patch_flag`, `patch_user`, `patch_role`, `AuditQuery`, `audit`, `configure_admin` |
| `backend/src/financial_tests.rs` |  |
| `backend/src/handlers/admin/analytics.rs` | `DashboardMetrics`, `get_dashboard_metrics` |
| `backend/src/handlers/admin/bets.rs` | `BetListItem`, `get_all_bets`, `get_bet`, `SettleBetRequest`, `settle_bet`, `void_bet`, `delete_bet` |
| `backend/src/handlers/admin/events.rs` | `EventRecord`, `CreateEventRequest`, `EventResponse`, `create_event`, `get_all_events`, `get_event`, `UpdateEventRequest`, `update_event`, `delete_event`, `update_event_status` |
| `backend/src/handlers/admin/mod.rs` |  |
| `backend/src/handlers/admin/monitoring.rs` | `FraudAlert`, `AdminLog`, `get_fraud_alerts`, `get_audit_logs` |
| `backend/src/handlers/admin/tests.rs` |  |
| `backend/src/handlers/admin/users.rs` | `ListUsersQuery`, `UserListItem`, `UsersListResponse`, `UserDetailsResponse`, `UpdateUserStatusRequest`, `list_users`, `get_user_details`, `update_user_status`, `verify_user` |
| `backend/src/handlers/ai_picks.rs` | `AiPicksService`, `from_env`, `GenerateRequest`, `ChatRequest`, `generate`, `list`, `get`, `chat`, `conversations`, `conversation`, `configure` |
| `backend/src/handlers/auth.rs` | `RegisterRequestHandler`, `AuthResponse`, `UserResponse`, `register`, `login`, `logout`, `refresh`, `verify_email` |
| `backend/src/handlers/betting.rs` | `EventQuery`, `get_events`, `get_event`, `place_bet`, `get_user_bets`, `get_bet` |
| `backend/src/handlers/chat.rs` | `ChatRequest`, `ChatResponse`, `ErrorResponse`, `chat`, `chat_health` |
| `backend/src/handlers/health.rs` | `HealthCheckResponse`, `health_check`, `readiness` |
| `backend/src/handlers/intelligence.rs` | `DeviggedOddsRow`, `DeviggedOddsQuery`, `get_devigged_odds`, `EvBetRow`, `EvBetsQuery`, `get_ev_bets`, `ArbitrageRow`, `ArbitrageQuery`, `get_arbitrage`, `RefreshIntelligenceResponse`, `refresh_intelligence` |
| `backend/src/handlers/limits.rs` | `GamblingLimitsResponse`, `UpdateLimitsRequest`, `SelfExcludeRequest`, `get_limits`, `update_limits`, `self_exclude` |
| `backend/src/handlers/mod.rs` |  |
| `backend/src/handlers/monitoring.rs` | `metrics` |
| `backend/src/handlers/not_found.rs` | `not_found` |
| `backend/src/handlers/parlay.rs` | `calculate_parlay`, `save_parlay`, `get_saved_parlays`, `get_parlay`, `get_calculation_history`, `delete_parlay` |
| `backend/src/handlers/player_props.rs` | `PlayerProp`, `PlayerPropsQuery`, `get_player_props`, `get_player_props_by_event` |
| `backend/src/handlers/sports.rs` | `SportsResponse`, `SportInfo`, `LeagueInfo`, `BetCategoriesResponse`, `BetCategory`, `get_sports`, `get_bet_categories`, `get_sport_leagues` |
| `backend/src/handlers/user.rs` | `UserProfile`, `UpdateProfileRequest`, `ChangePasswordRequest`, `UserActivity`, `get_profile`, `update_profile`, `get_activity`, `change_password` |
| `backend/src/handlers/wallet.rs` | `DepositRequest`, `WithdrawRequest`, `BalanceResponse`, `TransactionResponse`, `get_balance`, `deposit`, `withdraw`, `get_transactions` |
| `backend/src/main.rs` | `run_server` |
| `backend/src/middleware/admin_auth.rs` | `RequireAdmin`, `new`, `RequireAdminMiddleware`, `RequireSuperAdmin`, `new`, `RequireSuperAdminMiddleware`, `get_admin_claims` |
| `backend/src/middleware/jwt_auth.rs` | `RequireAuth`, `new`, `RequireAuthMiddleware`, `get_claims` |
| `backend/src/middleware/mod.rs` |  |
| `backend/src/middleware/monitoring.rs` | `Metrics`, `new`, `MetricsMiddleware` |
| `backend/src/middleware/rate_limit.rs` | `RateLimitMiddleware`, `new`, `RateLimitMiddlewareService` |
| `backend/src/middleware/security_headers.rs` | `SecurityHeaders`, `SecurityHeadersMiddleware` |
| `backend/src/models.rs` | `User`, `is_admin`, `is_super_admin`, `CreateUserRequest`, `RegisterRequest`, `LoginRequest`, `UserResponse`, `UpdateUserRequest`, `Wallet`, `WalletResponse`, `DepositRequest`, `WithdrawalRequest`, `Transaction`, `TransactionResponse`, `Event`, `EventResponse`, `Bet`, `PlaceBetRequest`, `BetResponse`, `GamblingLimits`, `UpdateLimitsRequest`, `UserActivity`, `UserActivityResponse`, `Claims`, `ApiResponse`, `PaginatedResponse`, `PaginationMeta`, `BettingPattern`, `FraudAlert`, `HealthCheck`, `DatabaseHealth`, `RateLimitStatus`, `success`, `error`, `from_user`, `from_event`, `from_bet`, `from_transaction`, `ParlayBet`, `CalculateParlayRequest`, `ParlayCalculationResponse`, `SaveParlayRequest`, `Parlay`, `ParlayLeg`, `ParlayCalculation`, `ParlayWithLegs` |
| `backend/src/monitoring.rs` | `MonitoringService`, `SystemMetrics`, `new`, `increment_requests`, `increment_errors`, `get_metrics`, `record_bet`, `record_registration`, `record_deposit`, `record_withdrawal`, `get_health_status`, `metrics_enabled`, `HealthStatus` |
| `backend/src/pick_selection.rs` | `rank`, `build_picks` |
| `backend/src/pipeline_gateway.rs` | `normalize_pipeline_url`, `proxy` |
| `backend/src/published.rs` | `prediction` |
| `backend/src/published_picks.rs` | `generate` |
| `backend/src/rag.rs` | `Message`, `RagAgent`, `from_env`, `allow_request`, `answer` |
| `backend/src/rates.rs` | `RateLimitType`, `RateLimiter`, `new`, `check`, `get_quota_info`, `UserRateLimiter`, `new`, `check`, `cleanup_inactive`, `tracked_users_count`, `IpRateLimiter`, `new`, `check`, `cleanup_inactive`, `tracked_ips_count`, `RateLimiters`, `new`, `check_bet_limit`, `check_login_limit`, `check_register_limit`, `check_deposit_limit`, `check_withdraw_limit`, `check_api_limit`, `cleanup_all`, `get_stats`, `RateLimiterStats` |
| `backend/src/session_tests.rs` |  |
| `backend/src/sessions.rs` | `create`, `validate`, `revoke` |
| `backend/src/utils.rs` | `extract_ip_address`, `extract_user_agent`, `extract_user_id`, `validate_age`, `validate_bet_type`, `validate_selection`, `validate_email`, `sanitize_string`, `generate_session_id` |
