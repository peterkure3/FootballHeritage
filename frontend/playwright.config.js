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
    baseURL: 'http://localhost:5173',  // Your Vite dev port
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    // Add more for cross-browser
  ],
  webServer: {
    command: 'npm run dev',  // Starts Vite automatically
    port: 5173,
    reuseExistingServer: !process.env.CI,
  },
});
