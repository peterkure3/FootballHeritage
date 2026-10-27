import { featureAccess } from './feature-fixture.js';
import { test, expect } from "@playwright/test";
import { spawn, execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import process from "node:process";
import { readFileSync } from "node:fs";

const user = {
  id: "prediction-test",
  first_name: "Test",
  last_name: "User",
  email: "test@example.com",
  balance: 0,
};
const now = new Date().toISOString();
const quote = {
  bookmaker: "Test Book",
  observed_at: now,
  fresh: true,
  prices: { home_win: 2, draw: 3, away_win: 5 },
  fair_probabilities: { home_win: 15 / 31, draw: 10 / 31, away_win: 6 / 31 },
};
const forecast = {
  match_id: 1,
  competition: "Test League",
  home_team: "Home Club",
  away_team: "Away Club",
  kickoff: now,
  prediction: {
    status: "current",
    winner: "home_win",
    model_version: "2.0.0",
    generated_at: now,
    probabilities: { home_win: 0.6, draw: 0.25, away_win: 0.15 },
  },
  market: {
    state: "current",
    quotes: [quote],
    comparisons: [
      {
        outcome: "home_win",
        bookmaker: "Test Book",
        decimal_odds: 2,
        observed_at: now,
        consensus_prob: 0.4839,
        break_even_prob: 0.5,
        estimated_ev_units: 0.2,
      },
    ],
  },
};
const missing = {
  ...forecast,
  match_id: 2,
  home_team: "Other Club",
  prediction: null,
  market: { state: "missing", quotes: [], comparisons: [] },
};
const summary = {
  overall_accuracy: 50,
  total_predictions: 2,
  correct_predictions: 1,
  log_loss: 0.7,
  brier_score: 0.4,
  excluded: {
    unknown_kickoff: 0,
    no_valid_pre_kickoff: 1,
    unknown_kickoff_outside_date_window: 380,
  },
  evidence_note: "Pre-kickoff timestamps are verified.",
  by_league: [
    { league: "Test League", total: 2, correct: 1, accuracy_pct: 50 },
  ],
  sample_start: now,
  sample_end: now,
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript((data) => {
    sessionStorage.setItem("token", "test-only-token");
    sessionStorage.setItem("betting_user_data", JSON.stringify(data));
  }, user);
  await page.route("**/user/profile", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/**", (route) => {
    if (new URL(route.request().url()).pathname === "/api/v1/me/features") return route.fulfill({ json: featureAccess });
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/prediction-dashboard/fixtures"))
      return route.fulfill({
        json: {
          items:
            url.searchParams.get("page") === "2"
              ? [{ ...missing, match_id: 3 }]
              : [forecast, missing],
          competitions: ["Test League"],
          total_count: 7,
          page_size: 6,
          active_model_version: "2.0.0",
          generated_at: now,
        },
      });
    if (url.pathname.endsWith("/predictions/versions"))
      return route.fulfill({
        json: { versions: [{ version: "2.0.0" }], current_version: "2.0.0" },
      });
    if (url.pathname.endsWith("/predictions/accuracy-data"))
      return route.fulfill({ json: summary });
    if (url.pathname.endsWith("/predictions/history-data"))
      return route.fulfill({
        json: { total_count: 0, correct_count: 0, predictions: [] },
      });
    if (url.pathname.endsWith("/sport-models/teams"))
      return route.fulfill({ json: { teams: ["Buffalo Bills", "Kansas City Chiefs", "New York Jets"] } });
    if (url.pathname.endsWith("/sport-models/preview")) {
      const body = route.request().postDataJSON();
      return route.fulfill({
        json: {
          ...body,
          model_version: "nfl-test",
          active: false,
          history_through: now,
          settlement_rule: "INCLUDING_OVERTIME_TIES_VOID",
          probability_basis: "CONDITIONAL_ON_NO_FINAL_TIE",
          market_features_used: false,
          probabilities: { home_win: 0.55, away_win: 0.45 },
        },
      });
    }
    if (url.pathname.endsWith("/sport-models"))
      return route.fulfill({
        json: {
          runs: [
            {
              candidate_id: "20261009T144354530070Z",
              sports: { nfl: { status: "candidate" } },
            },
          ],
        },
      });
    return route.fulfill({ json: [] });
  });
});

test("complete probabilities, decimal quotes, missing market, and pagination", async ({
  page,
}) => {
  await page.goto("/predictions");
  await expect(
    page.getByRole("heading", { name: /See the probabilities/ }),
  ).toBeVisible();
  const card = page.locator(".pd-forecast").first();
  await expect(card).toContainText("Draw");
  await expect(card).toContainText("25.0%");
  await expect(card).toContainText("2.00");
  await expect(card).toContainText("+0.200");
  await expect(page.locator(".pd-forecast").nth(1)).toContainText(
    "Prediction pending",
  );
  await expect(page.locator(".pd-forecast").nth(1)).toContainText(
    "Market unavailable",
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../stages/03-build/output/predictions-ui-desktop.png",
    fullPage: true,
  });
  const next = page.waitForRequest(
    (request) =>
      request.url().includes("/prediction-dashboard/fixtures") &&
      new URL(request.url()).searchParams.get("page") === "2",
  );
  await page.getByRole("button", { name: "Next page" }).click();
  await next;
  await expect(page.locator(".pd-forecast")).toHaveCount(1);
});

test("La Liga uses its database key and league options survive empty filters", async ({ page }) => {
  await page.route("**/prediction-dashboard/fixtures?*", (route) => route.fulfill({ json: {
    items: [], competitions: ["Bundesliga", "Primera Division", "Serie A"],
    competition_labels: { "Primera Division": "La Liga" }, total_count: 0,
    active_model_version: "2.0.0", generated_at: now,
  } }));
  await page.goto("/predictions?view=comparisons");
  const select = page.getByRole("combobox", { name: "Competition", exact: true });
  await expect(select.getByRole("option", { name: "La Liga", exact: true })).toHaveAttribute("value", "Primera Division");
  const request = page.waitForRequest((request) => new URL(request.url()).searchParams.get("competition") === "Primera Division");
  await select.selectOption({ label: "La Liga" });
  await request;
  await expect(select.getByRole("option")).toHaveCount(4);
  await expect(page.getByText("No upcoming fixtures match these filters.")).toBeVisible();
});

