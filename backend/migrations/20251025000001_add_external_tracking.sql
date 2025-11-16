-- Add external tracking columns to events table
ALTER TABLE events 
ADD COLUMN IF NOT EXISTS external_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS external_source VARCHAR(50),
ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS updated_by UUID REFERENCES users(id);

-- Create unique constraint for external events
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_external 
ON events(external_id, external_source) 
WHERE external_id IS NOT NULL AND external_source IS NOT NULL;

-- Add settled_by column to bets table for admin tracking
ALTER TABLE bets
ADD COLUMN IF NOT EXISTS settled_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS settled_at TIMESTAMP;

-- Add admin_logs table if it doesn't exist
CREATE TABLE IF NOT EXISTS admin_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id UUID,
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id ON admin_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at ON admin_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_logs_target ON admin_logs(target_type, target_id);
