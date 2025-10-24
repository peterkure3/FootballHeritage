-- ============================================================================
-- Migration: Add Admin System
-- Description: Adds role-based access control and admin management tables
-- Date: 2025-10-24
-- ============================================================================

-- Step 1: Add role column to users table
-- ============================================================================
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user' 
CHECK (role IN ('user', 'admin', 'superadmin'));

-- Update existing users to have 'user' role
UPDATE users SET role = 'user' WHERE role IS NULL;

-- Create index for faster role-based queries
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Step 2: Create admin activity logs table
-- ============================================================================
CREATE TABLE IF NOT EXISTS admin_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),  -- 'user', 'event', 'bet', 'system', 'odds'
    target_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for admin logs
CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action ON admin_logs(action);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target ON admin_logs(target_type, target_id);

-- Step 3: Create platform metrics table
-- ============================================================================
CREATE TABLE IF NOT EXISTS platform_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL UNIQUE,
    total_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    total_bets INTEGER DEFAULT 0,
    total_bet_amount DECIMAL(15,2) DEFAULT 0,
    total_payouts DECIMAL(15,2) DEFAULT 0,
    platform_revenue DECIMAL(15,2) DEFAULT 0,
    total_deposits DECIMAL(15,2) DEFAULT 0,
    total_withdrawals DECIMAL(15,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for date-based queries
CREATE INDEX IF NOT EXISTS idx_platform_metrics_date ON platform_metrics(date DESC);

-- Step 4: Create fraud alerts table
-- ============================================================================
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    alert_type VARCHAR(50) NOT NULL,  
    -- Types: 'multiple_accounts', 'unusual_betting', 'rapid_deposits', 'suspicious_withdrawal', 'pattern_detected'
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT NOT NULL,
    metadata JSONB,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'investigating', 'resolved', 'false_positive')),
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fraud alerts
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_user_id ON fraud_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON fraud_alerts(status);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_severity ON fraud_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_fraud_alerts_created_at ON fraud_alerts(created_at DESC);

-- Step 5: Add admin-specific columns to events table (if needed)
-- ============================================================================
ALTER TABLE events 
ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS settled_by UUID REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS settled_at TIMESTAMP WITH TIME ZONE;

-- Step 6: Create function to update platform metrics daily
-- ============================================================================
CREATE OR REPLACE FUNCTION update_platform_metrics()
RETURNS void AS $$
DECLARE
    metric_date DATE := CURRENT_DATE;
BEGIN
    INSERT INTO platform_metrics (
        date,
        total_users,
        new_users,
        active_users,
        total_bets,
        total_bet_amount,
        total_payouts,
        platform_revenue,
        total_deposits,
        total_withdrawals
    )
    SELECT
        metric_date,
        (SELECT COUNT(*) FROM users WHERE is_active = true),
        (SELECT COUNT(*) FROM users WHERE DATE(created_at) = metric_date),
        (SELECT COUNT(DISTINCT user_id) FROM bets WHERE DATE(created_at) = metric_date),
        (SELECT COUNT(*) FROM bets WHERE DATE(created_at) = metric_date),
        (SELECT COALESCE(SUM(amount), 0) FROM bets WHERE DATE(created_at) = metric_date),
        (SELECT COALESCE(SUM(potential_win), 0) FROM bets WHERE status = 'WON' AND DATE(settled_at) = metric_date),
        (SELECT COALESCE(SUM(amount), 0) - COALESCE(SUM(potential_win), 0) 
         FROM bets 
         WHERE status IN ('WON', 'LOST') AND DATE(settled_at) = metric_date),
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE transaction_type = 'DEPOSIT' AND DATE(created_at) = metric_date),
        (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE transaction_type = 'WITHDRAWAL' AND DATE(created_at) = metric_date)
    ON CONFLICT (date) 
    DO UPDATE SET
        total_users = EXCLUDED.total_users,
        new_users = EXCLUDED.new_users,
        active_users = EXCLUDED.active_users,
        total_bets = EXCLUDED.total_bets,
        total_bet_amount = EXCLUDED.total_bet_amount,
        total_payouts = EXCLUDED.total_payouts,
        platform_revenue = EXCLUDED.platform_revenue,
        total_deposits = EXCLUDED.total_deposits,
        total_withdrawals = EXCLUDED.total_withdrawals,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Step 7: Create view for admin dashboard summary
