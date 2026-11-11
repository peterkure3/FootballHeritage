import { featureAccess } from './feature-fixture.js';
import { test, expect } from '@playwright/test';

// Explicit test-only data, never application fallback content.
const game = { fixture_id:'test-game',sport:'nba',competition:'NBA',home_team:'Boston Celtics',away_team:'New York Knicks',
  kickoff:'2026-10-25T23:00:00Z',settlement_rule:'INCLUDING_OVERTIME',generated_at:'2026-10-25T20:00:00Z',
  model_version:'test-candidate',status:'candidate_preview',probabilities:{home_win:.6,away_win:.4} };
const leg = {selection:'home_win',decimal_odds:2.2,bookmaker:'Test Book A',observed_at:'2026-10-25T20:00:00Z'};
const pick = {...game,...leg,probability:.6,ev_pct:.32,pick_type:'model_value'};
const market = {...game,market:'h2h',bookmaker:'Test Book A',fair_probabilities:{home_win:.52,away_win:.48},overround:.04,
  legs:{home_win:leg,away_win:{...leg,selection:'away_win',decimal_odds:1.9}}};
const summary = {fixtures:1,ai_picks:1,predictions:1,devigged_odds:1,ev_bets:1,player_props:1,arbitrage:1};
const data = {sport:'nba',label:'NBA',snapshot_at:'2026-10-25T20:00:00Z',snapshot_status:'current',source_errors:[],summary,
  ai_picks:[pick],predictions:[game],devigged_odds:[market],
  ev_bets:[{...pick,probability_basis:'other_book_consensus',model_version:null,model_status:null,reference_books:['Test Book B','Test Book C']}],
  player_props:[{...market,market:'player_points',player:'Test Player',line:20.5,fair_probabilities:{over:.52,under:.48},
    legs:{over:{...leg,selection:'over'},under:{...leg,selection:'under',decimal_odds:1.9}}}],
  arbitrage:[{...game,market:'h2h',gross_roi:.1,execution_verified:false,legs:[{...leg,reference_stake:50},
    {...leg,selection:'away_win',bookmaker:'Test Book B',reference_stake:50}]}]};
const sports = [['football','Football'],['nba','NBA'],['nfl','NFL'],['wnba','WNBA'],['ncaab','NCAAB'],['college-football','College Football']];

test.beforeEach(async ({page}) => {
  await page.route('**/api/v1/me/features', route => route.fulfill({json: featureAccess}));
});

test('wrong-sport snapshots never populate Best Picks', async ({page}) => {
  await mock(page);
  await page.route('**/api/v1/pipeline/betting-intel/wnba', route => route.fulfill({json:data}));
  await page.goto('/ai-picks/intelligence/wnba/best-picks');
  await expect(page.getByText('No eligible best picks right now.', {exact:true})).toBeVisible();
  await expect(page.getByRole('table')).toHaveCount(0);
});

test('sport predictions and picks retain the existing intelligence flag', async ({page}) => {
  await mock(page);
  await page.route('**/api/v1/me/features', route => route.fulfill({json:{features:{...featureAccess.features,intelligence:false}}}));
  await page.goto('/sport/nba');
  const nav = page.locator('.fh-subnav');
  await expect(nav.getByRole('link',{name:'Home',exact:true})).toBeVisible();
  await expect(nav.getByRole('link',{name:'Best Picks',exact:true})).toHaveCount(0);
  await expect(nav.getByRole('link',{name:'Predictions',exact:true})).toHaveCount(0);
  await page.goto('/ai-picks/intelligence/nba/best-picks');
  await expect(page.getByRole('heading',{name:'Feature unavailable',exact:true})).toBeVisible();
});

async function mock(page) {
  await page.route('**/api/v1/pipeline/betting-intel/*/settled-performance*', route => {
    const sport = new URL(route.request().url()).pathname.split('/').at(-2);
    return route.fulfill({json:{sport,versions:[],competitions:[sport.toUpperCase()],summary:{
      total_predictions:0,correct_predictions:0,overall_accuracy:null,log_loss:null,brier_score:null,
      excluded:{unknown_kickoff:0,unknown_kickoff_outside_date_window:0,no_valid_pre_kickoff:0,pending:0,ambiguous_result:0,invalid_forecast:0},
      by_league:[],sample_start:null,sample_end:null,evidence_note:'No retained eligible forecasts yet.'},
      history:{predictions:[],total_count:0,correct_count:0,page:1,page_size:10}}});
  });
  await page.route('**/api/v1/pipeline/prediction-dashboard/fixtures?*', route => route.fulfill({json:{items:[],total_count:0,competitions:[],bookmakers:[],generated_at:data.snapshot_at,active_model_version:'test'}}));
  await page.route('**/api/v1/me/features', route => route.fulfill({ json: featureAccess }));
  await page.route('**/api/v1/pipeline/betting-intel', route => route.fulfill({json:{snapshot_at:data.snapshot_at,snapshot_status:'current',source_errors:[],
    sports:sports.map(([sport,label])=>({sport,label,summary:sport==='nba'?summary:{},top_pick:sport==='nba'?pick:null,next_prediction:sport==='nba'?game:null}))}}));
  await page.route('**/api/v1/pipeline/betting-intel/*', route => {
    const sport = new URL(route.request().url()).pathname.split('/').pop();
    return route.fulfill({json:sport==='nba'?data:{...data,sport,label:'WNBA',summary:{},ai_picks:[],predictions:[],ev_bets:[],arbitrage:[],devigged_odds:[],player_props:[]}});
  });
}