test("evaluated league models show their provenance and held-out sample", async ({ page }) => {
  await page.route("**/prediction-dashboard/fixtures?*", (route) => route.fulfill({ json: {
    items: [{ ...forecast, prediction: { ...forecast.prediction,
      model_kind: "evaluated_league_candidate", model_version: "league-PD-test", active: false,
      feature_cutoff: now, test_metrics: { samples: 379, accuracy: 0.5277 } } }],
    competitions: ["Primera Division"], total_count: 1, generated_at: now, active_model_version: "2.0.0",
  } }));
  await page.goto("/predictions");
  await expect(page.getByText("Evaluated league model", { exact: true })).toBeVisible();
  await page.getByText("Model & source details", { exact: true }).click();
  await expect(page.getByText("379 games · 52.8% accuracy", { exact: true })).toBeVisible();
  await expect(page.getByText("League match history; bookmaker prices excluded", { exact: true })).toBeVisible();
});

test("live league forecasts render in the bookmaker grid", async ({ page }) => {
  test.skip(process.env.RUN_LEAGUE_LIVE_TESTS !== "1", "Requires the authenticated local API on port 5567");
  test.setTimeout(60000);
  let live;
  await page.route("**/prediction-dashboard/fixtures?*", async (route) => {
    const query = new URL(route.request().url()).search.slice(1);
    const code = "import config,os,sys,requests; sys.stdout.reconfigure(encoding='utf-8'); r=requests.get('http://127.0.0.1:5567/api/v1/prediction-dashboard/fixtures',params=sys.argv[1],headers={'x-internal-token':os.getenv('PIPELINE_INTERNAL_TOKEN','')},timeout=20); r.raise_for_status(); print(r.text)";
    live = JSON.parse(execFileSync("py", ["-3", "-c", code, query], {
      cwd: fileURLToPath(new URL("../../pipeline/", import.meta.url)), encoding: "utf8", windowsHide: true,
    }));
    await route.fulfill({ json: live });
  });
  await page.goto("/predictions?view=comparisons");
  const select = page.getByRole("combobox", { name: "Competition", exact: true });
  const filtered = page.waitForResponse((response) => new URL(response.url()).searchParams.get("competition") === "Primera Division");
  await select.selectOption({ label: "La Liga" });
  await filtered;
  await expect(page.locator(".bc-table tbody tr")).toHaveCount(20);
  await expect(select).toHaveValue("Primera Division");
  expect(live.competitions).toHaveLength(10);
  expect(JSON.stringify(live)).not.toContain("\uFFFD");
  expect(live.items.every((item) => item.prediction?.model_kind === "evaluated_league_candidate")).toBe(true);
  await expect(page.locator(".bc-table tbody tr").first()).toContainText("%");
  await page.screenshot({ path: "../stages/03-build/output/league-grid-live-20261025.png" });
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.locator(".bc-table tbody tr").first().scrollIntoViewIfNeeded();
  await page.screenshot({ path: "../stages/03-build/output/league-grid-probabilities-20261025.png" });
});

