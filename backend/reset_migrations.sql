-- Show current migrations
\echo 'Current migrations in database:'
SELECT version, description, installed_on FROM _sqlx_migrations ORDER BY version;

-- Delete old/missing migration entries
\echo ''
\echo 'Deleting old migration entries...'
DELETE FROM _sqlx_migrations WHERE version NOT IN (
  20251023150910,
  20251024000001,
  20251025000001
);

-- Show final state
\echo ''
\echo 'Final migrations in database:'
SELECT version, description, installed_on FROM _sqlx_migrations ORDER BY version;
