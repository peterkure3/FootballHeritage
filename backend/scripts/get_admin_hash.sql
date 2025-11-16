-- Run this query in pgAdmin or DBeaver to get the bcrypt hash
-- First, the test user was created with password 'Admin123!'

SELECT 
    email,
    password_hash,
    'Copy this hash and paste it into migration file line 225' as instruction
FROM users 
WHERE email = 'test_hash@test.com';

-- Then update the admin user with this hash:
-- UPDATE users 
-- SET password_hash = 'PASTE_HASH_HERE'
-- WHERE email = 'admin@footballheritage.com';
