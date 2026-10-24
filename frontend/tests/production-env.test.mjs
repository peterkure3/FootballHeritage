import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { productionApiBase } from '../src/utils/apiUrl.js';
import { validateProductionEnv } from '../scripts/validate-production-env.mjs';

test('production API contract accepts HTTPS origin and a single API prefix', () => {
  for (const value of ['https://api.example.test', 'https://api.example.test/', 'https://api.example.test/api/v1', 'https://api.example.test/api/v1/']) {
    assert.equal(productionApiBase(value), 'https://api.example.test/api/v1');
    assert.equal(validateProductionEnv({ VITE_API_URL: value }), 'https://api.example.test/api/v1');
  }
});

test('production API contract rejects missing, local and unsafe destinations', () => {
  for (const value of [undefined, '', ' ', 'invalid', 'http://api.example.test', 'https://localhost', 'https://127.0.0.1', 'https://[::1]', 'https://user:password@api.example.test', 'https://api.example.test?token=secret', 'https://api.example.test/#fragment', 'https://api.example.test/api/v1/api/v1', '/api/v1']) {
    assert.throws(() => productionApiBase(value), /VITE_API_URL/);
  }
});

test('public secret-like variables stay forbidden without disclosing their values', () => {
  for (const key of ['VITE_JWT_SECRET', 'VITE_INTERNAL_TOKEN', 'VITE_DB_PASSWORD', 'VITE_PRIVATE_KEY', 'VITE_GEMINI_API_KEY']) {
    assert.throws(() => validateProductionEnv({ VITE_API_URL: 'https://api.example.test', [key]: 'never-print-this-value' }), error => {
      assert.match(error.message, /Secret-like VITE/);
      assert.ok(!error.message.includes('never-print-this-value'));
      return true;
    });
  }
});

test('validator loads Vite production files and respects process environment precedence', () => {
  const directory = mkdtempSync(join(tmpdir(), 'fh-production-env-'));
  const validator = fileURLToPath(new URL('../scripts/validate-production-env.mjs', import.meta.url));
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('VITE_')));
  const run = overrides => spawnSync(process.execPath, [validator], {
    cwd: directory, env: { ...env, ...overrides }, encoding: 'utf8',
  });
  try {
    const missing = run({});
    assert.equal(missing.status, 1);
    assert.match(missing.stderr, /required/);
    assert.match(missing.stderr, /Preview or Production/);
    writeFileSync(join(directory, '.env'), 'VITE_API_URL=http://localhost:8888\n');
    assert.equal(run({}).status, 1);
    writeFileSync(join(directory, '.env.production'), 'VITE_API_URL=https://api.example.test/api/v1\n');
    assert.equal(run({}).status, 0);
    assert.equal(run({ VITE_API_URL: 'http://localhost:8888' }).status, 1);
    const invalid = run({ VITE_API_URL: 'https://user:never-print-this-value@api.example.test' });
    assert.equal(invalid.status, 1);
    assert.ok(!invalid.stderr.includes('never-print-this-value'));
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});
