import { featureAccess } from './feature-fixture.js';
import { test, expect } from "@playwright/test";

test.use({ timezoneId: "Africa/Kampala" });

const administrator = {
  id: "admin-test",
  first_name: "Alex",
  email: "admin@example.test",
  is_admin: true,
  balance: 0,
};
const metrics = {
  total_users: 19,
  new_users_today: 2,
  active_users_today: 4,
  total_bets_today: 7,
  bet_volume_today: 123.45,
  revenue_today: -12.5,
  live_events: 3,
  upcoming_events: 12,
};
const account = {
  id: "account-1",
  first_name: "Test",
  last_name: "Member",
  email: "member@example.test",
  role: "user",
  is_active: true,
  is_verified: false,
  total_bets: 8,
};
const event = {
  id: "event-1",
  home_team: "Arsenal",
  away_team: "Chelsea",
  league: "Premier League",
  sport: "SOCCER",
  status: "UPCOMING",
  event_date: "2026-10-20T18:00:00Z",
  home_score: null,
  away_score: null,
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript((user) => {
    sessionStorage.setItem("token", "admin-test-token");
    sessionStorage.setItem("betting_user_data", JSON.stringify(user));
  }, administrator);
  await page.route("**/api/v1/**", (route) => {
    if (new URL(route.request().url()).pathname === "/api/v1/me/features") return route.fulfill({ json: featureAccess });
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/user/profile"))
      return route.fulfill({ json: administrator });
    if (path.endsWith("/analytics/dashboard"))
      return route.fulfill({ json: metrics });
    if (path.endsWith("/admin/users"))
      return route.fulfill({
        json: {
          users: [account],
          total: 26,
          page: 1,
          total_pages: 2,
          limit: 25,
        },
      });
    if (path.endsWith("/audit-logs"))
      return route.fulfill({
        json: {
          logs: [
            {
              id: "log-1",
              admin_email: "admin@example.test",
              action: "verify_user",
              target_type: "user",
              target_id: "account-1",
              created_at: "2026-10-15T06:00:00Z",
            },
          ],
        },
      });
    if (path.endsWith("/fraud-alerts"))
      return route.fulfill({ json: { alerts: [] } });
    if (path.endsWith("/admin/events"))
      return route.fulfill({ json: { events: [event], count: 1 } });
    return route.fulfill({ json: {} });
  });
});

test("sidebar collapse preserves accessible links and destinations", async ({
  page,
}) => {
  await page.goto("/admin/analytics");
  const nav = page.getByRole("navigation", { name: "Admin navigation" });
  await expect(
    nav.getByRole("link", { name: "Statistics", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    nav.getByRole("link", { name: "Sportsbook odds" }),
  ).toHaveAttribute("href", "/predictions?view=comparisons");
  await expect(
    nav.getByRole("link", { name: "Probabilities & EV" }),
  ).toHaveAttribute("href", "/predictions?view=fixtures");
  await expect(nav.getByRole("link", { name: "Paper trials" })).toHaveAttribute(
    "href",
    "/predictions?view=trials",
  );
  await expect(page.getByText("Full Access")).toHaveCount(0);
  await page.getByRole("button", { name: "Collapse sidebar" }).click();
  await expect(page.locator("#admin-sidebar")).toHaveCSS("width", "76px");
  await nav.getByRole("link", { name: "Revenue", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Revenue overview." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Expand sidebar" }).click();
  await expect(page.locator("#admin-sidebar")).toHaveCSS("width", "248px");
  const sidebarBox = await page.locator("#admin-sidebar").boundingBox();
  const mainBox = await page.locator(".admin-shell main").boundingBox();
  expect(sidebarBox.x).toBe(0);
  expect(mainBox.x).toBeGreaterThanOrEqual(sidebarBox.x + sidebarBox.width);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../stages/03-build/output/admin-pages-desktop.png",
    fullPage: false,
    animations: "disabled",
  });
});

