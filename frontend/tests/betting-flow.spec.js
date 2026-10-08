import { test, expect } from "@playwright/test";

// Explicit test-only API fixtures. No mock data is shipped in the application.
const user = {
  id: "test-user",
  first_name: "Test",
  last_name: "User",
  email: "test@user.com",
  balance: 1000,
};
const events = ["NFL", "NBA"].map((sport, index) => ({
  id: index + 1,
  event_id: index + 1,
  sport,
  league: sport,
  home_team: index ? "Lakers" : "Chiefs",
  away_team: index ? "Celtics" : "Bills",
  event_date: new Date(Date.now() + 86400000 * (index + 1)).toISOString(),
  status: "upcoming",
  moneyline_home: 1.85,
  moneyline_away: 2.1,
  spread_home: -3.5,
  spread_away: 3.5,
  spread_odds_home: 1.91,
  spread_odds_away: 1.91,
  total: 47.5,
  over_odds: 1.91,
  under_odds: 1.91,
}));
async function mockServices(page) {
  await page.route("**/api/v1/**", (route) => route.fulfill({ json: [] }));
  await page.route("**/auth/login", (route) =>
    route.fulfill({ json: { token: "test-only-token", user } }),
  );
  await page.route("**/user/profile", (route) => route.fulfill({ json: user }));
  await page.route("**/betting/events", (route) =>
    route.fulfill({ json: events }),
  );
  await page.route("**/sports", (route) =>
    route.fulfill({
      json: [
        { sport: "NFL", event_count: 1 },
        { sport: "NBA", event_count: 1 },
      ],
    }),
  );
}
async function login(page) {
  await page.goto("/login");
  await page.locator('input[name="email"]').fill(user.email);
  await page.locator('input[name="password"]').fill("securePass123");
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page).toHaveURL("/dashboard");
  await expect(
    page.getByRole("heading", { name: /Welcome back/ }),
  ).toBeVisible();
}
test("existing login, odds, parlay builder and single betting flow", async ({
  page,
}) => {
  // This multi-screen scenario includes login, a lazy sidebar and a full refresh.
  // Firefox's cold module load on Windows can consume most of the default 30s.
  test.setTimeout(60000);
  await mockServices(page);
  let placed = null;
  await page.route("**/betting/bets", (route) => {
    if (route.request().method() !== "POST") return route.fulfill({ json: [] });
    placed = route.request().postDataJSON();
    return route.fulfill({
      json: { bet_id: 124, status: "pending", new_balance: 990 },
    });
  });
  await login(page);
  await page.goto("/odds");
  await expect(
    page.getByRole("heading", { name: "Chiefs vs Bills" }),
  ).toBeVisible();
  const oddsButton = page.getByTestId("bet-moneyline-away").first();
  expect(
    await oddsButton.evaluate((element) => getComputedStyle(element).color),
  ).toBe("rgb(32, 39, 35)");
  await page.getByTestId("add-to-parlay-home").first().click();
  await expect(page.getByText(/Added to parlay/i)).toBeVisible();
  await expect(
    page.getByText("Parlay Builder", { exact: true }).first(),
  ).toBeVisible();
  await page.getByTestId("bet-moneyline-away").first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.locator("#bet-amount-input").fill("10");
  await dialog.getByRole("button", { name: /Place bet/i }).click();
  await expect(page.getByText(/Bet placed!/i)).toBeVisible();
  expect(placed).toMatchObject({ amount: 10, odds: 2.1 });
  await page.evaluate(() => sessionStorage.clear());
  await page.reload();
  await expect(page).toHaveURL("/login");
});
test("wallet remains reachable and deposit uses existing handler", async ({
  page,
}) => {
  await mockServices(page);
  let deposited = null;
  await page.route("**/wallet/deposit", (route) => {
    deposited = route.request().postDataJSON();
    return route.fulfill({ json: { amount: 20, new_balance: 1020 } });
  });
  await login(page);
  await page.getByRole("button", { name: "Account for Test" }).click();
  await page
    .locator("#menu-account")
    .getByRole("button", { name: "Wallet", exact: true })
    .click();
  const wallet = page.getByRole("dialog", { name: "Wallet", exact: true });
  await expect(wallet).toBeVisible();
  await wallet.locator("input").fill("20");
  await wallet.locator('button[type="submit"]').click();
  await expect(page.getByText(/Deposited.*successfully/i)).toBeVisible();
  expect(deposited).toEqual({ amount: 20 });
  await wallet.press("Escape");
  await expect(wallet).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Account for Test" }),
  ).toBeFocused();
});
