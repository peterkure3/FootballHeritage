import { defaultApiFixture } from './feature-fixture.js';
import { test, expect } from "@playwright/test";

// Explicitly mocked provider results for UI tests.
const michigan = {
  id: "130",
  name: "Michigan",
  full_name: "Michigan Wolverines",
  seed: 1,
  region: "Midwest",
  score: 69,
  winner: true,
  record: "37-3",
};
const uconn = {
  id: "41",
  name: "UConn",
  full_name: "UConn Huskies",
  seed: 2,
  region: "East",
  score: 63,
  winner: false,
};
const duke = {
  id: "150",
  name: "Duke",
  full_name: "Duke Blue Devils",
  seed: 1,
  region: "East",
  score: 70,
  winner: false,
};
const bracket = {
  season: 2026,
  fetched_at: "2026-10-19T09:00:00Z",
  source: "ESPN",
  status: "complete",
  champion: michigan,
  official_bracket_url: "https://www.ncaa.com/brackets/basketball-men/d1/2026",
  rounds: ["Elite Eight", "Championship"],
  teams: [michigan, uconn, duke],
  games: [
    {
      id: "regional",
      date: "2026-03-29T20:00Z",
      round: "Elite Eight",
      region: "East",
      status: "finished",
      status_detail: "Final",
      teams: [{ ...uconn, winner: true }, duke],
    },
    {
      id: "final",
      date: "2026-04-07T00:50Z",
      round: "Championship",
      region: null,
      status: "finished",
      status_detail: "Final",
      teams: [michigan, uconn],
    },
  ],
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem("token", "test-only-token");
    sessionStorage.setItem(
      "betting_user_data",
      JSON.stringify({ id: "test-user", email: "test@example.com" }),
    );
  });
  await page.route("**/api/v1/**", defaultApiFixture);
  await page.route("**/user/profile", (route) =>
    route.fulfill({ json: { id: "test-user", email: "test@example.com" } }),
  );
  await page.route("**/ncaab/bracket?*", (route) =>
    route.fulfill({ json: bracket }),
  );
});

for (const width of [1440, 390]) {
  test(`NCAAB opens the actual tournament and filters sourced teams at ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/app");
    if (width === 390) {
      await page.getByRole("button", { name: "Open navigation" }).click();
      await page
        .locator("#mobile-navigation summary")
        .filter({ hasText: /^NCAAB$/ })
        .click();
      await page
        .locator("#mobile-navigation")
        .getByRole("link", { name: "March Madness", exact: true })
        .click();
    } else {
      await page
        .getByRole("navigation", { name: "Sports", exact: true })
        .getByRole("link", { name: "NCAAB", exact: true })
        .hover();
      await page
        .locator("#menu-ncaab")
        .getByRole("link", { name: "March Madness", exact: true })
        .click();
    }
    await expect(page).toHaveURL("/college/bracket");
    await expect(
      page.getByRole("heading", { name: "March Madness", exact: true }),
    ).toBeVisible();
    await expect(page.locator(".mm-champion")).toContainText("Michigan");
    await expect(page.locator(".mm-game")).toHaveCount(2);
    await expect(page.locator(".fh-subnav a[aria-current='page']")).toHaveText(
      "March Madness",
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: testInfo.outputPath(`march-madness-${width}.png`),
      fullPage: true,
    });
    await page.getByLabel("Region", { exact: true }).selectOption("East");
    await expect(page.locator(".mm-game")).toHaveCount(1);
    await page
      .getByLabel("Round", { exact: true })
      .selectOption("Championship");
    await expect(page.getByLabel("Region", { exact: true })).toHaveValue("");
    await expect(page.locator(".mm-game")).toContainText("69");
    await page
      .getByRole("button", { name: "Tournament teams", exact: true })
      .click();
    await expect(page.locator(".mm-team-card")).toHaveCount(3);
    await page.getByLabel("Find a team", { exact: true }).fill("Michigan");
    await expect(page.locator(".mm-team-card")).toHaveCount(1);
    await page.getByRole("button", { name: "View tournament games" }).click();
    await expect(page.locator(".mm-game")).toHaveCount(1);
    await page
      .getByRole("button", { name: "Clear filters", exact: true })
      .click();
    await expect(page.locator(".mm-game")).toHaveCount(2);
    await page
      .getByLabel("Game status", { exact: true })
      .selectOption("upcoming");
    await expect(
      page.getByRole("heading", { name: "No games match these filters." }),
    ).toBeVisible();
  });
}

test("tournament handles unavailable data and preserves stale provenance on refresh", async ({
  page,
}) => {
  await page.route("**/ncaab/bracket?*", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Tournament feed unavailable" },
    }),
  );
  await page.goto("/college/bracket");
  await expect(page.getByRole("alert")).toContainText(
    "Tournament feed unavailable",
  );
  await page.route("**/ncaab/bracket?*", (route) =>
    route.fulfill({ json: bracket }),
  );
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.locator(".mm-game")).toHaveCount(2);
  const source = await page.locator(".mm-source").textContent();
  await page.route("**/ncaab/bracket?*", (route) =>
    route.fulfill({
      json: {
        ...bracket,
        stale: true,
        warning:
          "Refresh failed. Showing the last successful tournament snapshot.",
      },
    }),
  );
  await page.getByRole("button", { name: "Refresh data", exact: true }).click();
  await expect(page.locator(".mm-notice")).toContainText("Refresh failed");
  await expect(page.locator(".mm-source")).toHaveText(source);
});
