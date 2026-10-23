import { chromium } from '@playwright/test';
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  page.on('pageerror', (error) => console.log('PAGE ERROR', error.message));
  page.on('response', (response) => {
    if (response.url().includes('sport-models')) console.log('API', response.status(), response.url());
  });
  const user = { id: 'model-lab-check', first_name: 'Test', last_name: 'User', email: 'test@example.com', balance: 0 };
  await page.addInitScript((user) => {
    globalThis.sessionStorage.setItem('token', 'test-only-token');
    globalThis.sessionStorage.setItem('betting_user_data', JSON.stringify(user));
  }, user);
  await page.route('**/user/profile', (route) => route.fulfill({ json: user }));
  await page.goto('http://localhost:5173/predictions?tab=models');
  await page.getByRole('button', { name: 'Model lab', exact: true }).click();
  const model = page.getByLabel('Sport / candidate');
  await model.waitFor();
  const initialHome = page.getByRole('combobox', { name: 'Home team', exact: true });
  await initialHome.fill('chief');
  await page.getByRole('option', { name: 'Kansas City Chiefs', exact: true }).click();
  if (await initialHome.inputValue() !== 'Kansas City Chiefs') throw new Error('Home team selection failed');
  const initialAway = page.getByRole('combobox', { name: 'Away team', exact: true });
  await initialAway.fill('bills');
  await initialAway.press('ArrowDown');
  await initialAway.press('Enter');
  if (await initialAway.inputValue() !== 'Buffalo Bills') throw new Error('Away team selection failed');
  console.log('LIVE DEFAULT MODEL: home mouse selection and away keyboard selection passed');
  const values = await model.locator('option').evaluateAll((options) => options.map((option) => option.value).filter(Boolean));
  console.log('INITIAL', await page.locator('.pd-preview-form').innerText());
  for (const value of values) {
    await model.selectOption(value);
    const home = page.getByRole('combobox', { name: 'Home team', exact: true });
    await home.waitFor();
    try {
      await home.fill('a', { timeout: 25000 });
      console.log('MODEL', value, 'INPUT', await home.inputValue(), 'OPTIONS', await page.getByRole('option').count());
      await home.press('Escape');
    } catch (error) {
      console.log('FAILED', value, error.message, await page.locator('.pd-preview-form').innerText());
    }
  }
  await page.screenshot({ path: '../stages/03-build/output/model-lab-live-20261017.png', fullPage: true });
} finally { await browser.close(); }
