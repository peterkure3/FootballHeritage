-- Clean up old migration entries that don't have files
DELETE FROM _sqlx_migrations WHERE version = 20241019000001;

-- Show remaining migrations
SELECT version, description, installed_on FROM _sqlx_migrations ORDER BY installed_on;