test("all requested bookmakers remain visible across pages without invented prices", async ({
  page,
}) => {
  const inventory = JSON.parse(
    readFileSync(
      new URL("../../_config/bookmakers.json", import.meta.url),
      "utf8",
    ),
  );
  const bookmakers = inventory.sportsbooks.map((book) => ({
    bookmaker: book.bookmaker + (book.region ? `:${book.region}` : ""),
    name:
      (book.current_name ?? book.requested_name) +
      (book.region ? ` · ${book.region}` : ""),
  }));
  await page.route("**/prediction-dashboard/fixtures?*", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            ...missing,
            market: {
              ...missing.market,
              quotes: [{ ...quote, bookmaker: "admiralbet:UG", fresh: false }],
            },
          },
        ],
        bookmakers,
        total_count: 40,
        page_size: 20,
        competitions: ["UEFA Champions League"],
        active_model_version: "2.0.0",
        generated_at: now,
      },
    }),
  );
  await page.goto("/predictions");
  await page
    .getByRole("button", { name: "Bookmaker grid", exact: true })
    .click();
  await expect(page.locator(".bc-book")).toHaveCount(bookmakers.length);
  await expect(
    page.locator(".bc-book").filter({ hasText: "AdmiralBet" }),
  ).toHaveCount(0);
  await expect(
    page.locator(".bc-book").filter({ hasText: "betPawa" }),
  ).toContainText("No linked prices");
  await expect(page.locator(".bc-table tbody td.bc-missing")).toHaveCount(
    (bookmakers.length + 1) * 3,
  );
  await page.getByRole("button", { name: "Next page" }).click();
  await expect(page.locator(".bc-book")).toHaveCount(bookmakers.length);
  await page
    .getByRole("combobox", { name: "Competition", exact: true })
    .selectOption("UEFA Champions League");
  await expect(page.locator(".bc-book")).toHaveCount(bookmakers.length);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("bookmaker grid puts populated columns first and reports fixture coverage", async ({ page }) => {
  await page.route("**/prediction-dashboard/fixtures?**", (route) => route.fulfill({
    json: {
      items: [{ ...forecast, market: { ...forecast.market, quotes: [quote, { ...quote, bookmaker: "Z extra" }] } }, missing],
      bookmakers: [{ bookmaker: "A empty", name: "A empty" }, { bookmaker: "Z extra", name: "Z extra" }, { bookmaker: "Test Book", name: "Test Book" }],
      total_count: 2, competitions: [], active_model_version: "2.0.0", generated_at: now,
    },
  }));
  await page.goto("/predictions?view=comparisons");
  const columns = page.locator(".bc-book");
  await expect(columns).toHaveCount(3);
  await expect(columns.nth(0)).toContainText("Test Book");
  await expect(columns.nth(1)).toContainText("Z extra");
  await expect(columns.nth(2)).toContainText("A empty");
  await expect(columns.nth(0)).toContainText("1/2 fixtures with fresh prices");
});

