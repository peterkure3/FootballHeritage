import {test, expect} from '@playwright/test';
import {defaultApiFixture} from './feature-fixture.js';

function evidence(sport, query) {
  const label = sport.toUpperCase();
  const model = `shadow-candidate:${'a'.repeat(64)}`;
  const rows = [true, false].map((correct, index) => ({match_id:`${sport}:${index}`,home_team:`${label} Home ${index}`,away_team:`${label} Away ${index}`,
    competition:label,match_date:'2026-11-01T23:00:00Z',home_prob:.75,away_prob:.25,draw_prob:null,
    home_score:correct?110:100,away_score:105,predicted_winner:'home_win',actual_result:correct?'home_win':'away_win',
    is_correct:correct,model_version:model,prediction_created_at:'2026-11-01T20:00:00Z'}));
  const selected = rows.filter(row => !query.get('result_filter') || query.get('result_filter') === 'all' || row.is_correct === (query.get('result_filter') === 'correct'));
  return {sport,versions:[{version:model}],competitions:[label],summary:{total_predictions:2,correct_predictions:1,overall_accuracy:50,
    log_loss:.8,brier_score:.4,excluded:{unknown_kickoff:0,unknown_kickoff_outside_date_window:0,no_valid_pre_kickoff:0,pending:3,ambiguous_result:1,invalid_forecast:2},
    by_league:[{league:label,total:2,correct:1,accuracy_pct:50}],sample_start:rows[0].match_date,sample_end:rows[0].match_date,
    evidence_note:'Pre-tipoff archived candidates; final scores include overtime.'},
    history:{predictions:selected,total_count:selected.length,correct_count:selected.filter(row=>row.is_correct).length,page:1,page_size:10}};
}

test.beforeEach(async ({page}) => {
  await page.route('**/api/v1/**', defaultApiFixture);
});

for (const sport of ['nba','ncaab']) {
  test(`${sport} settled performance is scoped, filterable and responsive`, async ({page}) => {
    await page.setViewportSize({width:390,height:844});
    let footballRequests = 0;
    await page.route('**/api/v1/pipeline/predictions/**', route => {footballRequests++; return route.fulfill({json:{}});});
    await page.route(`**/api/v1/pipeline/betting-intel/${sport}/settled-performance*`, route => {
      return route.fulfill({json:evidence(sport,new URL(route.request().url()).searchParams)});
    });
    await page.goto(`/ai-picks/intelligence/${sport}/predictions?view=history`);
    await expect(page.getByRole('heading',{name:`${sport.toUpperCase()} measured performance.`,exact:true})).toBeVisible();
    await expect(page.locator('.pd-stat').filter({hasText:'Eligible fixtures'})).toContainText('2');
    await expect(page.getByRole('table')).toContainText(`${sport.toUpperCase()} Home 0`);
    await expect(page.getByRole('table').locator('tbody tr').first().locator('td').nth(1)).not.toContainText('D ');
    const request = page.waitForRequest(req => req.url().includes('/settled-performance') && new URL(req.url()).searchParams.get('result_filter') === 'incorrect');
    await page.getByRole('combobox',{name:'Result',exact:true}).selectOption('incorrect');
    await request;
    await expect(page.getByRole('table').locator('tbody tr')).toHaveCount(1);
    await expect(page.locator('.pd-stat').filter({hasText:'Eligible fixtures'})).toContainText('2');
    const modelRequest = page.waitForRequest(req => new URL(req.url()).searchParams.has('model_version'));
    await page.getByRole('combobox',{name:'Model version',exact:true}).selectOption(`shadow-candidate:${'a'.repeat(64)}`);
    await modelRequest;
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
    await page.reload();
    await expect(page.getByRole('heading',{name:`${sport.toUpperCase()} measured performance.`,exact:true})).toBeVisible();
    expect(footballRequests).toBe(0);
  });
}

test('wrong-sport settled evidence is rejected rather than substituted', async ({page}) => {
  await page.route('**/api/v1/pipeline/betting-intel/ncaab/settled-performance*', route => route.fulfill({json:evidence('nba',new URLSearchParams())}));
  await page.goto('/ai-picks/intelligence/ncaab/predictions?view=history');
  await expect(page.getByRole('alert')).toContainText('The source did not return NCAAB performance.');
  await expect(page.getByRole('table')).toHaveCount(0);
});
