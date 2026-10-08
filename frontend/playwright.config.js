// @ts-check
// playwright.config.js
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',  // Folder for your tests
  fullyParallel: true,  // For performance
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',  // Nice reports
  use: {
    trace: 'on-first-retry',  // Debug failures
    baseURL: 'http://127.0.0.1:5187', // Isolated test server, separate from a user's dev session.
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    // Add more for cross-browser
  ],
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5187 --strictPort',
    port: 5187,
    reuseExistingServer: false,
  },
});
