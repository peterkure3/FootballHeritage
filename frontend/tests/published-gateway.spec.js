import { test, expect } from '@playwright/test';

test('browser polls a published computation with one immutable request identity', async ({ page }) => {
  await page.route('**/__gateway_transport_test', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Gateway transport test</title>' }));
  const requests = [];
  await page.route('**/api/v1/pipeline/sport-models/preview', async route => {
    requests.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData() });
    await route.fulfill(requests.length === 1
      ? { status: 202, headers: { 'X-Gateway-Pending': '1', 'Retry-After': '1' }, json: { status: 'pending' } }
      : { status: 200, json: { probability: 0.55, source: 'test-only-publication' } });
  });
  await page.goto('/__gateway_transport_test');
  const result = await page.evaluate(async () => {
    const { publishedFetch } = await import('/src/utils/publishedFetch.mjs');
    const response = await publishedFetch(fetch, `${location.origin}/api/v1/pipeline/sport-models/preview`, { method: 'POST', body: '{"candidate_id":"test-only"}' });
    return { status: response.status, body: await response.json() };
  });
  expect(result).toEqual({ status: 200, body: { probability: 0.55, source: 'test-only-publication' } });
  expect(requests).toHaveLength(2);
  expect(requests[0]).toEqual(requests[1]);
  expect(requests[0].key).toMatch(/^[a-f0-9-]{36}$/);
});