test("mobile sidebar traps focus, closes with Escape and after navigation", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/admin/analytics");
  const toggle = page.getByRole("button", { name: "Toggle admin menu" });
  await expect(
    page.getByRole("navigation", { name: "Admin navigation" }),
  ).not.toBeVisible();
  await toggle.click();
  await expect(
    page.getByRole("button", { name: "Close sidebar", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(
    page.getByRole("link", { name: "Preferences", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(toggle).toBeFocused();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await expect(page.locator("#admin-sidebar")).toHaveCSS("transform", "none");
  await page.screenshot({
    path: "../stages/03-build/output/admin-sidebar-mobile.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Users", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "User management." }),
  ).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("statistics and revenue render live values and truthful errors", async ({
  page,
}) => {
  await page.goto("/admin/analytics");
  await expect(page.locator(".admin-metrics article").first()).toContainText(
    "19",
  );
  await page.goto("/admin/revenue");
  await expect(page.locator(".admin-metrics")).toContainText("123.45");
  await expect(page.locator(".admin-metrics")).toContainText("-12.50");
  await expect(page.getByText("$45,678.90")).toHaveCount(0);
  await page.route("**/admin/analytics/dashboard", (route) =>
    route.fulfill({
      status: 503,
      json: { error: "Metrics service unavailable" },
    }),
  );
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Metrics service unavailable",
  );
  await expect(page.locator(".admin-metrics")).toContainText("123.45");
});

test("user filters and pagination reach the API; changes require successful backend response", async ({
  page,
}) => {
  await page.goto("/admin/users");
  await expect(
    page.getByText("member@example.test", { exact: true }),
  ).toBeVisible();
  const search = page.waitForRequest(
    (request) =>
      request.url().includes("/admin/users?") &&
      new URL(request.url()).searchParams.get("search") === "O'Brien",
  );
  await page.getByLabel("Search users").fill("O'Brien");
  await search;
  const next = page.waitForRequest(
    (request) =>
      request.url().includes("/admin/users?") &&
      new URL(request.url()).searchParams.get("page") === "2",
  );
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await next;
  await page.getByRole("button", { name: "Suspend", exact: true }).click();
  await page.getByLabel("Reason").fill("Review requested");
  await page.route("**/users/account-1/status", (route) => {
    expect(route.request().postDataJSON()).toEqual({
      is_active: false,
      reason: "Review requested",
    });
    return route.fulfill({
      status: 503,
      json: { error: "Update unavailable" },
    });
  });
  await page.getByRole("button", { name: "Confirm suspend" }).click();
  await expect(page.getByRole("dialog")).toContainText("Update unavailable");
  await expect(page.getByText("Account updated successfully.")).toHaveCount(0);
  await page.route("**/users/account-1/status", (route) =>
    route.fulfill({ json: { success: true } }),
  );
  await page.getByRole("button", { name: "Confirm suspend" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByText("Account updated successfully.")).toBeVisible();
});

test("audit log uses recorded actions and searchable targets", async ({
  page,
}) => {
  await page.goto("/admin/logs");
  await expect(page.getByRole("table")).toContainText("verify_user");
  await expect(
    page.getByRole("region", { name: "Pending fraud alerts" }),
  ).toContainText("No pending alerts");
  await page.getByLabel("Search audit logs").fill("not-recorded");
  await expect(page.getByText("No actions match your search.")).toBeVisible();
  await expect(page.getByText("john_doe")).toHaveCount(0);
});

test("events retain edit forms, send filters, and show failed deletions", async ({
  page,
}) => {
  await page.goto("/admin/events");
  await expect(page.getByRole("table")).toContainText("Arsenal v Chelsea");
  await expect(page.getByRole("table")).toContainText("—");
  const filtered = page.waitForRequest(
    (request) =>
      request.url().includes("/admin/events?") &&
      new URL(request.url()).searchParams.get("status") === "UPCOMING",
  );
  await page.getByLabel("Event status").selectOption("UPCOMING");
  await filtered;
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Edit Event" })).toBeVisible();
  await expect(page.locator('input[type="datetime-local"]')).toHaveValue(
    "2026-10-20T21:00",
  );
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await page.route("**/admin/events/event-1", (route) =>
    route.fulfill({ status: 409, json: { error: "Event has active bets" } }),
  );
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("Event has active bets");
  await expect(page.getByRole("table")).toContainText("Arsenal v Chelsea");
});

test("bet management accurately reports disabled backend actions", async ({
  page,
}) => {
  await page.goto("/admin/bets");
  await expect(
    page.getByText("Bet administration is unavailable."),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /settle|void/i })).toHaveCount(
    0,
  );
  await expect(page.getByText("user1@example.com")).toHaveCount(0);
});

test("preferences persist assistant shortcut visibility", async ({ page }) => {
  await page.goto("/admin/settings");
  const preference = page.getByRole("checkbox", {
    name: "Show the SportsGPT shortcut",
  });
  await preference.uncheck();
  await expect(page.locator(".admin-chat-launcher")).toHaveCount(0);
  await page.reload();
  await expect(preference).not.toBeChecked();
  await preference.check();
  await expect(page.locator(".admin-chat-launcher")).toBeVisible();
  await expect(page.getByText("Two-Factor Authentication")).toHaveCount(0);
});

test("SportsGPT quick prompts use the actual prompt and retries reuse the request", async ({
  page,
}) => {
  const bodies = [];
  await page.route("**/ai-picks/chat", (route) => {
    bodies.push(route.request().postDataJSON());
    if (bodies.length === 1)
      return route.fulfill({
        status: 503,
        json: { error: "Assistant temporarily unavailable" },
      });
    return route.fulfill({
      json: {
        conversation_id: "conversation-1",
        reply: {
          reply: "EV uses the model probability and the quoted decimal odds.",
        },
      },
    });
  });
  await page.goto("/admin/sportsgpt");
  await page
    .getByRole("button", {
      name: "Explain expected value and bookmaker margin",
    })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Assistant temporarily unavailable",
  );
  expect(bodies[0].messages.at(-1).content).toBe(
    "Explain expected value and bookmaker margin",
  );
  await page.getByRole("button", { name: "Retry response" }).click();
  await expect(page.getByRole("log")).toContainText(
    "EV uses the model probability",
  );
  expect(bodies[1].request_id).toBe(bodies[0].request_id);
  await expect(
    page.locator('.admin-chat-message[data-role="user"]'),
  ).toHaveCount(1);
});
