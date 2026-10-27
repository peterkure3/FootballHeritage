import test from 'node:test';
import assert from 'node:assert/strict';
import { publishedFetch } from '../src/utils/publishedFetch.mjs';

test('published jobs preserve the exact body and idempotency key while polling', async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push([url, options.body, options.headers.get('Idempotency-Key')]);
    return calls.length === 1 ? new Response('{}', { status: 202, headers: { 'X-Gateway-Pending': '1', 'Retry-After': '1' } }) : Response.json({ probability: 0.55 });
  };
  const result = await publishedFetch(fetcher, 'https://api.test/api/v1/pipeline/sport-models/preview', { method: 'POST', body: '{"candidate_id":"reviewed"}' });
  assert.equal(result.status, 200);
  assert.equal(calls.length, 2);
  assert.deepEqual(calls[0], calls[1]);
  assert.match(calls[0][2], /^[a-f0-9-]{36}$/);
});

test('ordinary accepted responses are not treated as computation results', async () => {
  let calls = 0;
  const response = await publishedFetch(async () => { calls++; return new Response('', { status: 202 }); }, '/api/v1/other');
  assert.equal(response.status, 202);
  assert.equal(calls, 1);
});

test('pending timeout is an explicit failure rather than an empty success', async () => {
  const response = await publishedFetch(async () => new Response('{}', { status: 202, headers: { 'X-Gateway-Pending': '1' } }), '/api/v1/pipeline/matches', {}, 0);
  assert.equal(response.status, 503);
  assert.equal((await response.json()).error.code, 'PUBLICATION_PENDING');
});

test('aborting a pending computation stops polling', async () => {
  const controller = new AbortController();
  controller.abort(new DOMException('Cancelled', 'AbortError'));
  let calls = 0;
  await assert.rejects(publishedFetch(async () => { calls++; return new Response('{}', { status: 202, headers: { 'X-Gateway-Pending': '1' } }); }, '/api/v1/pipeline/matches', { signal: controller.signal }), { name: 'AbortError' });
  assert.equal(calls, 1);
});
