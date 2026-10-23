import { featureAccess } from './feature-fixture.js';
import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { execFileSync, spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import process from "node:process";

// Explicit test responses; the application has no sample-data fallback.
const now = new Date().toISOString();
const user = {
  id: "admin-test",
  first_name: "Admin",
  email: "admin@example.test",
  is_admin: true,
  balance: 0,
};
const operations = {
  generated_at: now,
  active_model_version: "2.0.0",
  configured_bookmakers: 10,
  covered_bookmakers: 2,
  summary: {
    upcoming_fixtures: 38,
    current_forecasts: 28,
    fresh_quotes: 12,
    priced_fixtures: 10,
    compared_outcomes: 30,
    positive_ev_outcomes: 12,
    next_kickoff: now,
    latest_quote_at: now,
    latest_forecast_at: now,
  },
  competitions: [
    {
      competition: "Premier League",
      fixtures: 20,
      current_forecasts: 16,
      priced_fixtures: 8,
    },
    {
      competition: "UEFA Champions League",
      fixtures: 18,
      current_forecasts: 12,
      priced_fixtures: 2,
    },
  ],
  bookmakers: Array.from({ length: 10 }, (_, i) => ({
    bookmaker: `book${i}`,
    name: i === 0 ? "Bovada" : `Source ${i}`,
    fresh_quotes: i < 2 ? (i === 0 ? 8 : 4) : 0,
    fixtures: i < 2 ? 4 : 0,
    latest_quote_at: i < 2 ? now : null,
  })),
  collector: {
    outcome: "success",
    last_attempt_at: now,
    last_success_at: now,
    failed_steps: [],
  },
  latest_collection: {
    state: "available",
    completed_at: now,
    snapshot_count: 1190,
    sources_with_quotes: 2,
    sources_checked: 3,
    transport: "scrapling",
  },
};
const study = {
  study_id: "model-study",
  candidate_id: "test-candidate",
  policy: { selection: "largest_stressed_ev" },
  settled_selections: 6,
  pending_selections: 6,
  fixture_days: 2,
  batch_count: 3,
  roi: -0.04167,
  stressed_roi: -0.06,
  assessment_status: "collecting",
  protocol: { minimum_selections: 200, minimum_fixture_days: 60 },
};
const paper = {
  profitable_edge_established: false,
  collector: operations.collector,
  studies: [
    study,
    {
      ...study,
      study_id: "manual",
      policy: { selection: "user_selected" },
      settled_selections: 1,
      pending_selections: 99,
    },
  ],
  trials: [
    {
      candidate_id: "test-candidate",
      trial_sha256: "trial",
      policy: study.policy,
      pending_forecasts: 14,
      settled_selections: 0,
      roi: null,
      stressed_roi: null,
      fixtures: [],
    },
    {
      candidate_id: "manual",
      trial_sha256: "manual",
      policy: { selection: "user_selected" },
      pending_forecasts: 99,
      settled_selections: 1,
      roi: -1,
      stressed_roi: -1,
      fixtures: [],
    },
  ],
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript((admin) => {
    sessionStorage.setItem("token", "test-token");
    sessionStorage.setItem("betting_user_data", JSON.stringify(admin));
  }, user);
  await page.route("**/api/v1/**", (route) => {
    if (new URL(route.request().url()).pathname === "/api/v1/me/features") return route.fulfill({ json: featureAccess });
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/prediction-dashboard/operations"))
      return route.fulfill({ json: operations });
    if (path.endsWith("/prediction-dashboard/paper-trials"))
      return route.fulfill({ json: paper });
    if (path.endsWith("/user/profile")) return route.fulfill({ json: user });
    return route.fulfill({ json: [] });
  });
});

test("live metrics, source filters, export, and paper ledger navigation", async ({
  page,
}) => {
  await page.goto("/admin/dashboard");
  await expect(
    page.getByRole("heading", { name: "Operations overview." }),
  ).toBeVisible();
  await expect(page.locator(".ops-metric").nth(0).locator("strong")).toHaveText(
    "38",
  );
  await expect(page.locator(".ops-metric").nth(1).locator("strong")).toHaveText(
    "2 / 10",
  );
  await expect(page.locator(".ops-metric").nth(3).locator("strong")).toHaveText(
    "6",
  );
  await expect(
    page.getByText("14 forecasts awaiting final results"),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Paper trial progress" }),
  ).toContainText("-4.17%");
  await expect(
    page.getByRole("region", { name: "Collection health" }),
  ).toContainText("Last collection completed");
  await expect(page.getByText("user1@example.com")).toHaveCount(0);
  await page.getByLabel("Search sportsbooks").fill("bovada");
  await expect(page.locator(".ops-table tbody tr")).toHaveCount(1);
  await page.getByLabel("Search sportsbooks").fill("");
  await page.getByLabel("Filter sportsbook coverage").selectOption("missing");
  await page.getByRole("button", { name: "Show all sources" }).click();
  await expect(page.locator(".ops-table tbody tr")).toHaveCount(8);
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export snapshot" }).click();
  const download = await downloadPromise;
  const exported = JSON.parse(readFileSync(await download.path(), "utf8"));
  expect(exported.operations.summary.upcoming_fixtures).toBe(38);
  expect(exported.paper_trials.trials).toHaveLength(2);
  await page.getByRole("link", { name: "View ledger" }).click();
  await expect(page).toHaveURL(/\/predictions\?view=trials/);
  await expect(
    page.getByRole("heading", { name: "Prospective paper trials" }),
  ).toBeVisible();
});