test("bookmaker grid keeps FootballHeritage first and switches probabilities to EV", async ({
  page,
}) => {
  await page.goto("/predictions");
  await page
    .getByRole("button", { name: "Bookmaker grid", exact: true })
    .click();
  const grid = page.locator(".bc-table");
  await expect(
    grid.locator("thead tr").first().locator("th").nth(1),
  ).toContainText("FootballHeritage");
  await expect(
    grid.locator("thead tr").first().locator("th").nth(2),
  ).toContainText("Test Book");
  const row = grid.locator("tbody tr").first();
  await expect(row.locator("td").nth(0)).toHaveText("60.0%");
  await expect(row.locator("td").nth(3)).toHaveText("48.4%");
  await expect(row.locator("td").nth(4)).toHaveText("32.3%");
  await expect(grid.locator("tbody tr").nth(1).locator("td")).toHaveText([
    "—",
    "—",
    "—",
    "—",
    "—",
    "—",
  ]);
  await page.getByLabel("Comparison metric").selectOption("odds");
  await expect(row.locator("td").nth(0)).toHaveText("60.0%");
  await expect(row.locator("td").nth(3)).toHaveText("2.00");
  await expect(row.locator("td").nth(4)).toHaveText("3.00");
  await expect(row.locator("td").nth(5)).toHaveText("5.00");
  await page.getByLabel("Comparison metric").selectOption("ev");
  await expect(row.locator("td").nth(0)).toHaveText("60.0%");
  await expect(row.locator("td").nth(3)).toHaveText("+20.0%");
  await expect(row.locator("td").nth(4)).toHaveText("-25.0%");
  await expect(row.locator("td").nth(5)).toHaveText("-25.0%");
  await page.screenshot({
    path: "../stages/03-build/output/bookmaker-grid-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  const widths = await page.evaluate(() => ({
    body: document.documentElement.scrollWidth,
    viewport: innerWidth,
    grid: document.querySelector(".bc-scroll").scrollWidth,
    container: document.querySelector(".bc-scroll").clientWidth,
  }));
  expect(widths.body).toBeLessThanOrEqual(widths.viewport);
  expect(widths.grid).toBeGreaterThan(widths.container);
  await page.screenshot({
    path: "../stages/03-build/output/bookmaker-grid-mobile.png",
    fullPage: true,
  });
});

test("bookmaker grid suppresses stale prices and requires a fresh model for EV", async ({
  page,
}) => {
  await page.route("**/prediction-dashboard/fixtures?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            ...forecast,
            market: {
              ...forecast.market,
              quotes: [{ ...quote, fresh: false }],
            },
          },
          {
            ...forecast,
            match_id: 2,
            prediction: { ...forecast.prediction, status: "stale" },
          },
        ],
        total_count: 2,
        competitions: [],
        active_model_version: "2.0.0",
        generated_at: now,
      },
    }),
  );
  await page.goto("/predictions");
  await page
    .getByRole("button", { name: "Bookmaker grid", exact: true })
    .click();
  const rows = page.locator(".bc-table tbody tr");
  await expect(rows.nth(0).locator("td").nth(3)).toHaveText("—");
  await expect(rows.nth(1).locator("td").nth(3)).toHaveText("48.4%");
  await page.getByLabel("Comparison metric").selectOption("odds");
  await expect(rows.nth(0).locator("td").nth(3)).toHaveText("—");
  await expect(rows.nth(1).locator("td").nth(3)).toHaveText("2.00");
  await page.getByLabel("Comparison metric").selectOption("ev");
  await expect(rows.nth(1).locator("td").nth(3)).toHaveText("—");
});

