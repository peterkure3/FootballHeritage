import { test, expect } from '@playwright/test';

test('Try Again recovers a failed Login import without losing the return URL', async ({ page }) => {
  let failImport = true;
  let importRequests = 0;
  await page.route('**/src/pages/Login.jsx*', async (route) => {
    importRequests += 1;
    if (failImport) {
      return route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<!doctype html><html><body>Unexpected HTML fallback</body></html>',
      });
    }
    return route.continue();
  });

  await page.goto('/login?returnTo=%2Fprofile');
  await expect(page.getByRole('heading', { name: 'Oops! Something went wrong' })).toBeVisible();
  failImport = false;
  await page.getByRole('button', { name: 'Try Again', exact: true }).click();

  await expect(page.getByRole('heading', { name: 'Welcome back.' })).toBeVisible();
  await expect(page.getByLabel('Email Address')).toBeVisible();
  await expect(page).toHaveURL(/\/login\?returnTo=%2Fprofile$/);
  expect(importRequests).toBeGreaterThan(1);
});
