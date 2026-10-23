import { test } from 'node:test';
import assert from 'node:assert/strict';
import { internalTokenGuard } from '../services/internal-auth.js';

test('production chatbot denies public callers, including valid-origin requests', () => {
  process.env.NODE_ENV = 'production';
  process.env.CHATBOT_INTERNAL_TOKEN = 'a'.repeat(32);
  for (const supplied of [undefined, 'wrong-token']) {
    let status;
    const response = { status(code) { status = code; return this; }, json(body) { assert.equal(body.error.code, 'PRIVATE_SERVICE'); } };
    internalTokenGuard({ headers: { origin: 'https://staging.example.test', 'x-internal-token': supplied } }, response, () => assert.fail('must deny'));
    assert.equal(status, 403);
  }
  let accepted = false;
  internalTokenGuard({ headers: { 'x-internal-token': process.env.CHATBOT_INTERNAL_TOKEN } }, {}, () => { accepted = true; });
  assert.equal(accepted, true);
  process.env.CHATBOT_INTERNAL_TOKEN = '';
  internalTokenGuard({ headers: {} }, { status(code) { assert.equal(code, 403); return this; }, json() {} }, () => assert.fail('missing configuration must deny'));
});
