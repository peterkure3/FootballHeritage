import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: 'staging-acceptance.spec.js',
  workers: 1,
  retries: 0,
  reporter: 'line',
  timeout: 60000,
  use: {
    ...devices['Desktop Chrome'],
    baseURL: 'https://staging.footballheritage.test:18443',
    ignoreHTTPSErrors: true, // Local test certificate only; never a hosted policy.
    trace: 'off',
    screenshot: 'off',
    launchOptions: { args: ['--host-resolver-rules=MAP staging.footballheritage.test 127.0.0.1'] },
  },
});