test("one unavailable service does not hide the other and can be retried", async ({
  page,
}) => {
  let failing = true;
  await page.route("**/prediction-dashboard/operations", (route) =>
    failing
      ? route.fulfill({
          status: 503,
          json: { detail: "Operations overview is unavailable" },
        })
      : route.fulfill({ json: operations }),
  );
  await page.goto("/admin/dashboard");
  await expect(page.getByRole("alert")).toContainText("operations unavailable");
  await expect(
    page.locator(".ops-metric").first().locator("strong"),
  ).toHaveText("—");
  await expect(page.locator(".ops-metric").nth(3).locator("strong")).toHaveText(
    "6",
  );
  await expect(
    page.getByRole("button", { name: "Export snapshot" }),
  ).toBeDisabled();
  failing = false;
  await page.getByRole("button", { name: "Retry operations" }).click();
  await expect(
    page.locator(".ops-metric").first().locator("strong"),
  ).toHaveText("38");
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("refresh failure preserves last good metrics and marks cached data", async ({
  page,
}) => {
  let failing = false;
  await page.route("**/prediction-dashboard/operations", (route) =>
    failing
      ? route.fulfill({
          status: 503,
          json: { detail: "Temporarily unavailable" },
        })
      : route.fulfill({ json: operations }),
  );
  await page.goto("/admin/dashboard");
  await expect(
    page.getByRole("button", { name: "Refresh data" }),
  ).toBeEnabled();
  failing = true;
  await page.getByRole("button", { name: "Refresh data" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Showing the last successful response",
  );
  await expect(
    page.locator(".ops-metric").first().locator("strong"),
  ).toHaveText("38");
});

test("mobile overview fits the viewport and menu remains usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/admin/dashboard");
  await expect(
    page.locator(".ops-metric").first().locator("strong"),
  ).toHaveText("38");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: "../stages/03-build/output/admin-operations-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Toggle admin menu" }).click();
  await expect(
    page.getByRole("navigation", { name: "Admin navigation" }),
  ).toBeVisible();
});

test("ordinary users cannot open the admin overview", async ({ page }) => {
  await page.addInitScript(() =>
    sessionStorage.setItem(
      "betting_user_data",
      JSON.stringify({ id: "ordinary", is_admin: false }),
    ),
  );
  await page.goto("/admin/dashboard");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.locator(".ops-dashboard")).toHaveCount(0);
});

test("real operational evidence renders with database-backed paper trials", async ({
  page,
}) => {
  test.skip(
    process.env.RUN_PREDICTION_DB_TESTS !== "1",
    "Opt-in local database integration",
  );
  test.setTimeout(90000);
  const python = execFileSync(
    "py",
    ["-3", "-c", "import sys; print(sys.executable)"],
    { encoding: "utf8", windowsHide: true },
  ).trim();
  const server = spawn(
    python,
    ["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "5567"],
    {
      cwd: fileURLToPath(new URL("../../pipeline/", import.meta.url)),
      stdio: "ignore",
      windowsHide: true,
    },
  );
  const base = "http://127.0.0.1:5567";
  try {
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt++) {
      if (server.exitCode !== null)
        throw new Error("Isolated operations API failed to start");
      try {
        ready = (
          await fetch(`${base}/api/v1/prediction-dashboard/operations`, {
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
    const evidence = await (
      await fetch(`${base}/api/v1/prediction-dashboard/operations`)
    ).json();
    await page.route("**/prediction-dashboard/**", async (route) => {
      const url = new URL(route.request().url());
      const response = await route.fetch({
        url: `${base}${url.pathname}${url.search}`,
      });
      await route.fulfill({ response });
    });
    await page.goto("/admin/dashboard");
    await expect(
      page.locator(".ops-metric").first().locator("strong"),
    ).toHaveText(evidence.summary.upcoming_fixtures.toLocaleString());
    await expect(
      page
        .getByRole("region", { name: "Paper trial progress" })
        .locator(".ops-study")
        .first(),
    ).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await page.screenshot({
      path: "../stages/03-build/output/admin-operations-live.png",
      fullPage: true,
    });
  } finally {
    await page.unrouteAll({ behavior: "wait" });
    server.kill();
    if (server.exitCode === null)
      await new Promise((resolve) => server.once("exit", resolve));
  }
});
