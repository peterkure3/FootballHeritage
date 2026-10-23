import assert from 'node:assert/strict';
import { chromium, expect } from '@playwright/test';
import { createServer } from 'vite';

const server=await createServer({server:{host:'127.0.0.1',port:5189,strictPort:true},logLevel:'error'});
let browser;
try {
  await server.listen();
  const response=await fetch('http://127.0.0.1:5567/api/v1/betting-intel/nba');
  assert(response.ok);
  const data=await response.json();
  assert(data.predictions.length>0);
  browser=await chromium.launch();
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  await page.route('**/api/v1/betting-intel**',async route=>{
    const url=new URL(route.request().url());
    const upstream=await route.fetch({url:`http://127.0.0.1:5567${url.pathname}${url.search}`});
    await route.fulfill({response:upstream});
  });
  await page.goto('http://127.0.0.1:5189/ai-picks/intelligence/nba/predictions');
  await expect(page.getByRole('table')).toContainText(data.predictions[0].home_team);
  await expect(page.getByRole('table')).toContainText('Experimental candidate');
  await page.screenshot({path:'../stages/03-build/output/betting-intel-desktop-20261020.png'});
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('table')).toBeVisible();
  assert(await page.evaluate(()=>globalThis.document.documentElement.scrollWidth<=globalThis.innerWidth));
  await page.screenshot({path:'../stages/03-build/output/betting-intel-mobile-20261020.png'});
  console.log(JSON.stringify({real_nba_predictions:data.predictions.length,checks:'Desktop and mobile rendering, candidate labels and viewport bounds passed'}));
} finally {
  await browser?.close();
  await server.close();
}
