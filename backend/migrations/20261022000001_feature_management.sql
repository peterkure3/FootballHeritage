-- Existing access is preserved by explicit defaults. Emergency switches never
-- admit an exception, including for administrators.
CREATE TABLE feature_flags (
    key TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    emergency_disabled BOOLEAN NOT NULL DEFAULT FALSE,
    maintenance_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    default_enabled BOOLEAN NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE user_feature_overrides (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    feature_key TEXT NOT NULL REFERENCES feature_flags(key),
    enabled BOOLEAN NOT NULL,
    PRIMARY KEY(user_id, feature_key)
);
CREATE TABLE role_feature_rules (
    role TEXT NOT NULL CHECK(role IN ('guest','user','admin','superadmin')),
    feature_key TEXT NOT NULL REFERENCES feature_flags(key),
    enabled BOOLEAN NOT NULL,
    PRIMARY KEY(role, feature_key)
);
CREATE TABLE feature_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    administrator_id UUID NOT NULL,
    action TEXT NOT NULL,
    feature_key TEXT NOT NULL,
    target TEXT NOT NULL,
    before_value JSONB NOT NULL,
    after_value JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX feature_audit_logs_created ON feature_audit_logs(created_at DESC, id DESC);
INSERT INTO feature_flags(key,description,category,enabled,default_enabled) VALUES
('maintenance','Restrict product operations during maintenance','Platform',FALSE,FALSE),
('registration','New account registration','Platform',TRUE,TRUE),
('ai_picks','AI-generated picks and saved picks','AI',TRUE,TRUE),
('ai_chat','Grounded AI conversations','AI',TRUE,TRUE),
('predictions','Prediction dashboards and model previews','Analytics',TRUE,TRUE),
('intelligence','De-vigged odds, EV and arbitrage','Analytics',TRUE,TRUE),
('best_picks','Best-value bet recommendations','Analytics',TRUE,TRUE),
('player_props','Player proposition markets','Betting',TRUE,TRUE),
('parlays','Parlay calculation and saved parlays','Betting',TRUE,TRUE),
('betting','Bet placement and bet history','Betting',TRUE,TRUE),
('wallet','Wallet balances and transactions','Account',TRUE,TRUE),
('wallet_funding','Demo deposits and withdrawals; no payment provider','Account',TRUE,TRUE),
('sports','Sports and league browsing','Sports',TRUE,TRUE),
('fpl','Fantasy Premier League tools','Sports',TRUE,TRUE),
('college','College basketball and tournament tools','Sports',TRUE,TRUE);
INSERT INTO role_feature_rules(role,feature_key,enabled)
SELECT role,key,TRUE FROM feature_flags CROSS JOIN
    (VALUES ('guest'),('user'),('admin'),('superadmin')) roles(role);

-- Feature audit rows are immutable through ordinary application SQL.
CREATE FUNCTION protect_feature_audit() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Feature audit history is append-only';
END $$;
CREATE TRIGGER feature_audit_immutable BEFORE UPDATE OR DELETE ON feature_audit_logs
FOR EACH ROW EXECUTE FUNCTION protect_feature_audit();

-- Database-level protection covers status changes and future role/delete APIs.
CREATE FUNCTION protect_last_superadmin() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.role = 'superadmin' AND OLD.is_active AND
       (TG_OP = 'DELETE' OR NEW.role IS DISTINCT FROM 'superadmin' OR NOT NEW.is_active) THEN
        PERFORM pg_advisory_xact_lock(762604221);
        IF NOT EXISTS(SELECT 1 FROM users WHERE role='superadmin' AND is_active
                      AND (locked_until IS NULL OR locked_until<=NOW()) AND id<>OLD.id) THEN
            RAISE EXCEPTION 'Cannot remove the last active superadmin';
        END IF;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER users_last_superadmin BEFORE UPDATE OF role,is_active OR DELETE ON users
FOR EACH ROW EXECUTE FUNCTION protect_last_superadmin();
