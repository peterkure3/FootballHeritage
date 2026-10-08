import { test, expect } from "@playwright/test";

// All upstream data in this suite is explicitly mocked test data, never app fallback data.
const fixtures = [
  {
    match_id: 1,
    competition: "Premier League",
    date: "2026-10-07T18:00:00Z",
    home_team: "Arsenal",
    away_team: "Chelsea",
    home_score: 2,
    away_score: 1,
    status: "finished",
  },
];
const user = {
  id: "test-user",
  first_name: "Test",
  last_name: "User",
  email: "test@example.com",
  balance: 1000,
};
async function authenticate(page) {
  await page.addInitScript((userData) => {
    if (!sessionStorage.getItem("test-initialized")) {
      sessionStorage.setItem("token", "test-only-token");
      sessionStorage.setItem("betting_user_data", JSON.stringify(userData));
      sessionStorage.setItem("test-initialized", "true");
    }
  }, user);
}
test("NBA fixtures use canonical basketball data without including other leagues", async ({
  page,
}) => {
  await authenticate(page);
  await page.route("**/betting/events", (route) =>
    route.fulfill({
      json: [
        {
          id: 10,
          sport: "basketball",
          league: "NBA",
          home_team: "Lakers",
          away_team: "Celtics",
          event_date: "2026-10-08T18:00:00Z",
        },
        {
          id: 11,
          sport: "basketball",
          league: "EuroLeague",
          home_team: "Other club",
          away_team: "Another club",
          event_date: "2026-10-08T18:00:00Z",
        },
        {
          sport: "basketball",
          league: "NBA",
          home_team: "Missing fixture ID",
          away_team: "Unknown club",
        },
      ],
    }),
  );
  await page.goto("/sport/nba/scores");
  await expect(page.locator(".fh-match")).toHaveCount(1);
  await expect(page.locator(".fh-match")).toContainText("Lakers");
  await expect(page.locator(".fh-match")).toHaveAttribute("href", /match=10/);
});

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/**", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/matches?*", (route) =>
    route.fulfill({ json: fixtures }),
  );
  await page.route("**/user/profile", (route) => route.fulfill({ json: user }));
});

