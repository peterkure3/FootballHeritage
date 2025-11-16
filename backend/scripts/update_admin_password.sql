-- Update admin user with the bcrypt hash from test user
-- This copies the password hash for 'Admin123!' to the admin account

UPDATE users 
SET password_hash = (
    SELECT password_hash 
    FROM users 
    WHERE email = 'test_hash@test.com'
)
WHERE email = 'admin@footballheritage.com';

-- Verify the update
SELECT 
    email,
    role,
    CASE 
        WHEN password_hash LIKE '$2b$%' THEN '✅ Bcrypt hash (correct)'
        WHEN password_hash LIKE '$argon2%' THEN '❌ Argon2 hash (wrong)'
        ELSE '❌ Unknown hash format'
    END as hash_type,
    is_active,
    is_verified
FROM users 
WHERE email IN ('admin@footballheritage.com', 'test_hash@test.com')
ORDER BY role DESC;
