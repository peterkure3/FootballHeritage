-- Simple Wallet Reset Script
-- This deletes all existing wallets so they can be recreated with the new encryption key
-- Run this, then restart the backend and wallets will be auto-created on first access

BEGIN;

-- Show wallets that will be deleted
SELECT 
    w.id as wallet_id,
    u.email,
    w.created_at
FROM wallets w
JOIN users u ON w.user_id = u.id;

-- Delete all wallets (they will be recreated with new encryption key)
DELETE FROM wallets;

-- Verify deletion
SELECT COUNT(*) as remaining_wallets FROM wallets;

COMMIT;

-- After running this:
-- 1. Restart the backend server
-- 2. Wallets will be auto-created with 0.00 balance when users access wallet endpoints
-- 3. Users can deposit funds normally
