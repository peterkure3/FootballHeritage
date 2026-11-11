import { test, expect } from '@playwright/test';
import { defaultApiFixture } from './feature-fixture.js';

// Explicit test data only. The application never substitutes these records.
const labels = { nba: 'NBA', nfl: 'NFL', wnba: 'WNBA', ncaab: 'NCAAB', 'college-football': 'College Football', football: 'Football' };
function games(sport = 'nba') {
  return [
    { id: `${sport}:next`, sport, league: labels[sport], home_team: 'Los Angeles Lakers', away_team: 'Boston Celtics', date: '2026-11-11T18:00:00Z', status: 'SCHEDULED', home_score: null, away_score: null },
    { id: `${sport}:tomorrow`, sport, league: labels[sport], home_team: 'New York Knicks', away_team: 'Golden State Warriors', date: '2026-11-12T20:00:00Z', status: 'SCHEDULED', home_score: null, away_score: null },
    { id: `${sport}:final`, sport, league: labels[sport], home_team: 'Houston Rockets', away_team: 'Denver Nuggets', date: '2026-11-11T06:00:00Z', status: 'FINISHED', home_score: 110, away_score: 100 },
    { id: `${sport}:yesterday`, sport, league: labels[sport], home_team: 'Atlanta Hawks', away_team: 'Los Angeles Lakers', date: '2026-11-10T20:00:00Z', status: 'FINISHED', home_score: 114, away_score: 124 },
  ];
}

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(new Date('2026-11-11T12:00:00Z'));
  await page.route('**/api/v1/**', defaultApiFixture);
  await page.route('**/api/v1/pipeline/sport-schedule/*?*', route => {
    const url = new URL(route.request().url());
    const sport = url.pathname.split('/').at(-1);
    return route.fulfill({ json: { sport, source_issues: [], items: [...games(sport), ...games(sport).slice(0, 1), { ...games(sport)[0], sport: 'foreign', home_team: 'Foreign team' }] } });
  });
  await page.route('**/api/v1/pipeline/matches?*', route => route.fulfill({ json: games('football') }));
  await page.route('**/api/v1/pipeline/betting-intel', route => route.fulfill({ json: {
    snapshot_at: '2026-11-11T11:55:00Z', snapshot_status: 'current', sports: Object.entries(labels).map(([sport, label]) => ({
      sport, label, summary: { predictions: 10, ev_bets: 8, arbitrage: 0 },
      top_pick: { sport, competition: label, home_team: 'Los Angeles Lakers', away_team: 'Boston Celtics', kickoff: '2026-11-11T18:00:00Z',
        selection: 'home_win', probability: .72, model_status: 'candidate_preview', model_version: 'test-candidate' },
    })),
  } }));
});

