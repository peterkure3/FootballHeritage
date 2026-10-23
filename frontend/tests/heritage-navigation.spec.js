import { defaultApiFixture } from './feature-fixture.js';
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
  await page.route("**/api/v1/**", defaultApiFixture);
  await page.route("**/api/v1/pipeline/matches?*", (route) =>
    route.fulfill({ json: fixtures }),
  );
  await page.route("**/user/profile", (route) => route.fulfill({ json: user }));
});

for (const width of [1440, 900, 390]) {
  test(`Fantasy Sports links to FPL at ${width}px`, async ({ page }) => {
    await authenticate(page);
    await page.setViewportSize({ width, height: 900 });
    await page.route("**/fpl/advice", (route) => route.fulfill({ status: 404, json: {} }));
    await page.goto("/app");
    if (width <= 850) {
      await page.getByRole("button", { name: "Open navigation" }).click();
      await page.locator("#mobile-navigation summary").filter({ hasText: /^Fantasy Sports$/ }).click();
      await page.locator("#mobile-navigation").getByRole("link", { name: /Fantasy Premier League/ }).click();
    } else {
      const trigger = page.getByRole("button", { name: "Fantasy Sports", exact: true });
      await trigger.focus();
      await expect(trigger).toHaveAttribute("aria-expanded", "true");
      await page.keyboard.press("Escape");
      await expect(trigger).toBeFocused();
      await expect(trigger).toHaveAttribute("aria-expanded", "false");
      await trigger.click();
      await page.locator("#menu-fantasy").getByRole("link", { name: /Fantasy Premier League/ }).click();
    }
    await expect(page).toHaveURL("/fpl-advisor");
    await expect(page.getByRole("heading", { name: "Fantasy Premier League", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "No FPL Data Available" })).toBeVisible();
    await expect(page.locator("#menu-fantasy")).toHaveCount(0);
    await expect(page.locator("#mobile-navigation")).toHaveCount(0);
    await page.getByRole("button", { name: "Captain Picks", exact: true }).click();
    await expect(page.getByRole("button", { name: "Captain Picks", exact: true })).toHaveAttribute("aria-pressed", "true");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    if (width > 850) {
      const nav = await page.locator(".fh-desktop-nav").boundingBox();
      const actions = await page.locator(".fh-nav-actions").boundingBox();
      expect(nav.x + nav.width).toBeLessThanOrEqual(actions.x);
      await expect(page.locator(".fh-fantasy-menu .active")).toHaveText("Fantasy Sports");
    }
  });
}

for (const width of [1440, 900, 390]) {
  test(`FPL redesigned workspace preserves player tools at ${width}px`, async ({ page }, testInfo) => {
    await authenticate(page);
    await page.setViewportSize({ width, height: 1000 });
    const players = Array.from({ length: 15 }, (_, id) => ({
      id: id + 1, web_name: `Player ${id + 1}`, team_name: "Test United", position: id < 3 ? "FWD" : id < 6 ? "MID" : id < 10 ? "DEF" : "GKP",
      price: 7.5, expected_points: 6.2, form: "5.1", points_per_game: "4.7", total_points: 60,
      selected_by_percent: "7.5", value_score: 0.83, fixture_difficulty_avg: 2.4, status: "a",
    }));
    const advice = { gameweek: 9, generated_at: "2026-10-19T09:00:00Z",
      optimal_team: { formation: { DEF: 4, MID: 3, FWD: 3 }, starting_xi: players.slice(0, 11), bench: players.slice(11), captain: players[0], vice_captain: players[1], total_cost: 98.5, budget_remaining: 1.5, expected_points: 68.2 },
      captain_picks: players.slice(0, 6), value_picks: players.slice(0, 3), differential_picks: players.slice(0, 2),
      top_goalkeepers: players.slice(10), top_defenders: players.slice(6, 10), top_midfielders: players.slice(3, 6), top_forwards: players.slice(0, 3),
    };
    await page.route("**/fpl/advice", route => route.fulfill({ json: advice }));
    await page.goto("/fpl-advisor");
    await expect(page.locator(".fpl-pitch .fpl-player")).toHaveCount(11);
    await expect(page.locator(".fpl-bench .fpl-player")).toHaveCount(4);
    await expect(page.locator(".fpl-metrics")).toContainText("£98.5m");
    const player = page.locator(".fpl-pitch .fpl-player").first();
    await player.locator("summary").focus();
    await page.keyboard.press("Enter");
    await expect(player).toHaveAttribute("open", "");
    await expect(player).toContainText("Ownership");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`fpl-${width}.png`), fullPage: true });
    await page.getByRole("button", { name: "Captain Picks", exact: true }).click();
    await expect(page.locator(".fpl-player")).toHaveCount(5);
    await page.getByRole("button", { name: "Show all 6 players" }).click();
    await expect(page.locator(".fpl-player")).toHaveCount(6);
    for (const [tab, heading] of [["By Position", "Top Goalkeepers"], ["Value Picks", "Best Value Picks"], ["Differentials", "Differential Picks"]]) {
      await page.getByRole("button", { name: tab, exact: true }).click();
      await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    }
  });
}