test('NBA shares prediction cards and two-way bookmaker tools without soccer results', async ({page}) => {
  await mock(page);
  const now = new Date().toISOString();
  const upcoming = {...game, kickoff:new Date(Date.now()+7200000).toISOString(), generated_at:now};
  const freshMarket = {...market, kickoff:upcoming.kickoff, legs:{home_win:{...leg,observed_at:now},away_win:{...leg,selection:'away_win',decimal_odds:1.9,observed_at:now}}};
  await page.route('**/api/v1/pipeline/betting-intel/nba', route => route.fulfill({json:{...data,predictions:[upcoming],devigged_odds:[freshMarket]}}));
  let soccerQueries = 0;
  await page.route('**/api/v1/pipeline/predictions/**', route => {soccerQueries++; return route.fulfill({json:{}});});
  await page.goto('/ai-picks/intelligence/nba/predictions');
  await expect(page.locator('.pd-forecast')).toContainText('60.0%');
  await expect(page.locator('.pd-forecast')).toContainText('Experimental candidate');
  const tabs = page.getByRole('navigation',{name:'Prediction views'});
  await tabs.getByRole('button',{name:'Bookmaker grid',exact:true}).click();
  await expect(page.locator('.bc-head.bc-brand')).toHaveAttribute('colspan','2');
  await expect(page.locator('.bc-table')).toContainText('52.0%');
  await expect(page.locator('.bc-outcome')).toHaveText(['1','2','1','2']);
  await page.getByRole('combobox',{name:'Comparison metric'}).selectOption('odds');
  await expect(page.locator('.bc-table')).toContainText('2.20');
  await tabs.getByRole('button',{name:'Settled performance',exact:true}).click();
  await expect(page.getByRole('heading',{name:'NBA measured performance.',exact:true})).toBeVisible();
  await expect(page.getByText('No eligible settled predictions match these filters.',{exact:true})).toBeVisible();
  await tabs.getByRole('button',{name:'Paper trials',exact:true}).click();
  await expect(page.getByRole('heading',{name:'No NBA paper trials connected.',exact:true})).toBeVisible();
  expect(soccerQueries).toBe(0);
});

test('intelligence hub retains six sport summaries',async({page})=>{
  await mock(page); await page.goto('/ai-picks/intelligence');
  await expect(page).toHaveURL(/\/ai-picks\/intelligence$/);
  await expect(page.locator('.bi-sport-card')).toHaveCount(6);
  await expect(page.locator('.bi-sport-card').filter({has:page.getByRole('heading',{name:'NBA intelligence',exact:true})})).toContainText('Experimental candidate');
  await page.getByRole('link',{name:'Explore NBA',exact:true}).click();
  await expect(page.getByRole('heading',{name:'NBA AI picks & predictions'})).toBeVisible();
  await expect(page.getByRole('table')).toContainText('Boston Celtics');
});

test('NBA tools show provenance, props and correct arbitrage units',async({page})=>{
  await mock(page); await page.goto('/ai-picks/intelligence/nba/predictions');
  await expect(page.locator('.pd-forecast')).toContainText('60.0%');
  await expect(page.locator('.pd-forecast')).toContainText('Experimental candidate');
  await page.goto('/ai-picks/intelligence/nba/devigged-odds');
  await expect(page.getByRole('table')).toContainText('52.0%');
  await page.getByRole('navigation',{name:'Intelligence tools'}).getByRole('link',{name:'EV bets'}).click();
  await expect(page.getByRole('table')).toContainText('target book excluded');
  await page.getByRole('navigation',{name:'Intelligence tools'}).getByRole('link',{name:'Player props'}).click();
  await expect(page.getByRole('table')).toContainText('Test Player');
  await expect(page.getByRole('table')).toContainText('20.5');
  await page.getByRole('navigation',{name:'Intelligence tools'}).getByRole('link',{name:'Arbitrage',exact:true}).click();
  await expect(page.getByRole('table')).toContainText('10.0% gross ROI');
  await expect(page.getByRole('table')).toContainText('Execution unverified');
  await expect(page.getByRole('table')).toContainText('50.00');
});