test("filters share the exact date and model scope; correctness filters the table", async ({
  page,
}) => {
  await page.goto("/predictions");
  await page.getByRole("button", { name: "Settled performance" }).click();
  await expect(
    page.getByText("Pre-kickoff accuracy", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("v2.0.0", { exact: true })).toHaveCount(1);
  const summaryRequest = page.waitForRequest(
    (request) =>
      request.url().includes("/accuracy-data") &&
      request.url().includes("start_date=2026-09-01"),
  );
  const historyRequest = page.waitForRequest(
    (request) =>
      request.url().includes("/history-data") &&
      request.url().includes("start_date=2026-09-01"),
  );
  await page.getByLabel("From (UTC)").fill("2026-09-01");
  await Promise.all([summaryRequest, historyRequest]);
  const filtered = page.waitForRequest((request) =>
    request.url().includes("result_filter=correct"),
  );
  await page
    .getByRole("combobox", { name: "Result", exact: true })
    .selectOption("correct");
  await filtered;
  await expect(page.getByText(/Missing kickoff dates: 380/)).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../stages/03-build/output/predictions-ui-performance.png",
    fullPage: true,
  });
});

test("NFL candidate preview has two outcomes and tie settlement, on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/predictions");
  await page.getByRole("button", { name: "Model lab" }).click();
  await page
    .getByLabel("Sport / candidate")
    .selectOption("20261009T144354530070Z|nfl");
  await page
    .getByLabel("Home team", { exact: true })
    .fill("chief");
  await page.getByRole("option", { name: "Kansas City Chiefs", exact: true }).click();
  const away = page.getByRole("combobox", { name: "Away team", exact: true });
  await away.fill("BILLS");
  await away.press("ArrowDown");
  await away.press("Enter");
  await expect(away).toHaveValue("Buffalo Bills");
  await page.getByLabel("Kickoff (your local time)").fill("2026-11-01T18:00");
  await page.getByRole("button", { name: "Preview matchup" }).click();
  await expect(page.getByText("Candidate preview · inactive")).toBeVisible();
  await expect(page.locator(".pd-probabilities .pd-outcome")).toHaveCount(2);
  await expect(
    page.getByText("conditional on no final tie", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../stages/03-build/output/predictions-ui-mobile-models.png",
    fullPage: true,
  });
});

test("Model lab team search handles empty results, invalid names and model reset", async ({ page }) => {
  await page.goto("/predictions?tab=models");
  await page.getByRole("button", { name: "Model lab" }).click();
  const home = page.getByRole("combobox", { name: "Home team", exact: true });
  const model = page.getByLabel("Sport / candidate");
  await expect(home).toBeEnabled();
  await model.selectOption("20261009T144354530070Z|nfl");
  await home.click();
  await expect(page.getByRole("listbox", { name: "Home team" }).getByRole("option")).toHaveCount(3);
  await home.fill("unknown");
  await expect(page.getByText("No matching teams. Try another name.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Preview matchup" })).toBeDisabled();
  await home.fill("chief");
  await home.press("ArrowDown");
  await home.press("Enter");
  await page.getByLabel("Away team", { exact: true }).click();
  await expect(page.getByRole("option", { name: "Kansas City Chiefs", exact: true })).toHaveCount(0);
  await page.getByRole("combobox", { name: "Away team", exact: true }).press("Escape");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await model.selectOption("");
  await expect(home).toHaveValue("");
  await expect(home).toBeDisabled();
});

test("Model lab team list recovers after a failed request", async ({ page }) => {
  let fail = true;
  await page.route("**/sport-models/teams?*", (route) => fail
    ? route.fulfill({ status: 503, json: { detail: "Unavailable" } })
    : route.fulfill({ json: { teams: ["Buffalo Bills", "Kansas City Chiefs"] } }));
  await page.goto("/predictions");
  await page.getByRole("button", { name: "Model lab" }).click();
  await page.getByLabel("Sport / candidate").selectOption("20261009T144354530070Z|nfl");
  await expect(page.getByText("Could not load teams.")).toBeVisible();
  await expect(page.getByLabel("Home team", { exact: true })).toBeEnabled();
  fail = false;
  await page.getByRole("button", { name: "Retry team list" }).click();
  await expect(page.getByLabel("Home team", { exact: true })).toBeEnabled();
});

