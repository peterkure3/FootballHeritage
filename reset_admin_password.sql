-- Reset admin password to: Admin123!
-- Run this with: psql -U postgres -d football_heritage -f reset_admin_password.sql

UPDATE users 
SET password_hash = '$argon2id$v=19$m=19456,t=2,p=1$OSz9XW9vKu3Sd7UXLxtSGg$UH8FSANHWQDGhI0j+6edvYpTCF1X3uZ5wDogB12uU+k'
WHERE email = 'admin@footballheritage.com';

SELECT 'Password reset successful! Login with:' as message;
SELECT 'Email: admin@footballheritage.com' as info;
SELECT 'Password: Admin123!' as info;
