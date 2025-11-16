-- Add status column to transactions table
ALTER TABLE transactions 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'completed' 
CHECK (status IN ('pending', 'completed', 'failed', 'cancelled'));

-- Update existing records to have 'completed' status
UPDATE transactions SET status = 'completed' WHERE status IS NULL;

-- Make status NOT NULL after setting defaults
ALTER TABLE transactions ALTER COLUMN status SET NOT NULL;
