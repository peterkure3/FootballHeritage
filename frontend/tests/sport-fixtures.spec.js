import { test, expect } from '@playwright/test';
import process from 'node:process';
import { featureAccess } from './feature-fixture.js';

const sports = [['ncaab', 'NCAAB'], ['nfl', 'NFL'], ['college-football', 'College Football']];

for (const [sport, label] of sports) {
  test(`${label} renders fixtures from the local gateway`, async ({page, request}) => {
    test.skip(process.env.FH_INTEL_LIVE !== '1', 'Requires the running local Rust gateway and refreshed fixture snapshot');
    const endpoint = `http://127.0.0.1:8888/api/v1/pipeline/betting-intel/${sport}`;
    const response = await request.get(endpoint);
    expect(response.ok()).toBeTruthy();
    const payload = await response.json();
    expect(payload.sport).toBe(sport);
    expect(payload.fixtures.length).toBeGreaterThan(0);
    await page.route('**/api/v1/**', async route => {
      const path = new URL(route.request().url()).pathname;
      if (path === '/api/v1/me/features') return route.fulfill({json: featureAccess});
      if (path === `/api/v1/pipeline/betting-intel/${sport}`) {
        const actual = await route.fetch({url: endpoint});
        return route.fulfill({response: actual});
      }
      return route.fulfill({json: []});
    });
    await page.goto(`/ai-picks/intelligence/${sport}/predictions`);
    await expect(page.locator('.pd-forecast')).toHaveCount(Math.min(payload.fixtures.length, 6));
    await expect(page.locator('.pd-forecast').first()).toContainText(payload.fixtures[0].home_team);
    await expect(page.locator('.pd-forecast').first()).toContainText(payload.fixtures[0].away_team);
    await expect(page.locator('.pd-feed-summary')).toContainText(String(payload.fixtures.length));
  });
}

for (const mobile of [false, true]) {
  for (const [sport, label] of sports) {
    test(`${label} shows scheduled games without forecasts on ${mobile ? 'mobile' : 'desktop'}`, async ({ page }) => {
      if (mobile) await page.setViewportSize({ width: 390, height: 844 });
      const kickoff = new Date(Date.now() + 86400000).toISOString();
      const game = {fixture_id: `${sport}:scheduled`, sport, competition: label, home_team: `${label} Home`,
        away_team: `${label} Away`, kickoff, settlement_rule: sport === 'nfl' ? 'TIE_PUSH' : 'INCLUDING_OVERTIME',
        status: 'SCHEDULED', prediction: null, prediction_status: 'unavailable'};
      let refreshes = 0;
      await page.route('**/api/v1/**', route => {
        const path = new URL(route.request().url()).pathname;
        if (path === '/api/v1/me/features') return route.fulfill({ json: featureAccess });
        if (path === `/api/v1/pipeline/betting-intel/${sport}`) {
          refreshes++;
          return route.fulfill({json: {sport, fixtures: [game, {...game, fixture_id: 'foreign', sport: 'nba', home_team: 'Foreign NBA team'}],
            predictions: [], devigged_odds: [], summary: {fixtures: 1, predictions: 0}, ai_picks: []}});
        }
        return route.fulfill({json: []});
      });
      await page.goto(`/ai-picks/intelligence/${sport}/predictions`);
      const card = page.locator('.pd-forecast');
      await expect(card).toHaveCount(1);
      await expect(card).toContainText(`${label} Home`);
      await expect(card).toContainText('Prediction unavailable');
      await expect(card.locator('.pd-probabilities')).toHaveCount(0);
      await expect(page.getByText('Foreign NBA team')).toHaveCount(0);
      await page.getByRole('button', {name: 'Refresh', exact: true}).click();
      await expect.poll(() => refreshes).toBeGreaterThan(1);
      const tabs = page.getByRole('navigation', {name: 'Prediction views'});
      await tabs.getByRole('button', {name: 'Bookmaker grid', exact: true}).click();
      await expect(page.locator('.bc-table')).toContainText(`${label} Home`);
      await page.reload();
      await expect(page.locator('.bc-table')).toContainText(`${label} Home`);
      await tabs.getByRole('button', {name: 'Upcoming fixtures', exact: true}).click();
      await expect(page.locator('.pd-forecast')).toContainText('Prediction unavailable');
      await page.goto(`/ai-picks/intelligence/${sport}/best-picks`);
      await expect(page.getByText('No eligible best picks right now.', {exact: true})).toBeVisible();
      await page.goBack();
      await expect(page.locator('.pd-forecast')).toContainText(`${label} Home`);
    });
  }
}
