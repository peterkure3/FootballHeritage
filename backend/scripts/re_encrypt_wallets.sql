-- Re-encryption Script for Wallet Balances
-- This script should be run after changing the ENCRYPTION_KEY
-- WARNING: This will reset all wallet balances to 0.00 with the new encryption key

-- First, let's see what wallets exist
SELECT 
    w.id as wallet_id,
    w.user_id,
    u.email,
    w.created_at
FROM wallets w
JOIN users u ON w.user_id = u.id;

-- Option 1: Reset all wallets to 0.00 (SAFEST - no data loss risk)
-- Uncomment the following lines to execute:

-- UPDATE wallets 
-- SET 
--     encrypted_balance = 'ENCRYPTED_ZERO_PLACEHOLDER',
--     encryption_iv = 'IV_PLACEHOLDER',
--     updated_at = NOW()
-- WHERE TRUE;

-- After running this, restart the backend server and use the deposit endpoint
-- to add funds with the new encryption key

-- Option 2: Manual re-encryption (requires backend script)
-- Create a Rust script that:
-- 1. Reads all wallets with old key
-- 2. Decrypts balances with old key
-- 3. Re-encrypts with new key
-- 4. Updates database

-- For now, we recommend Option 1 (reset to zero) since this appears to be
-- a development environment
