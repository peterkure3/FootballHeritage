import { test } from 'node:test';
import assert from 'node:assert/strict';
import { apiBase } from '../src/utils/apiUrl.js';
import { featureForPath, hasFeature } from '../src/features/policy.js';

test('API base adds the prefix exactly once', () => {
  for (const base of ['https://api.example.test','https://api.example.test/','https://api.example.test/api/v1','https://api.example.test/api/v1/api/v1/']) {
    assert.equal(apiBase(base), 'https://api.example.test/api/v1');
  }
  assert.throws(() => apiBase(''));
});
test('unknown keys and missing policy never grant access', () => {
  assert.equal(hasFeature(undefined, 'wallet'), false);
  assert.equal(hasFeature({ features: {} }, 'unknown'), false);
  assert.equal(hasFeature({ features: { wallet: true } }, 'wallet'), true);
});
test('feature routes and essential account operations remain distinct', () => {
  assert.equal(featureForPath('/ai-picks/chat'), 'ai_chat');
  assert.equal(featureForPath('/ai-picks/intelligence/nba'), 'intelligence');
  assert.equal(featureForPath('/login'), null);
  assert.equal(featureForPath('/profile'), null);
  assert.equal(featureForPath('/admin/features'), null);
});
