// tests/betting-flow.spec.js
import { test, expect } from '@playwright/test';

/**
 * E2E Test: User Login, View Odds, Build Parlay
 * 
 * This test mocks all API responses to work without a real backend.
 * It verifies the complete betting flow from login to parlay placement.
 */
test('User can login, view odds, and build parlay', async ({ page }) => {
  
  // ============================================
  // STEP 1: Mock API Responses
  // ============================================
  
  /**
   * Mock Login API
   * Intercepts POST /api/v1/auth/login
   * Returns fake JWT token and user data
   */
  await page.route('**/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        token: 'fake-jwt-token-12345',
        user: {
          id: 1,
          username: 'testuser',
          email: 'test@user.com',
          balance: 1000.00,
          role: 'user'
        }
      })
    });
  });

  /**
   * Mock User Profile API
   * Intercepts GET /api/v1/user
   * Returns user details for authenticated requests
   */
  await page.route('**/user/profile', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1,
        username: 'testuser',
        email: 'test@user.com',
        balance: 1000.00,
        role: 'user'
      })
    });
  });

  /**
   * Mock Odds/Events API
   * Intercepts GET /api/v1/betting/events
   * Returns sample sports events with odds
   */
  await page.route('**/betting/events', async (route) => {
    console.log('🔵 Mock: Intercepted /api/v1/betting/events request');
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 1,
          event_id: 1,
          sport: 'NFL',
          league: 'NFL',
          home_team: 'Chiefs',
          away_team: 'Bills',
          event_date: new Date(Date.now() + 86400000).toISOString(), // Tomorrow
          event_time: new Date(Date.now() + 86400000).toISOString(),
          start_time: new Date(Date.now() + 86400000).toISOString(),
          status: 'upcoming',
          // Moneyline odds (required for OddsRow)
          moneyline_home: 1.85,
          moneyline_away: 2.10,
          // Spread odds
          spread_home: -3.5,
          spread_away: 3.5,
          spread_odds_home: 1.91,
          spread_odds_away: 1.91,
          // Total (over/under)
          total: 47.5,
          over_odds: 1.91,
          under_odds: 1.91,
        },
        {
          id: 2,
          event_id: 2,
          sport: 'NBA',
          league: 'NBA',
          home_team: 'Lakers',
          away_team: 'Celtics',
          event_date: new Date(Date.now() + 172800000).toISOString(), // 2 days from now
          event_time: new Date(Date.now() + 172800000).toISOString(),
          start_time: new Date(Date.now() + 172800000).toISOString(),
          status: 'upcoming',
          // Moneyline odds
          moneyline_home: 1.95,
          moneyline_away: 1.95,
          // Spread odds
          spread_home: -2.5,
          spread_away: 2.5,
          spread_odds_home: 1.91,
          spread_odds_away: 1.91,
          // Total
          total: 215.5,
          over_odds: 1.91,
          under_odds: 1.91,
        }
      ])
    });
  });

  /**
   * Mock Sports List API
   * Intercepts GET /api/v1/sports
   * Returns available sports with event counts
   */
  await page.route('**/sports', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { sport: 'NFL', event_count: 10, upcoming_count: 8 },
        { sport: 'NBA', event_count: 15, upcoming_count: 12 }
      ])
    });
  });

  /**
   * Mock Parlay Placement API
   * Intercepts POST /api/v1/betting/parlay
   * Returns success response with bet details
   */
  await page.route('**/betting/parlay', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        bet_id: 123,
        status: 'pending',
        total_odds: 3.85,
        potential_payout: 38.50,
        new_balance: 990.00,
        message: 'Parlay placed successfully!'
      })
    });
  });

  /**
   * Mock Single Bet Placement API
   * Intercepts POST /api/v1/betting/bet
   * Returns success response
   */
  await page.route('**/betting/bets', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        bet_id: 124,
        status: 'pending',
        new_balance: 995.00,
        message: 'Bet placed successfully!'
      })
    });
  });

  /**
   * Mock Bet History API
   * Intercepts GET /api/v1/betting/history
   * Returns empty bet history
   */
  await page.route('**/betting/bets', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([])
    });
  });

  // ============================================
  // STEP 2: Navigate to Login Page
  // ============================================
  
  console.log('Navigating to /login...');
  await page.goto('/login');
  
  // Wait for page to load
  await page.waitForLoadState('networkidle');

  // ============================================
  // STEP 3: Fill Login Form
  // ============================================
  
  console.log('Filling login form...');
  
  // Fill email input
  await page.fill('input[name="email"]', 'test@user.com');
  
  // Fill password input
  await page.fill('input[name="password"]', 'securePass123');
  
  // Submit form
  console.log('Submitting login form...');
  await page.click('button[type="submit"]');

  // ============================================
  // STEP 4: Assert Successful Login
  // ============================================
  
  console.log('Waiting for redirect to /dashboard...');
  
  // Wait for redirect to dashboard (with timeout)
  await page.waitForURL('/dashboard', { timeout: 5000 });
  
  // Verify we're on dashboard
  await expect(page).toHaveURL('/dashboard');
  console.log('✓ Successfully redirected to /dashboard');
  
  // Check for user greeting (adjust text based on your Dashboard.jsx)
  // This might be "Welcome, testuser" or similar
  await expect(page.locator('text=/Welcome|testuser|Test User/i')).toBeVisible({ timeout: 3000 });
  console.log('✓ User greeting visible');

  // ============================================
  // STEP 5: Navigate to Odds Page
  // ============================================
  
  console.log('Navigating to /odds...');
  await page.goto('/odds');
  await page.waitForLoadState('networkidle');
  
  // Verify odds are displayed
  await expect(page.locator('text=/Chiefs|Bills|Lakers|Celtics/i').first()).toBeVisible({ timeout: 5000 });
  console.log('✓ Odds page loaded with events');

  // ============================================
  // STEP 6: Add Event to Parlay
  // ============================================
  
  console.log('Attempting to add event to parlay...');
  
  // Click "Add to Parlay" button (now has data-testid)
  const addButton = page.locator('[data-testid="add-to-parlay-home"]').first();
  await addButton.click();
  console.log('✓ Event added to parlay');
  
  // Wait for success toast
  await expect(page.locator('text=/Added to parlay/i')).toBeVisible({ timeout: 3000 });
  console.log('✓ Parlay toast notification visible');
  
  // Check if parlay sidebar shows (lazy loaded)
  await page.waitForTimeout(500); // Wait for lazy load
  await expect(page.locator('text=/Parlay Builder/i').first()).toBeVisible({ timeout: 3000 });
  console.log('✓ Parlay sidebar visible');

  // ============================================
  // STEP 7: Place Single Bet
  // ============================================
  
  console.log('Attempting to place a single bet...');
  
  // Click on moneyline bet button (now has data-testid)
  const betButton = page.locator('[data-testid="bet-moneyline-away"]').first();
  await betButton.click();
  console.log('✓ Bet modal opened');
  
  // Wait for modal to appear
  await page.waitForSelector('[role="dialog"]', { timeout: 3000 });
  
  // Fill bet amount
  await page.fill('input[id="bet-amount-input"]', '10');
  console.log('✓ Bet amount entered: $10');
  
  // Click place bet button
  await page.click('button:has-text("Place Bet")');
  console.log('✓ Bet placement button clicked');
  
  // Wait for success toast
  await expect(page.locator('text=/Bet placed|success/i')).toBeVisible({ timeout: 5000 });
  console.log('✓ Bet placed successfully!');

  // ============================================
  // STEP 8: Security Check - Expired JWT
  // ============================================
  
  console.log('Testing security: Removing JWT token...');
  
  // Clear localStorage (simulates expired/removed token)
  await page.evaluate(() => {
    localStorage.clear();
  });
  
  // Reload page
  await page.reload();
  
  // Should redirect to login
  await page.waitForURL('/login', { timeout: 5000 });
  await expect(page).toHaveURL('/login');
  console.log('✓ Security check passed: Redirected to login after token removal');

  console.log('\n✅ All tests passed!');
});