test('schedule groups dates, deduplicates games and persists team/date filters', async ({ page }) => {
  await page.goto('/sport/nba/schedule');
  await expect(page.getByRole('heading', { name: 'NBA Schedule', exact: true })).toBeVisible();
  await expect(page.locator('.sc-table tbody tr')).toHaveCount(3);
  await expect(page.getByText('Foreign team', { exact: true })).toHaveCount(0);
  await expect(page.locator('.sc-final')).toHaveText(['Final']);
  await expect(page.getByRole('button', { name: 'Wed Nov 11 Today' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByLabel('Team schedules', { exact: true }).selectOption('Los Angeles Lakers');
  await expect(page.locator('.sc-table tbody tr')).toHaveCount(1);
  await expect(page).toHaveURL(/team=Los\+Angeles\+Lakers/);
  await page.reload();
  await expect(page.getByLabel('Team schedules', { exact: true })).toHaveValue('Los Angeles Lakers');
  await page.getByRole('button', { name: 'Next week', exact: true }).click();
  await expect(page).toHaveURL(/date=2026-11-18/);
  await expect(page.locator('.sc-no-games')).toHaveCount(2);
  await page.getByRole('button', { name: 'Today', exact: true }).click();
  await expect(page.locator('.sc-table tbody tr')).toHaveCount(1);
});

test('schedule opens a matchup and calendar selection survives history navigation', async ({ page }) => {
  await page.goto('/sport/nba/schedule?date=2026-11-10');
  await page.locator('.sc-match-link').filter({ hasText: 'Atlanta Hawks' }).click();
  await expect(page.getByRole('dialog')).toContainText('Los Angeles Lakers at Atlanta Hawks');
  await page.getByRole('button', { name: 'Close dialog' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByLabel('Jump to date').fill('2026-11-12');
  await expect(page.locator('.sc-table tbody tr')).toHaveCount(1);
  await page.goBack();
  await expect(page.getByLabel('Jump to date')).toHaveValue('2026-11-10');
});

test('sport home features real-scope games, finals and model probability in a bento', async ({ page }) => {
  await page.goto('/sport/nba');
  await expect(page.getByRole('region', { name: 'Prediction spotlight' })).toContainText('Los Angeles Lakers');
  await expect(page.getByRole('img', { name: '72.0 percent model probability' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Featured games' }).locator('.sc-featured-game')).toHaveCount(2);
  await expect(page.getByRole('region', { name: 'Featured results' })).toContainText('110');
  await expect(page.getByRole('region', { name: 'Featured results' }).locator('.sc-featured-game')).toHaveCount(2);
  await expect(page.getByText('Experimental candidate', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'View full schedule' }).click();
  await expect(page).toHaveURL('/sport/nba/schedule');
});

for (const sport of Object.keys(labels)) {
  test(`${sport} schedule uses its own source and date controls`, async ({ page }) => {
    await page.goto(`/sport/${sport}/schedule?date=2026-11-11`);
    await expect(page.getByRole('heading', { name: `${labels[sport]} Schedule`, exact: true })).toBeVisible();
    await expect(page.locator('.sc-table tbody tr')).toHaveCount(3);
    await expect(page.locator('.sc-schedule')).not.toContainText('Foreign team');
  });
}

for (const width of [1440, 1024, 768, 390, 320]) {
  test(`sport centre fits ${width}px and schedule keeps scrolling inside its table`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/sport/nba');
    await expect(page.locator('.sc-probability-ring')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.goto('/sport/nba/schedule');
    await expect(page.locator('.sc-table').first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}

test('schedule source failures offer retry and reject foreign-sport responses', async ({ page }) => {
  await page.route('**/api/v1/pipeline/sport-schedule/nba?*', route => route.fulfill({ json: { sport: 'wnba', items: games('wnba') } }));
  await page.goto('/sport/nba/schedule');
  await expect(page.getByRole('alert')).toContainText('The schedule source did not return NBA fixtures.');
  await expect(page.locator('.sc-table')).toHaveCount(0);
  await expect(page.locator('.sc-schedule').getByRole('button', { name: 'Retry', exact: true })).toBeVisible();
});

test('stale predictions do not display a current probability', async ({ page }) => {
  await page.route('**/api/v1/pipeline/betting-intel', route => route.fulfill({ json: { snapshot_status: 'stale', sports: [] } }));
  await page.goto('/sport/nba');
  await expect(page.getByRole('region', { name: 'Prediction spotlight' })).toContainText('Forecast needs a refresh.');
  await expect(page.locator('.sc-probability-ring')).toHaveCount(0);
});

test('sport panels use the existing typography, card and control tokens', async ({ page }) => {
  await page.goto('/sport/nba');
  await expect(page.locator('.sc-probability-ring')).toBeVisible();
  const home = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement);
    return {
      radius: getComputedStyle(document.querySelector('.sc-results-panel')).borderRadius,
      expectedRadius: root.getPropertyValue('--fh-radius-card').trim(),
      heading: getComputedStyle(document.querySelector('.sc-home-heading h2')).fontFamily,
      body: getComputedStyle(document.querySelector('.sc-featured-game')).fontFamily,
      button: getComputedStyle(document.querySelector('.sc-spotlight-action')).borderRadius,
      expectedButton: root.getPropertyValue('--fh-radius-control').trim(),
    };
  });
  expect(home.radius).toBe(home.expectedRadius);
  expect(home.button).toBe(home.expectedButton);
  expect(home.heading).toContain('Georgia');
  expect(home.body).toContain('Arial');
  await page.goto('/sport/nba/schedule');
  const schedule = await page.locator('.sc-schedule').evaluate(element => ({
    radius: getComputedStyle(element).borderRadius,
    heading: getComputedStyle(element.querySelector('h2')).fontFamily,
  }));
  expect(schedule.radius).toBe(home.expectedRadius);
  expect(schedule.heading).toContain('Georgia');
});

for (const width of [1440, 390]) {
  test(`match dialog is centred and its score remains readable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/sport/nba/schedule?date=2026-11-10&match=nba%3Ayesterday');
    const dialog = page.getByRole('dialog', { name: 'Los Angeles Lakers at Atlanta Hawks' });
    await expect(dialog).toBeVisible();
    await expect(dialog.locator('.sc-dialog-scoreboard')).toContainText('124');
    await expect(dialog.locator('.sc-dialog-scoreboard')).toContainText('114');
    const bounds = await dialog.boundingBox();
    expect(Math.abs(bounds.x + bounds.width / 2 - width / 2)).toBeLessThanOrEqual(2);
    expect(Math.abs(bounds.y + bounds.height / 2 - 450)).toBeLessThanOrEqual(2);
    expect(bounds.x).toBeGreaterThanOrEqual(15);
    expect(bounds.y).toBeGreaterThanOrEqual(15);
    expect(await dialog.locator('.sc-dialog-scoreboard strong').first().evaluate(element => parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(32);
    await page.keyboard.press('Escape');
    await expect(dialog).toHaveCount(0);
  });
}