test("Model lab team fields accept typing immediately while suggestions load", async ({ page }) => {
  let release;
  const ready = new Promise((resolve) => { release = resolve; });
  await page.route("**/sport-models/teams?*", async (route) => {
    await ready;
    await route.fulfill({ json: { teams: ["Buffalo Bills", "Kansas City Chiefs"] } });
  });
  await page.goto("/predictions");
  await page.getByRole("button", { name: "Model lab", exact: true }).click();
  const home = page.getByRole("combobox", { name: "Home team", exact: true });
  await expect(page.getByLabel("Sport / candidate")).toHaveValue("20261009T144354530070Z|nfl");
  await home.fill("chief");
  await expect(home).toHaveValue("chief");
  await expect(page.getByText("Loading team suggestions…", { exact: true })).toBeVisible();
  release();
  await page.getByRole("option", { name: "Kansas City Chiefs", exact: true }).click();
  await expect(home).toHaveValue("Kansas City Chiefs");
});

test("server failure is shown as an API error, not a missing prediction", async ({
  page,
}) => {
  await page.route("**/prediction-dashboard/fixtures?*", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Database temporarily unavailable" },
    }),
  );
  await page.goto("/predictions");
  await expect(page.getByRole("alert")).toContainText(
    "Database temporarily unavailable",
  );
  await expect(page.getByText("Prediction pending")).toHaveCount(0);
});

test("stale quotes never display estimated value", async ({ page }) => {
  await page.route("**/prediction-dashboard/fixtures?*", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            ...forecast,
            market: {
              state: "unverified_or_stale",
              quotes: [{ ...quote, observed_at: null, fresh: false }],
              comparisons: [],
            },
          },
        ],
        total_count: 1,
        competitions: [],
        active_model_version: "2.0.0",
        generated_at: now,
      },
    }),
  );
  await page.goto("/predictions");
  await expect(page.getByText(/Quotes are stale, incomplete/)).toBeVisible();
  await expect(page.getByText("Est. EV / unit")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../stages/03-build/output/predictions-ui-mobile-fixtures.png",
    fullPage: true,
  });
});

test("manual paper choice is labeled separately from the frozen trial", async ({
  page,
}) => {
  const row = {
    home: "Coventry City FC",
    away: "Newcastle United FC",
    kickoff: now,
    bookmaker: "ababet:UG",
    selected_outcome: "away_win",
    status: "recorded_pregame",
    settlement_status: "pending",
    profit_units: null,
    selection_evidence: { decimal_odds: 2.05, estimated_ev: 0.1 },
  };
  await page.route("**/prediction-dashboard/paper-trials", (route) =>
    route.fulfill({
      json: {
        studies: [
          { study_id: "manual", policy: { selection: "user_selected" } },
        ],
        trials: [
          {
            candidate_id: "manual-selection",
            trial_sha256: "manual",
            policy: { selection: "user_selected" },
            fixtures: [row],
            settled_selections: 0,
            pending_forecasts: 1,
            roi: null,
            stressed_roi: null,
          },
        ],
      },
    }),
  );
  await page.goto("/predictions");
  await page.getByRole("button", { name: "Paper trials" }).click();
  await expect(
    page.getByRole("heading", { name: "Manual paper selection" }),
  ).toBeVisible();
  await expect(
    page.getByText(/User-selected one-unit paper pick/),
  ).toBeVisible();
  await expect(page.locator(".pd-table")).toContainText("Newcastle United FC");
  await expect(page.locator(".pd-table")).toContainText("2.05");
  await expect(page.getByText(/Study progress/)).toHaveCount(0);
});