test("FPL data errors retry and refresh recovers the empty state", async ({ page }) => {
  await authenticate(page);
  let available = false;
  await page.route("**/fpl/advice", route => route.fulfill({ status: 503, json: {} }));
  await page.goto("/fpl-advisor");
  await expect(page.getByRole("alert")).toContainText("Failed to fetch FPL advice");
  await page.route("**/fpl/advice", route => route.fulfill(available
    ? { json: { gameweek: 9, captain_picks: [] } }
    : { status: 404, json: {} }));
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("heading", { name: "No FPL Data Available" })).toBeVisible();
  await page.route("**/fpl/refresh", route => {
    expect(route.request().method()).toBe("POST");
    available = true;
    return route.fulfill({ json: { success: true } });
  });
  await page.getByRole("button", { name: "Fetch FPL Data", exact: true }).click();
  await expect(page.getByRole("heading", { name: "No optimal team available." })).toBeVisible();
  await page.getByRole("button", { name: "Captain Picks", exact: true }).click();
  await expect(page.getByRole("heading", { name: "No player recommendations available." })).toBeVisible();
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
  await page.route("**/api/v1/pipeline/matches?*", (route) =>
    route.fulfill({
      status: 503,
      json: { error: "Test upstream unavailable" },
    }),
  );
  await page.goto("/sport/football/scores");
  await expect(
    page.getByRole("heading", { name: "Data unavailable" }),
  ).toBeVisible();
  await page.route("**/api/v1/pipeline/matches?*", (route) =>
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
            pick_type: "value",
            bookmaker: "Test bookmaker",
            odds_updated_at: "2026-10-07T11:50:00Z",
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
  await expect(page.locator(".fh-pick")).toContainText("Test bookmaker");
  await page.getByLabel("Sport", { exact: true }).selectOption("NBA");
  await expect(
    page.getByRole("button", { name: "Generate / refresh" }),
  ).toBeDisabled();
  await expect(page.getByRole("alert")).toContainText("No NBA model");
});
test("AI picks keeps model predictions when bookmaker odds are missing", async ({ page }) => {
  await authenticate(page);
  let body;
  await page.route("**/ai-picks/generate", (route) => {
    body = route.request().postDataJSON();
    return route.fulfill({ json: {
      id: "prediction-run", summary: { message: "Predictions ranked from the active model." },
      picks: [{ match_id: 2, home_team: "Arsenal", away_team: "Chelsea", competition: "Premier League",
        match_date: "2026-10-10T14:30:00Z", model_prob: 0.7, selection: "Arsenal (Home Win)",
        pick_type: "prediction", model_version: "test-model", decimal_odds: null, edge_pct: null,
        expected_value: null, recommended_stake: null, bookmaker: null,
        explanation: "No recent bookmaker quote is available." }],
    } });
  });
  await page.goto("/ai-picks?competition=Premier+League&date=2026-10-10");
  await page.getByRole("button", { name: "Generate / refresh" }).click();
  await expect(page.locator(".fh-pick")).toContainText("70.0%");
  await expect(page.locator(".fh-pick")).toContainText("Model prediction");
  await expect(page.locator(".fh-pick")).toContainText("No recent bookmaker quote");
  await expect(page.locator(".fh-pick-metrics")).toContainText("Unavailable");
  expect(body).toMatchObject({ competition: "Premier League", date: "2026-10-10", limit: 10 });
});
test("AI picks explains empty results and allows retry after service errors", async ({ page }) => {
  await authenticate(page);
  let count = 0;
  await page.route("**/ai-picks/generate", (route) => ++count === 1
    ? route.fulfill({ status: 503, json: { error: "Prediction database is unavailable" } })
    : route.fulfill({ json: { id: "empty-run", picks: [], summary: { message: "No recent model predictions match these filters." } } }));
  await page.goto("/ai-picks");
  await page.getByRole("button", { name: "Generate / refresh" }).click();
  await expect(page.getByRole("alert")).toContainText("Prediction database is unavailable");
  await page.getByRole("alert").getByRole("button", { name: "Retry" }).click();
  await expect(page.locator(".fh-content")).toContainText("No recent model predictions match these filters.");
  await expect(page.locator(".fh-pick")).toHaveCount(0);
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
  expect(requests[1].request_id).toBe(requests[0].request_id);
  await expect(page.locator(".fh-message.user")).toHaveCount(1);
});
test("RAG chat restores saved evidence and sends server history on follow-up", async ({ page }) => {
  await authenticate(page);
  const id = "82cebf90-68f4-4194-abf6-ef17e5d4b6e";
  await page.route(`**/api/v1/ai-picks/conversations/${id}`, (route) => route.fulfill({ json: [
    { role: "user", content: "Explain Arsenal" },
    { role: "assistant", content: "Arsenal home probability is 60%. [P1]", metadata: {
      mode: "retrieved_evidence", evidence: [{ id: "P1", home_team: "Arsenal", model_version: "test-model" }],
    } },
  ] }));
  let body;
  await page.route("**/api/v1/ai-picks/chat", (route) => {
    body = route.request().postDataJSON();
    return route.fulfill({ json: { conversation_id: id, reply: {
      reply: "The model draw probability is 25%. [P1]", mode: "gemini_rag", evidence: [{ id: "P1" }],
    } } });
  });
  await page.goto(`/ai-picks/chat?conversation=${id}`);
  await page.reload();
  await expect(page.locator(".fh-message.assistant")).toContainText("RETRIEVED EVIDENCE");
  await page.getByText("Sources and retrieved evidence", { exact: true }).click();
  await expect(page.locator(".fh-message.assistant pre")).toContainText("test-model");
  await page.getByLabel("Message", { exact: true }).fill("What about the draw?");
  await page.getByRole("button", { name: "Send", exact: true }).click();
  await expect(page.locator(".fh-message.assistant").last()).toContainText("25%");
  expect(body.conversation_id).toBe(id);
  expect(body.messages).toEqual([
    { role: "user", content: "Explain Arsenal" },
    { role: "assistant", content: "Arsenal home probability is 60%. [P1]" },
    { role: "user", content: "What about the draw?" },
  ]);
  await expect(page.locator(".fh-message")).toHaveCount(4);
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