test("unknown routes use the shared design and return home", async ({
  page,
}) => {
  await page.goto("/unknown-page");
  await expect(page.getByRole("heading", { name: "404" })).toBeVisible();
  await page.getByRole("link", { name: "Return home", exact: true }).click();
  await expect(page).toHaveURL("/");
  await page.goto("/sport/football/unknown-section");
  await expect(
    page.getByRole("heading", { name: "Page not found." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Return to sport home" }).click();
  await expect(page).toHaveURL("/sport/football");
});
test("homepage, sport selection, direct links and history", async ({
  page,
}) => {
  await page.goto("/app");
  await expect(
    page.getByRole("navigation", { name: "Football navigation" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("heading", {
      name: "A world of sport. A deeper perspective.",
    }),
  ).toBeVisible();
  const football = page
    .getByRole("navigation", { name: "Sports", exact: true })
    .getByRole("link", { name: "Football", exact: true });
  await football.click();
  await expect(page).toHaveURL(/\/sport\/football$/);
  const subnav = page.getByRole("navigation", { name: "Football navigation" });
  await subnav.getByRole("link", { name: "Scores", exact: true }).click();
  await expect(
    page.getByRole("link", { name: /Arsenal.*Chelsea/ }).last(),
  ).toBeVisible();
  await page.reload();
  await expect(
    subnav.getByRole("link", { name: "Scores", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await page
    .getByRole("link", { name: "FootballHeritage homepage", exact: true })
    .click();
  await expect(subnav).toHaveCount(0);
  await page.goBack();
  await expect(subnav).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL("/app");
});
test("sport mega menu retains hover and supports focus and Escape", async ({
  page,
}) => {
  await page.goto("/app");
  const football = page
    .getByRole("navigation", { name: "Sports", exact: true })
    .getByRole("link", { name: "Football", exact: true });
  await football.hover();
  const team = page
    .locator("#menu-football")
    .getByRole("link", { name: "Arsenal", exact: true });
  await team.hover();
  await expect(team).toBeVisible();
  await football.focus();
  await page.keyboard.press("Tab");
  await expect(page.locator("#menu-football")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(football).toHaveAttribute("aria-expanded", "false");
  await expect(football).toBeFocused();
});
test("guest and authenticated account menus use real store state", async ({
  page,
}) => {
  await page.goto("/app");
  const account = page.getByRole("button", { name: "Account menu" });
  await account.click();
  await expect(
    page
      .locator("#menu-account")
      .getByRole("link", { name: "Log in", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator("#menu-account")
      .getByRole("link", { name: "Create account", exact: true }),
  ).toBeVisible();
  await authenticate(page);
  await page.reload();
  await page.getByRole("button", { name: "Account for Test" }).hover();
  await expect(
    page
      .locator("#menu-account")
      .getByRole("link", { name: "Profile", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator("#menu-account")
      .getByRole("link", { name: "Log in", exact: true }),
  ).toHaveCount(0);
  await page
    .locator("#menu-account")
    .getByRole("button", { name: "Log out", exact: true })
    .click();
  await expect(page).toHaveURL("/login");
});
test("AI Picks menu opens by focus and routes directly", async ({ page }) => {
  await page.goto("/app");
  const ai = page.getByRole("button", { name: "AI Picks", exact: true });
  await ai.focus();
  await page
    .locator("#menu-ai")
    .getByRole("link", { name: "Chat", exact: true })
    .click();
  await expect(page).toHaveURL("/ai-picks/chat");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "AI Picks Chat", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Log in to use AI Picks." }),
  ).toBeVisible();
});
test("mobile accordions provide sports, AI and account routes", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/app");
  await page.getByRole("button", { name: "Open navigation" }).click();
  const mobile = page.getByRole("navigation", { name: "Mobile navigation" });
  await mobile
    .locator("summary")
    .filter({ hasText: /^Football$/ })
    .click();
  await mobile
    .getByRole("link", { name: "Schedule", exact: true })
    .first()
    .click();
  await expect(page).toHaveURL("/sport/football/schedule");
  await expect(mobile).toHaveCount(0);
  await page.getByRole("button", { name: "Open navigation" }).click();
  await mobile
    .locator("summary")
    .filter({ hasText: /^AI Picks$/ })
    .click();
  await mobile.getByRole("link", { name: "Best picks", exact: true }).click();
  await expect(page).toHaveURL("/ai-picks");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await mobile
    .locator("summary")
    .filter({ hasText: /^Account$/ })
    .click();
  await expect(
    mobile.getByRole("link", { name: "Create account", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeFocused();
});
test("match direct link opens accessible dialog and Escape restores focus", async ({
  page,
}) => {
  await page.goto("/sport/football/scores?match=1");
  await expect(
    page.getByRole("dialog", { name: "Arsenal versus Chelsea" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const match = page.getByRole("link", { name: /Arsenal.*Chelsea/ }).last();
  await match.click();
  await page.keyboard.press("Escape");
  await expect(match).toBeFocused();
});
test("scores show errors, retry, empty state and no sample scores", async ({
  page,
}) => {
  await page.route("**/api/v1/matches?*", (route) =>
    route.fulfill({
      status: 503,
      json: { error: "Test upstream unavailable" },
    }),
  );
  await page.goto("/sport/football/scores");
  await expect(
    page.getByRole("heading", { name: "Data unavailable" }),
  ).toBeVisible();
  await page.route("**/api/v1/matches?*", (route) =>
    route.fulfill({ json: [] }),
  );
  await page
    .locator(".fh-section")
    .getByRole("button", { name: "Retry", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "No fixtures match these filters." }),
  ).toBeVisible();
  await expect(page.locator(".fh-match")).toHaveCount(0);
});
test("saved stories remain account-scoped through refresh", async ({
  page,
}) => {
  await authenticate(page);
  await page.goto("/app");
  await page
    .getByRole("button", {
      name: "Save Under the lights. Beyond the ordinary.",
      exact: true,
    })
    .click();
  await page.goto("/saved");
  await page.reload();
  await expect(
    page
      .locator(".fh-content")
      .getByRole("heading", { name: "Under the lights. Beyond the ordinary." }),
  ).toBeVisible();
  await page.evaluate(() =>
    sessionStorage.setItem(
      "betting_user_data",
      JSON.stringify({ id: "different-user", email: "other@example.com" }),
    ),
  );
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "No saved stories yet." }),
  ).toBeVisible();
});
test("AI generation preserves API fields and exposes unavailable model", async ({
  page,
}) => {
  await authenticate(page);
  await page.route("**/ai-picks/generate", (route) =>
    route.fulfill({
      json: {
        id: "test-run",
        generated_at: "2026-10-07T12:00:00Z",
        picks: [
          {
            match_id: 1,
            home_team: "Arsenal",
            away_team: "Chelsea",
            selection: "Home Win",
            competition: "Premier League",
            model_prob: 0.6,
            implied_prob: 0.5,
            edge_pct: 10,
            expected_value: 20,
            decimal_odds: 2,
            model_version: "test-model",
          },
        ],
      },
    }),
  );
  await page.goto("/ai-picks");
  await page.getByRole("button", { name: "Generate / refresh" }).click();
  await expect(page.locator(".fh-pick")).toContainText("60.0%");
  await expect(page.locator(".fh-pick")).toContainText("50.0%");
  await expect(page.locator(".fh-pick")).toContainText("test-model");
  await page.getByLabel("Sport", { exact: true }).selectOption("NBA");
  await expect(
    page.getByRole("button", { name: "Generate / refresh" }),
  ).toBeDisabled();
  await expect(page.getByRole("alert")).toContainText("No NBA model");
});
test("chat retries original message and renders provider text safely", async ({
  page,
}) => {
  await authenticate(page);
  let count = 0;
  const requests = [];
  await page.route("**/api/v1/ai-picks/chat", (route) => {
    requests.push(route.request().postDataJSON());
    count++;
    return count === 1
      ? route.fulfill({
          status: 503,
          json: { error: "Test provider unavailable" },
        })
      : route.fulfill({
          json: {
            conversation_id: "test-conversation",
            reply: {
              reply: "<img src=x onerror=alert(1)> This is explanatory text.",
              evidence: [{ fixture_id: 1 }],
            },
          },
        });
  });
  await page.goto("/ai-picks/chat");
  await page
    .getByLabel("Message", { exact: true })
    .fill("Explain Arsenal versus Chelsea");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Test provider unavailable",
  );
  await page.getByRole("alert").getByRole("button", { name: "Retry" }).click();
  await expect(page.locator(".fh-message.assistant")).toContainText(
    "<img src=x onerror=alert(1)>",
  );
  await expect(page.locator(".fh-message.assistant img")).toHaveCount(0);
  expect(requests[1].messages).toEqual(requests[0].messages);
  await expect(page.locator(".fh-message.user")).toHaveCount(1);
});
for (const viewport of [
  { width: 1440, height: 1000 },
  { width: 900, height: 1000 },
  { width: 390, height: 844 },
]) {
  test(`template layout has no overflow at ${viewport.width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize(viewport);
    await page.goto("/app");
    await expect(page.locator(".fh-hero")).toBeVisible();
    await page.locator("img").evaluateAll(async (images) => {
      await Promise.all(
        images.map((image) => {
          image.loading = "eager";
          return image.decode().catch(() => {});
        }),
      );
    });
    expect(
      await page
        .locator(".fh-hero img")
        .evaluate((image) => image.naturalWidth),
    ).toBeGreaterThan(0);
    const layout = await page.evaluate(() => ({
      width: document.documentElement.clientWidth,
      scroll: document.documentElement.scrollWidth,
      background: getComputedStyle(document.querySelector(".fh-nav"))
        .backgroundColor,
    }));
    expect(layout.scroll).toBeLessThanOrEqual(layout.width);
    expect(layout.background).toBe("rgb(20, 27, 23)");
    if (viewport.width > 1000)
      await expect(page.locator(".fh-left-sidebar")).toBeVisible();
    else await expect(page.locator(".fh-left-sidebar")).toBeHidden();
    await page.screenshot({
      path: testInfo.outputPath(`homepage-${viewport.width}.png`),
      fullPage: true,
    });
  });
}
