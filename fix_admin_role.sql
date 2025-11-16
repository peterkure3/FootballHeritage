-- Fix admin user role and password
-- Run this with: psql -U postgres -d football_heritage -f fix_admin_role.sql

-- Update admin user to have superadmin role and proper password
UPDATE users 
SET 
    password_hash = '$argon2id$v=19$m=19456,t=2,p=1$OSz9XW9vKu3Sd7UXLxtSGg$UH8FSANHWQDGhI0j+6edvYpTCF1X3uZ5wDogB12uU+k',
    role = 'superadmin',
    is_verified = true,
    is_active = true,
    updated_at = NOW()
WHERE email = 'admin@footballheritage.com';

-- Verify the update
SELECT email, role, is_verified, is_active, created_at, updated_at 
FROM users 
WHERE email = 'admin@footballheritage.com';

SELECT 'Admin role fixed! User now has superadmin role.' as message;
