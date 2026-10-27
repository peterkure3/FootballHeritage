import { test, expect } from '@playwright/test';
import { featureAccess } from './feature-fixture';

test('feature catalog filters, cancellation, and responsive layouts', async ({ page }) => {
  const features = [
    ['ai_picks', 'AI-powered selections and match recommendations.', 'Intelligence'],
    ['predictions', 'Model forecasts, probabilities and expected value.', 'Intelligence'],
    ['wallet', 'Wallet balances and transaction history.', 'Account'],
    ['registration', 'Allow new members to create an account.', 'Account'],
    ['betting', 'Bet placement and active bet management.', 'Betting'],
    ['maintenance', 'Temporarily restrict access during platform maintenance.', 'Platform'],
  ].map(([key, description, category]) => ({ key, description, category,
    enabled: key !== 'maintenance', default_enabled: true,
    emergency_disabled: key === 'betting', maintenance_allowed: key === 'wallet',
  }));
  let writes = 0;
  await page.addInitScript(() => {
    sessionStorage.setItem('token', 'test-token');
    sessionStorage.setItem('betting_user_data', JSON.stringify({ id: 'admin-test', first_name: 'Alex', email: 'admin@example.test', is_admin: true }));
  });
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() === 'PATCH') writes += 1;
    return route.fulfill({ json: path === '/api/v1/admin/features' ? { features, roles: [] } : path === '/api/v1/me/features' ? featureAccess : [] });
  });
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto('/admin/features');
  await expect(page.locator('.feature-card')).toHaveCount(6);
  await expect(page.locator('.feature-metric').filter({ hasText: 'Emergency restrictions' }).locator('strong')).toHaveText('1');
  await page.screenshot({ path: '../stages/03-build/output/admin-features-desktop-20261027.png', fullPage: true });
  await page.getByLabel('Search features').fill('no-such-feature');
  await expect(page.getByRole('heading', { name: 'No matching features' })).toBeVisible();
  await page.getByRole('button', { name: 'Clear filters', exact: true }).click();
  await page.getByRole('combobox', { name: 'Category', exact: true }).selectOption('Account');
  await expect(page.locator('.feature-card')).toHaveCount(2);
  const wallet = page.locator('.feature-card').filter({ has: page.getByRole('heading', { name: 'wallet', exact: true }) });
  await wallet.getByLabel('Globally enabled', { exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(wallet.getByLabel('Globally enabled', { exact: true })).toBeChecked();
  expect(writes).toBe(0);
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('heading', { name: 'Feature Management' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: '../stages/03-build/output/admin-features-mobile-20261027.png', fullPage: true });
  features.find((feature) => feature.key === 'maintenance').emergency_disabled = true;
  await page.reload();
  await expect(page.locator('.feature-metric').filter({ hasText: 'Maintenance mode' }).locator('strong')).toHaveText('Active');
  await expect(page.locator('.feature-card').filter({ has: page.getByRole('heading', { name: 'maintenance', exact: true }) }).locator('.feature-status')).toHaveText('Active');
});
