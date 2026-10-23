import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import process from 'node:process';

test('real staging login, admin override, gated route, audit and logout', async ({ page, browser, request }) => {
  test.skip(process.env.STAGING_ACCEPTANCE !== '1', 'Requires the isolated local staging stack.');
  const values = Object.fromEntries(readFileSync(new URL('../../.staging/secrets.env', import.meta.url), 'utf8').trim().split(/\r?\n/).map(line => line.split('=')));
  const accounts = JSON.parse(readFileSync(new URL('../../.staging/accounts.json', import.meta.url), 'utf8'));
  const origin = 'https://staging.footballheritage.test:18443';
  const signIn = async (target, name) => {
    await target.goto(`${origin}/login`, { waitUntil: 'domcontentloaded' });
    await target.getByLabel('Email Address').fill(accounts[name].email);
    await target.getByLabel('Password', { exact: true }).fill(values.STAGING_ADMIN_PASSWORD);
    const response = target.waitForResponse(res => res.url().endsWith('/auth/login') && res.request().method() === 'POST');
    await target.getByRole('button', { name: 'Login', exact: true }).click();
    expect((await response).status()).toBe(200);
    await expect.poll(() => target.evaluate(() => sessionStorage.getItem('token'))).toBeTruthy();
  };
  await signIn(page, 'admin');
  const adminToken = await page.evaluate(() => sessionStorage.getItem('token'));
  await page.goto('/admin/features', { waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: 'Feature Management', exact: true })).toBeVisible();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.getByRole('heading', { name: 'Feature Management', exact: true })).toBeVisible();
  const target = `/api/v1/admin/users/${accounts.restricted.id}/features/ai_chat`;
  const restrictedContext = await browser.newContext({ ignoreHTTPSErrors: true });
  try {
    await page.getByLabel('Search features').fill('ai chat');
    await page.getByLabel('Find user by email or name').fill(accounts.restricted.email);
    await expect(page.getByRole('option', { name: accounts.restricted.email, exact: true })).toBeAttached();
    await page.getByRole('combobox', { name: 'Selected user', exact: true }).selectOption(accounts.restricted.id);
    await page.getByLabel('Selected user override').selectOption('false');
    await expect(page.getByRole('dialog')).toBeVisible();
    const changed = page.waitForResponse(res => res.url().endsWith(target) && res.request().method() === 'PATCH');
    await page.getByRole('button', { name: 'Confirm change' }).click();
    expect((await changed).status()).toBe(200);
    await expect(page.getByLabel('Selected user override')).toHaveValue('false');
    await expect(page.getByText('Feature access updated and recorded in audit history.')).toBeVisible();
    await expect(page.getByRole('cell').filter({ hasText: `user:${accounts.restricted.id}` }).first()).toBeVisible();
    const restricted = await restrictedContext.newPage();
    await signIn(restricted, 'restricted');
    await restricted.goto(`${origin}/ai-picks/chat`, { waitUntil: 'domcontentloaded' });
    await expect(restricted.getByRole('heading', { name: 'Feature unavailable', exact: true })).toBeVisible();
    await expect(restricted.locator('a[href="/ai-picks/chat"]')).toHaveCount(0);
  } finally {
    const restored = await fetch(`http://127.0.0.1:18888${target}`, {
      method: 'PATCH', headers: { Authorization: `Bearer ${adminToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: null }), signal: AbortSignal.timeout(5000),
    });
    expect(restored.status).toBe(200);
    await restrictedContext.close();
  }
  await page.getByRole('button', { name: 'Admin Administrator', exact: true }).click();
  const loggedOut = page.waitForResponse(res => res.url().endsWith('/auth/logout'));
  await page.getByRole('button', { name: 'Logout', exact: true }).click();
  expect((await loggedOut).status()).toBe(200);
  await expect(page).toHaveURL(/\/login/);
  const stale = await request.get('http://127.0.0.1:18888/api/v1/user/profile', { headers: { Authorization: `Bearer ${adminToken}` } });
  expect(stale.status()).toBe(401);
});
