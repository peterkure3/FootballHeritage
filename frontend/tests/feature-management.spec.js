import { expect, test } from "@playwright/test";

const flags = [
  "registration",
  "ai_picks",
  "ai_chat",
  "predictions",
  "intelligence",
  "best_picks",
  "player_props",
  "parlays",
  "betting",
  "wallet",
  "wallet_funding",
  "sports",
  "fpl",
  "college",
];

test("feature consumers share one request and one refresh timer", async ({ page }) => {
  await page.clock.install();
  let requests = 0;
  await page.route("**/api/v1/me/features", (route) => {
    requests += 1;
    return route.fulfill({
      json: { features: Object.fromEntries(flags.map((key) => [key, key !== "ai_chat"])) },
    });
  });
  await page.goto("/ai-picks/chat", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: "Feature unavailable" })).toBeVisible();
  expect(requests).toBe(1);
  await page.clock.fastForward(15001);
  await expect.poll(() => requests).toBe(2);
});

test("disabled feature hides navigation and blocks the direct route", async ({
  page,
}) => {
  await page.route("**/api/v1/me/features", (route) =>
    route.fulfill({
      json: {
        features: Object.fromEntries(flags.map((k) => [k, k !== "ai_chat"])),
      },
    }),
  );
  await page.route("**/api/v1/pipeline/matches?**", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.goto("/ai-picks/chat", { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("heading", { name: "Feature unavailable" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "AI Picks", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Chat", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Best picks", exact: true }),
  ).toBeVisible();
});

test("failed policy requests deny feature routes while login remains available", async ({
  page,
}) => {
  await page.route("**/api/v1/me/features", (route) =>
    route.fulfill({
      status: 503,
      json: { error: { message: "Policy unavailable" } },
    }),
  );
  await page.goto("/ai-picks/chat", { waitUntil: "domcontentloaded" });
  await expect(
    page.getByText("We could not verify access. Please try again."),
  ).toBeVisible();
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("button", { name: "Login", exact: true }),
  ).toBeVisible();
});

test("administrator confirms a feature change and sees its audit entry", async ({
  page,
}) => {
  let enabled = true;
  let changes = [];
  let roleEnabled = true;
  let overrides = {};
  await page.addInitScript(() => {
    sessionStorage.setItem("token", "test-token");
    sessionStorage.setItem(
      "betting_user_data",
      JSON.stringify({
        id: "admin-test",
        email: "admin@example.test",
        is_admin: true,
      }),
    );
  });
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/me/features")
      return route.fulfill({
        json: { features: Object.fromEntries(flags.map((k) => [k, true])) },
      });
    if (path === "/api/v1/admin/users")
      return route.fulfill({
        json: {
          users: [{ id: "selected-user", email: "selected@example.test" }],
        },
      });
    if (path === "/api/v1/admin/users/selected-user/features")
      return route.fulfill({
        json: { features: { wallet: enabled }, overrides },
      });
    if (path === "/api/v1/admin/users/selected-user/features/wallet") {
      overrides = { wallet: route.request().postDataJSON().enabled };
      return route.fulfill({ json: { success: true } });
    }
    if (path === "/api/v1/admin/features/wallet/roles/user") {
      roleEnabled = route.request().postDataJSON().enabled;
      return route.fulfill({ json: { success: true } });
    }
    if (path === "/api/v1/admin/features/audit")
      return route.fulfill({ json: changes });
    if (
      path === "/api/v1/admin/features/wallet" &&
      route.request().method() === "PATCH"
    ) {
      enabled = route.request().postDataJSON().enabled;
      changes = [
        {
          id: 1,
          administrator_id: "admin-test",
          action: "update",
          feature_key: "wallet",
          target: "global",
          before_value: true,
          after_value: enabled,
          created_at: new Date().toISOString(),
        },
      ];
      return route.fulfill({ json: { success: true } });
    }
    if (path === "/api/v1/admin/features")
      return route.fulfill({
        json: {
          features: [
            {
              key: "wallet",
              description: "Wallet balances and transactions",
              category: "Account",
              enabled,
              default_enabled: true,
              emergency_disabled: false,
              maintenance_allowed: false,
            },
          ],
          roles: [{ key: "wallet", role: "user", enabled: roleEnabled }],
        },
      });
    return route.fulfill({ json: [] });
  });
  await page.goto("/admin/features", { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("heading", { name: "Feature Management" }),
  ).toBeVisible();
  await page.getByLabel("Globally enabled", { exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(changes).toHaveLength(0);
  await page.getByRole("button", { name: "Confirm change" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByLabel("Globally enabled", { exact: true }),
  ).not.toBeChecked();
  await expect(
    page.getByRole("cell", { name: "admin-test", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Find user by email or name").fill("selected");
  await page
    .getByRole("combobox", { name: "Selected user", exact: true })
    .selectOption("selected-user");
  await page.getByLabel("Selected user override").selectOption("false");
  await page.getByRole("button", { name: "Confirm change" }).click();
  await expect(page.getByLabel("Selected user override")).toHaveValue("false");
  await page.getByLabel("user", { exact: true }).click();
  await page.getByRole("button", { name: "Confirm change" }).click();
  await expect(page.getByLabel("user", { exact: true })).not.toBeChecked();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("heading", { name: "Feature Management" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../stages/04-test/output/feature-management-mobile-20261022.png",
    fullPage: true,
  });
});
