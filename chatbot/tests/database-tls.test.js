import test from 'node:test';
import assert from 'node:assert/strict';
import { databaseTls } from '../services/database-tls.js';

test('production database certificates are verified', () => {
  assert.deepEqual(databaseTls({ NODE_ENV: 'production' }), { rejectUnauthorized: true });
  assert.throws(() => databaseTls({ NODE_ENV: 'production', PGSSLMODE: 'disable' }));
  assert.equal(databaseTls({ NODE_ENV: 'production', DEPLOYMENT_ENV: 'local-staging', PGSSLMODE: 'disable' }), false);
});