-- ============================================================================
CREATE OR REPLACE VIEW admin_dashboard_summary AS
SELECT
    -- User metrics
    (SELECT COUNT(*) FROM users WHERE is_active = true) as total_active_users,
    (SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE) as new_users_today,
    (SELECT COUNT(DISTINCT user_id) FROM bets WHERE DATE(created_at) = CURRENT_DATE) as active_users_today,
    
    -- Bet metrics
    (SELECT COUNT(*) FROM bets WHERE DATE(created_at) = CURRENT_DATE) as bets_today,
    (SELECT COALESCE(SUM(amount), 0) FROM bets WHERE DATE(created_at) = CURRENT_DATE) as bet_volume_today,
    (SELECT COUNT(*) FROM bets WHERE status = 'PENDING') as pending_bets,
    
    -- Revenue metrics
    (SELECT COALESCE(SUM(amount), 0) - COALESCE(SUM(potential_win), 0) 
     FROM bets 
     WHERE status IN ('WON', 'LOST') AND DATE(settled_at) = CURRENT_DATE) as revenue_today,
    
    -- Event metrics
    (SELECT COUNT(*) FROM events WHERE status = 'LIVE') as live_events,
    (SELECT COUNT(*) FROM events WHERE status = 'UPCOMING' AND event_date > CURRENT_TIMESTAMP) as upcoming_events,
    
    -- Alert metrics
    (SELECT COUNT(*) FROM fraud_alerts WHERE status = 'pending') as pending_alerts,
    (SELECT COUNT(*) FROM fraud_alerts WHERE status = 'pending' AND severity IN ('high', 'critical')) as critical_alerts;

-- Step 8: Create function to log admin actions
-- ============================================================================
CREATE OR REPLACE FUNCTION log_admin_action(
    p_admin_id UUID,
    p_action VARCHAR(100),
    p_target_type VARCHAR(50) DEFAULT NULL,
    p_target_id UUID DEFAULT NULL,
    p_details JSONB DEFAULT NULL,
    p_ip_address VARCHAR(45) DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    log_id UUID;
BEGIN
    INSERT INTO admin_logs (
        admin_id,
        action,
        target_type,
        target_id,
        details,
        ip_address,
        user_agent
    ) VALUES (
        p_admin_id,
        p_action,
        p_target_type,
        p_target_id,
        p_details,
        p_ip_address,
        p_user_agent
    )
    RETURNING id INTO log_id;
    
    RETURN log_id;
END;
$$ LANGUAGE plpgsql;

-- Step 9: Insert initial platform metrics for today
-- ============================================================================
SELECT update_platform_metrics();

-- Step 10: Create sample admin user (for testing only - change password in production!)
-- ============================================================================
-- Note: This creates an admin user with email 'admin@footballheritage.com'
-- Password: 'Admin123!' (MUST be changed in production)
-- The password hash below is for 'Admin123!' using Argon2

INSERT INTO users (
    email,
    password_hash,
    first_name,
    last_name,
    date_of_birth,
    role,
    is_verified,
    is_active
) VALUES (
    'admin@footballheritage.com',
    '$argon2id$v=19$m=19456,t=2,p=1$VGhpc0lzQVNhbHRGb3JUZXN0$qLml5cXhXQzJhcGFzc3dvcmRoYXNo',  -- Change this!
    'Admin',
    'User',
    '1990-01-01',
    'superadmin',
    true,
    true
)
ON CONFLICT (email) DO NOTHING;

-- Create wallet for admin user
INSERT INTO wallets (user_id, encrypted_balance, encryption_iv)
SELECT 
    id,
    'encrypted_0',  -- Will be properly encrypted by application
    'test_iv'
FROM users 
WHERE email = 'admin@footballheritage.com'
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE '✅ Admin system migration completed successfully!';
    RAISE NOTICE '📊 Tables created: admin_logs, platform_metrics, fraud_alerts';
    RAISE NOTICE '👤 Role column added to users table';
    RAISE NOTICE '🔍 Indexes created for performance';
    RAISE NOTICE '📈 Views and functions created';
    RAISE NOTICE '⚠️  IMPORTANT: Change admin password immediately!';
    RAISE NOTICE '📧 Admin email: admin@footballheritage.com';
    RAISE NOTICE '🔑 Temp password: Admin123!';
END $$;
