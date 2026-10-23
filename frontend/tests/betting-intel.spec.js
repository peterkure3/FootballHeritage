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

async function mock(page) {
  await page.route('**/api/v1/me/features', route => route.fulfill({ json: featureAccess }));
  await page.route('**/api/v1/pipeline/betting-intel', route => route.fulfill({json:{snapshot_at:data.snapshot_at,snapshot_status:'current',source_errors:[],
    sports:sports.map(([sport,label])=>({sport,label,summary:sport==='nba'?summary:{},top_pick:sport==='nba'?pick:null,next_prediction:sport==='nba'?game:null}))}}));
  await page.route('**/api/v1/pipeline/betting-intel/*', route => {
    const sport = new URL(route.request().url()).pathname.split('/').pop();
    return route.fulfill({json:sport==='nba'?data:{...data,sport,label:'WNBA',summary:{},ai_picks:[],predictions:[],ev_bets:[],arbitrage:[],devigged_odds:[],player_props:[]}});
  });
}

test('AI Picks desktop menu opens intelligence and six sport summaries',async({page})=>{
  await mock(page); await page.goto('/app');
  await page.getByRole('button',{name:'AI Picks',exact:true}).click();
  await page.getByRole('link',{name:'Intelligence',exact:true}).click();
  await expect(page).toHaveURL(/\/ai-picks\/intelligence$/);
  await expect(page.locator('.bi-sport-card')).toHaveCount(6);
  await expect(page.locator('.bi-sport-card').filter({has:page.getByRole('heading',{name:'NBA intelligence',exact:true})})).toContainText('Experimental candidate');
  await page.getByRole('link',{name:'Explore NBA',exact:true}).click();
  await expect(page.getByRole('heading',{name:'NBA AI picks & predictions'})).toBeVisible();
  await expect(page.getByRole('table')).toContainText('Boston Celtics');
});

test('NBA tools show provenance, props and correct arbitrage units',async({page})=>{
  await mock(page); await page.goto('/ai-picks/intelligence/nba/predictions');
  await expect(page.getByRole('table')).toContainText('60.0%');
  await expect(page.getByRole('table')).toContainText('Experimental candidate');
  await page.getByRole('navigation',{name:'Intelligence tools'}).getByRole('link',{name:'De-vigged odds'}).click();
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
  await expect(page).toHaveURL(/\/wnba$/);
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
  await page.locator('.fh-mobile-menu').getByText('AI Picks',{exact:true}).click();
  await expect(page.locator('.fh-mobile-menu').getByRole('link',{name:'Intelligence',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

test('unknown sport or tool has a recoverable page',async({page})=>{
  await page.goto('/ai-picks/intelligence/toString');
  await expect(page.getByRole('heading',{name:'Intelligence view unavailable.'})).toBeVisible();
  await expect(page.getByRole('link',{name:'Choose a supported sport and tool'})).toBeVisible();
});