test('sport switch clears NBA rows and filters have honest empty states',async({page})=>{
  await mock(page); await page.goto('/ai-picks/intelligence/nba');
  await page.getByRole('searchbox').fill('does not exist');
  await expect(page.getByText('No results match your filter.',{exact:true})).toBeVisible();
  await page.getByRole('navigation',{name:'Intelligence sport'}).getByRole('link',{name:'WNBA',exact:true}).click();
  await expect(page).toHaveURL(/\/wnba\/summary$/);
  await expect(page.getByRole('heading',{name:'WNBA AI picks & predictions'})).toBeVisible();
  await expect(page.locator('.bi-workspace')).not.toContainText('Boston Celtics');
});

test('snapshot failure offers retry without fake picks',async({page})=>{
  await page.route('**/api/v1/pipeline/betting-intel/nba',route=>route.fulfill({status:503,json:{detail:'Intelligence snapshot unavailable.'}}));
  await page.goto('/ai-picks/intelligence/nba');
  await expect(page.getByRole('alert')).toContainText('Intelligence snapshot unavailable.',{timeout:20000});
  await expect(page.locator('.bi-workspace').getByRole('button',{name:'Retry',exact:true})).toBeVisible();
  await expect(page.getByRole('table')).toHaveCount(0);
});

test('sport home has a linked intelligence summary',async({page})=>{
  await mock(page); await page.goto('/sport/nba');
  await expect(page.getByRole('heading',{name:'NBA AI picks & predictions'})).toBeVisible();
  await expect(page.locator('.bi-inline-summary')).toContainText('Boston Celtics');
  await page.locator('.bi-inline-summary').getByRole('link',{name:'View intelligence'}).click();
  await expect(page).toHaveURL(/\/intelligence\/nba$/);
});

test('mobile intelligence navigation and table stay within viewport',async({page})=>{
  await page.setViewportSize({width:390,height:844}); await mock(page); await page.goto('/ai-picks/intelligence/nba/player-props');
  await expect(page.getByRole('table')).toContainText('Test Player');
  await page.getByRole('button',{name:/Open navigation|Open menu|Toggle menu/}).click();
  await expect(page.locator('.fh-mobile-menu').getByRole('link',{name:'Chat',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

for (const [sport, label] of sports) {
  test(`${label} has ordered Predictions and Best Picks tabs`, async ({page}) => {
    await mock(page);
    await page.goto(`/sport/${sport}`);
    const nav = page.getByRole('navigation', {name: `${label} navigation`, exact:true});
    await expect(nav.getByRole('link', {name:'Best Picks', exact:true})).toBeVisible();
    expect((await nav.getByRole('link').allTextContents()).slice(0,8)).toEqual(['Home','Scores','Schedule','Standings','Teams','Insights','Predictions','Best Picks']);
    await nav.getByRole('link', {name:'Predictions',exact:true}).click();
    await expect(page).toHaveURL(new RegExp(`/intelligence/${sport}/predictions$`));
    await expect(page.getByRole('heading',{name:/See the probabilities/})).toBeVisible();
    await expect(page.getByRole('navigation',{name:'Prediction views'}).getByRole('button')).toHaveText(['Upcoming fixtures','Bookmaker grid','Settled performance','Model lab','Paper trials']);
    await nav.getByRole('link', {name:'Best Picks',exact:true}).click();
    await expect(page).toHaveURL(new RegExp(`/intelligence/${sport}/best-picks$`));
    await expect(nav.getByRole('link', {name:'Best Picks',exact:true})).toHaveAttribute('aria-current','page');
    if (sport === 'nba') await expect(page.getByRole('table')).toContainText('Boston Celtics');
    else {
      await expect(page.getByText('No eligible best picks right now.', {exact:true})).toBeVisible();
      await expect(page.getByRole('table')).toHaveCount(0);
    }
  });
}

test('mobile active picks tab, refresh, history and sport switches preserve context', async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await mock(page);
  await page.goto('/ai-picks/intelligence/nba/best-picks');
  const active = page.locator('.fh-subnav [aria-current="page"]');
  await expect(active).toHaveText('Best Picks');
  await expect(active).toBeInViewport();
  await page.reload();
  await expect(active).toBeInViewport();
  await page.getByRole('navigation',{name:'Intelligence sport'}).getByRole('link',{name:'WNBA',exact:true}).click();
  await expect(page).toHaveURL(/\/wnba\/best-picks$/);
  await expect(page.getByRole('table')).toHaveCount(0);
  await page.goBack();
  await expect(page).toHaveURL(/\/nba\/best-picks$/);
  await expect(page.getByRole('table')).toContainText('Boston Celtics');
  await page.goForward();
  await expect(page).toHaveURL(/\/wnba\/best-picks$/);
  await expect(page.getByRole('table')).toHaveCount(0);
});

test('unknown sport or tool has a recoverable page',async({page})=>{
  await page.goto('/ai-picks/intelligence/toString');
  await expect(page.getByRole('heading',{name:'Intelligence view unavailable.'})).toBeVisible();
  await expect(page.getByRole('link',{name:'Choose a supported sport and tool'})).toBeVisible();
});
