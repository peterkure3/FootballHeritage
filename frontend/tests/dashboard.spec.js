import { defaultApiFixture } from './feature-fixture.js';
import { test, expect } from "@playwright/test";
const user = {
  id: "dashboard-test",
  first_name: "Peter",
  email: "peter@example.com",
  balance: "1250.50",
};
const bets = [
  {
    id: 1,
    event_name: "Arsenal vs Chelsea",
    status: "won",
    amount: 20,
    odds: 2.1,
    placed_at: "2026-10-20T12:00:00Z",
  },
  {
    id: 2,
    event_name: "Liverpool vs Everton",
    status: "pending",
    amount: 15,
    odds: 1.8,
    placed_at: "2026-10-22T12:00:00Z",
  },
  {
    id: 3,
    event_name: "Milan vs Roma",
    status: "settled_lost",
    amount: 10,
    odds: 2,
    placed_at: "2026-10-21T12:00:00Z",
  },
  {
    id: 4,
    event_name: "Paris vs Lyon",
    status: "cancelled",
    amount: 5,
    odds: 3,
    placed_at: "2026-10-19T12:00:00Z",
  },
];
test.beforeEach(async ({ page }) => {
  await page.addInitScript((data) => {
    sessionStorage.setItem("token", "test-only-token");
    sessionStorage.setItem("betting_user_data", JSON.stringify(data));
  }, user);
  await page.route("**/api/v1/**", defaultApiFixture);
  await page.route("**/user/profile", (route) => route.fulfill({ json: user }));
  await page.route("**/betting/bets", (route) => route.fulfill({ json: bets }));
});
for (const width of [1440, 900, 390]) {
  test(`dashboard activity and responsive layout at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { name: "Welcome back, Peter." }),
    ).toBeVisible();
    await expect(page.locator(".ud-wallet > strong")).toHaveText("$1,250.50");
    await expect(
      page.locator(".ud-metric").filter({ hasText: "Win rate" }),
    ).toContainText("50%");
    await expect(
      page.locator(".ud-metric").filter({ hasText: "Win rate" }),
    ).toContainText("1 won · 1 lost");
    await expect(page.locator(".ud-bet-row")).toHaveCount(4);
    await expect(page.locator(".ud-bet-row").first()).toContainText(
      "Liverpool",
    );
    await page.getByRole("button", { name: "Pending", exact: true }).click();
    await expect(page.locator(".ud-bet-row")).toHaveCount(1);
    await page.getByRole("button", { name: "Settled", exact: true }).click();
    await expect(page.locator(".ud-bet-row")).toHaveCount(2);
    await page.getByRole("button", { name: "All bets", exact: true }).click();
    await expect(
      page.getByRole("link", { name: /AI picks Explore/ }),
    ).toHaveAttribute("href", "/ai-picks");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `test-results/dashboard-${width}.png`,
      fullPage: true,
    });
  });
}
test("empty history keeps settled win rate unavailable", async ({ page }) => {
  await page.route("**/betting/bets", (route) => route.fulfill({ json: [] }));
  await page.goto("/dashboard");
  await expect(
    page.getByRole("heading", { name: "Your story starts here" }),
  ).toBeVisible();
  await expect(
    page
      .locator(".ud-metric")
      .filter({ hasText: "Win rate" })
      .locator("strong"),
  ).toHaveText("—");
});
test("failed history offers retry without displaying false zero metrics", async ({
  page,
}) => {
  let fail = true;
  await page.route("**/betting/bets", (route) =>
    fail
      ? route.fulfill({ status: 500, json: { message: "Unavailable" } })
      : route.fulfill({ json: bets }),
  );
  await page.goto("/dashboard");
  await expect(
    page.getByRole("button", { name: "Retry bet history" }),
  ).toBeVisible({ timeout: 15000 });
  await expect(page.locator(".ud-metric").first().locator("strong")).toHaveText(
    "—",
  );
  await expect(
    page.getByRole("heading", { name: "Your story starts here" }),
  ).toHaveCount(0);
  fail = false;
  await page.getByRole("button", { name: "Retry bet history" }).click();
  await expect(page.locator(".ud-bet-row")).toHaveCount(4);
});
test("loading history has a distinct state", async ({ page }) => {
  await page.route("**/betting/bets", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1800));
    await route.fulfill({ json: bets });
  });
  await page.goto("/dashboard");
  await expect(
    page.locator(".user-dashboard").getByRole("status"),
  ).toContainText("Loading your betting activity");
  await expect(page.locator(".ud-bet-row")).toHaveCount(4);
});