test("paper trial leaves ROI pending until independently verified results", async ({
  page,
}) => {
  await page.route("**/prediction-dashboard/paper-trials", (route) =>
    route.fulfill({
      json: {
        trials: [
          {
            candidate_id: "frozen-test",
            trial_sha256: "test-trial",
            settled_selections: 0,
            pending_forecasts: 1,
            roi: null,
            stressed_roi: null,
            evidence_note: "Pending results are excluded from ROI.",
            fixtures: [
              {
                home: "Home Club",
                away: "Away Club",
                kickoff: now,
                status: "recorded_pregame",
                selected_outcome: "home_win",
                settlement_status: "pending",
                profit_units: null,
                selection_evidence: { decimal_odds: 2, estimated_ev: 0.2 },
              },
            ],
          },
        ],
      },
    }),
  );
  await page.goto("/predictions");
  await page.getByRole("button", { name: "Paper trials" }).click();
  await expect(page.getByText(/Paper ROI: Pending/)).toBeVisible();
  await expect(
    page.getByText(/Pending results are excluded from ROI/),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "Home win", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "pending", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("0.00%", { exact: true })).toHaveCount(0);
});

test("paper study shows both sample gates and collector failures", async ({
  page,
}) => {
  await page.route("**/prediction-dashboard/paper-trials", (route) =>
    route.fulfill({
      json: {
        trials: [],
        collector: {
          outcome: "failed",
          last_success_at: now,
          failed_steps: ["scripts.refresh_regional_pipeline"],
        },
        studies: [
          {
            study_id: "study",
            candidate_id: "frozen",
            settled_selections: 200,
            fixture_days: 59,
            pending_selections: 2,
            batch_count: 20,
            roi: -0.125,
            stressed_roi: -0.1425,
            protocol: { minimum_selections: 200, minimum_fixture_days: 60 },
            assessment_status: "collecting",
            assessment: null,
          },
        ],
      },
    }),
  );
  await page.goto("/predictions");
  await page.getByRole("button", { name: "Paper trials" }).click();
  await expect(
    page.getByText("200 / 200 settled selections · 59 / 60 fixture days"),
  ).toBeVisible();
  await expect(page.getByText(/Assessment: collecting/)).toBeVisible();
  await expect(page.getByRole("status")).toContainText(
    "Collection needs attention",
  );
  await expect(page.getByText(/Stressed ROI 95% interval/)).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("formal paper assessment discloses frozen interval without claiming executable profit", async ({
  page,
}) => {
  await page.route("**/prediction-dashboard/paper-trials", (route) =>
    route.fulfill({
      json: {
        trials: [],
        studies: [
          {
            study_id: "study",
            candidate_id: "frozen",
            settled_selections: 250,
            fixture_days: 65,
            pending_selections: 0,
            batch_count: 30,
            roi: 0.2,
            stressed_roi: 0.18,
            protocol: { minimum_selections: 200, minimum_fixture_days: 60 },
            assessment_status: "paper_evidence_passed",
            assessment: {
              selections: 240,
              fixture_days: 60,
              stressed_roi_ci95: [0.02, 0.31],
              max_stressed_drawdown_units: 8,
              paper_evidence_passed: true,
            },
          },
        ],
      },
    }),
  );
  await page.goto("/predictions");
  await page.getByRole("button", { name: "Paper trials" }).click();
  await expect(
    page.getByText(/Frozen cohort: 240 selections across 60 days/),
  ).toBeVisible();
  await expect(page.getByText(/2.00% to 31.00%/)).toBeVisible();
  await expect(
    page.getByText(/Executable profit remains unverified/),
  ).toBeVisible();
});

test("real pipeline responses render fixtures and performance", async ({
  page,
}) => {
  test.skip(
    process.env.RUN_PREDICTION_DB_TESTS !== "1",
    "Opt-in local pipeline database and saved model integration",
  );
  test.setTimeout(60000);
  const python = execFileSync(
    "py",
    ["-3", "-c", "import sys; print(sys.executable)"],
    { encoding: "utf8", windowsHide: true },
  ).trim();
  const server = spawn(
    python,
    ["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "5564"],
    {
      cwd: fileURLToPath(new URL("../../pipeline/", import.meta.url)),
      stdio: "ignore",
      windowsHide: true,
    },
  );
  const base = "http://127.0.0.1:5564";
  try {
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt++) {
      if (server.exitCode !== null)
        throw new Error("Isolated API exited before startup");
      try {
        ready = (
          await fetch(`${base}/api/v1/sport-models`, {
            signal: AbortSignal.timeout(1000),
          })
        ).ok;
      } catch {
        /* Startup pending. */
      }
      if (ready) break;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    expect(ready).toBe(true);
    await page.route("**/api/v1/**", async (route) => {
      const url = new URL(route.request().url());
      if (
        url.pathname.includes("/prediction-dashboard/") ||
        url.pathname.includes("/predictions/")
      ) {
        const response = await route.fetch({
          url: `${base}${url.pathname.replace('/api/v1/pipeline/', '/api/v1/')}${url.search}`,
        });
        await route.fulfill({ response });
      } else await route.fallback();
    });
    const performance = await (
      await fetch(`${base}/api/v1/predictions/accuracy-data?days=30`)
    ).json();
    await page.goto("/predictions");
    await expect(page.locator(".pd-forecast").first()).toBeVisible();
    await expect(
      page.locator(".pd-forecast").first().getByText("Draw", { exact: true }),
    ).toBeVisible();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: "../stages/03-build/output/predictions-ui-live.png",
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Bookmaker grid", exact: true })
      .click();
    const liveGrid = await (
      await fetch(
        `${base}/api/v1/prediction-dashboard/fixtures?page=1&page_size=20`,
      )
    ).json();
    await expect(page.locator(".bc-table tbody tr")).toHaveCount(
      liveGrid.items.length,
    );
    const liveBooks = [
      ...new Set([
        ...liveGrid.bookmakers.map((book) => book.bookmaker),
        ...liveGrid.items.flatMap((item) =>
          item.market.quotes.map((item) => item.bookmaker),
        ),
      ]),
    ].sort((a, b) => a.localeCompare(b));
    await expect(page.locator(".bc-book")).toHaveCount(liveBooks.length);
    await expect(page.locator(".bc-brand")).toContainText("FootballHeritage");
    await page.screenshot({
      path: "../stages/03-build/output/bookmaker-grid-live.png",
      fullPage: true,
    });
    await page.getByLabel("Comparison metric").selectOption("ev");
    await expect(page.locator(".bc-book").first()).toContainText(
      "Estimated EV",
    );
    await page.getByRole("button", { name: "Settled performance" }).click();
    await expect(
      page.getByText("Pre-kickoff accuracy", { exact: true }),
    ).toBeVisible();
    await expect(page.locator(".pd-stat").nth(1).locator("strong")).toHaveText(
      String(performance.total_predictions),
    );
    await expect(
      page.getByText(
        new RegExp(
          `Missing kickoff dates: ${performance.excluded.unknown_kickoff + performance.excluded.unknown_kickoff_outside_date_window}`,
        ),
      ),
    ).toBeVisible();
    const paper = await (
      await fetch(`${base}/api/v1/prediction-dashboard/paper-trials`)
    ).json();
    expect(paper.profitable_edge_established).toBe(false);
    await page.getByRole("button", { name: "Paper trials" }).click();
    const study = paper.studies[0];
    await expect(
      page.getByText(
        `${study.settled_selections} / 200 settled selections · ${study.fixture_days} / 60 fixture days`,
      ),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Prospective paper trials" }),
    ).toBeVisible();
    await expect(page.getByText(/Soccer candidate/).first()).toBeVisible();
    await page.screenshot({
      path: "../stages/03-build/output/trial-automation-ui-20261010.png",
      fullPage: true,
    });
  } finally {
    await page.unrouteAll({ behavior: "wait" });
    await page.close();
    server.kill();
    if (server.exitCode === null)
      await new Promise((resolve) => server.once("exit", resolve));
  }
});
