import { test, expect } from "@playwright/test";
import { existsSync, readFileSync } from "node:fs";

// Explicit test-only auth/data fixtures; live-service checks run separately.
const user = {
  id: "landing-test-user",
  first_name: "Landing",
  last_name: "Test",
  email: "landing@example.test",
  balance: 0,
};
test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/**", (route) => route.fulfill({ json: [] }));
  await page.route("**/user/profile", (route) => route.fulfill({ json: user }));
});

const landingCtas = [
  ["header logo", ".landing-nav .landing-brand", "/"],
  ["header Register", ".landing-nav .landing-register", "/register"],
  ["header Login", ".landing-nav .landing-login", "/login"],
  ["create account", ".landing-cta a:first-child", "/register"],
  ["explore FootballHeritage", ".landing-cta a:last-child", "/app"],
  ["explore platform", ".landing-ai-demo a", "/app"],
  ["join FootballHeritage", ".landing-final a", "/register"],
  ["footer logo", ".landing-footer-brand", "/"],
  ["footer Register", ".landing-footer>div a:first-child", "/register"],
  ["footer Login", ".landing-footer>div a:last-child", "/login"],
];
for (const width of [1440, 390]) {
  for (const route of ["login", "register"]) {
    test(`${route} uses only the landing account header at ${width}px`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`/${route}?returnTo=%2Fprofile`);
      const header = page.locator(".landing-auth-header");
      await expect(header).toBeVisible();
      await expect(header.locator("nav a")).toHaveText(["Register", "Login"]);
      await expect(
        page.getByRole("region", { name: "Scoreboard" }),
      ).toHaveCount(0);
      await expect(
        page.getByRole("navigation", { name: "Sports", exact: true }),
      ).toHaveCount(0);
      await expect(page.locator(".fh-subnav")).toHaveCount(0);
      await expect(page.locator('input[name="email"]')).toBeVisible();
      expect((await header.boundingBox()).height).toBeLessThan(150);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);

      const other = route === "login" ? "register" : "login";
      await header
        .getByRole("link", {
          name: other === "login" ? "Login" : "Register",
          exact: true,
        })
        .click();
      await expect(page).toHaveURL(`/${other}?returnTo=%2Fprofile`);
      await page.reload();
      await expect(page.locator(".landing-auth-header")).toBeVisible();
      await expect(
        page.getByRole("region", { name: "Scoreboard" }),
      ).toHaveCount(0);
      await page
        .getByRole("link", { name: "FootballHeritage home", exact: true })
        .click();
      await expect(page).toHaveURL("/");
      await page
        .getByRole("link", { name: "Explore FootballHeritage", exact: true })
        .click();
      await expect(page).toHaveURL("/app");
      await expect(
        page.getByRole("region", { name: "Scoreboard" }),
      ).toBeVisible();
      await expect(page.locator(".landing-auth-header")).toHaveCount(0);
    });
  }
}
for (const [label, selector, destination] of landingCtas) {
  test(`landing CTA: ${label}`, async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".fh-landing")).toBeVisible();
    await page.locator(selector).click();
    await expect(page).toHaveURL(destination);
    if (destination === "/register")
      await expect(page.locator('input[name="firstName"]')).toBeInViewport();
    if (destination === "/app") {
      await expect(
        page.getByRole("navigation", { name: "Sports", exact: true }),
      ).toBeVisible();
      await expect(page.locator(".landing-nav")).toHaveCount(0);
    }
  });
}
test("landing navigation is separate and browser history and refresh work", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("navigation", { name: "Sports", exact: true }),
  ).toHaveCount(0);
  await expect(page.locator(".landing-nav nav a")).toHaveText([
    "Register",
    "Login",
  ]);
  await page
    .getByRole("link", { name: "Explore FootballHeritage", exact: true })
    .click();
  await expect(page).toHaveURL("/app");
  await expect(
    page.getByRole("heading", {
      name: "A world of sport. A deeper perspective.",
    }),
  ).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL("/");
  await expect(page.locator(".fh-landing")).toBeVisible();
  await page.goForward();
  await expect(page).toHaveURL("/app");
  await expect(
    page.getByRole("heading", {
      name: "A world of sport. A deeper perspective.",
    }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", {
      name: "A world of sport. A deeper perspective.",
    }),
  ).toBeVisible();
});

test("landing keyboard order, visible focus and image fallback", async ({
  page,
}) => {
  await page.route("**/images/stadium.jpg", (route) => route.abort());
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator(".landing-nav .landing-brand")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.locator(".landing-nav .landing-register")).toBeFocused();
  expect(
    await page
      .locator(".landing-register")
      .evaluate((element) => getComputedStyle(element).outlineStyle),
  ).toBe("solid");
  await page.keyboard.press("Tab");
  await expect(page.locator(".landing-nav .landing-login")).toBeFocused();
  await expect(
    page.getByRole("img", { name: "Stadium image unavailable" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Create your account" }),
  ).toBeVisible();
  await expect(page.locator(".landing-ai")).toContainText(
    "Generation currently supports Football only",
  );
});

for (const width of [1440, 900, 390]) {
  test(`landing reference layout and contrast at ${width}px`, async ({
    page,
  }, info) => {
    await page.setViewportSize({ width, height: 960 });
    await page.goto("/");
    await page
      .locator(".landing-photo img")
      .evaluate((image) => image.decode());
    const visual = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > innerWidth,
      surface: getComputedStyle(document.querySelector(".fh-landing"))
        .backgroundColor,
      font: getComputedStyle(document.querySelector(".landing-hero h1"))
        .fontFamily,
      green: getComputedStyle(document.querySelector(".landing-register"))
        .backgroundColor,
      heroHeight: document
        .querySelector(".landing-photo")
        .getBoundingClientRect().height,
      muted: getComputedStyle(document.querySelector(".landing-hero-copy>p"))
        .color,
    }));
    expect(visual.overflow).toBe(false);
    expect(visual.surface).toBe("rgb(244, 245, 238)");
    expect(visual.green).toBe("rgb(28, 81, 49)");
    expect(visual.font).toContain("Georgia");
    expect(visual.heroHeight).toBe(
      width <= 600 ? 360 : width <= 850 ? 480 : 565,
    );
    const luminance = (color) =>
      color
        .match(/\d+/g)
        .slice(0, 3)
        .map(Number)
        .map((value) => {
          const v = value / 255;
          return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
        })
        .reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
    expect(
      (luminance(visual.surface) + 0.05) / (luminance(visual.muted) + 0.05),
    ).toBeGreaterThanOrEqual(4.5);
    const referencePath = new URL(
      "../../footballheritage-landing-template/footballheritage/src/landing.css",
      import.meta.url,
    );
    // Supplied ZIPs are local references, not required on a clean clone.
    // The actual UI color/layout/contrast assertions above always run.
    if (existsSync(referencePath)) {
      const reference = readFileSync(referencePath, "utf8");
      expect(reference).toContain("background:#f4f5ee");
      expect(reference).toContain("background:#1c5131");
      expect(reference).toContain("height:565px");
    }
    await page.screenshot({
      path: info.outputPath(`landing-${width}.png`),
      fullPage: true,
    });
  });
}

async function fillRegistration(page) {
  await page.locator('input[name="firstName"]').fill("Landing");
  await page.locator('input[name="lastName"]').fill("Test");
  await page.locator('input[name="email"]').fill(user.email);
  await page.locator('input[name="password"]').fill("TestOnly-Password123!");
  await page
    .locator('input[name="confirmPassword"]')
    .fill("TestOnly-Password123!");
  await page.locator('input[name="dob"]').fill("1990-01-01");
  await page.locator('input[name="terms"]').check();
}

test("registration upstream failure is visible and can be retried", async ({
  page,
}) => {
  let attempts = 0;
  await page.route("**/auth/register", (route) => {
    attempts++;
    return attempts === 1
      ? route.fulfill({
          status: 503,
          json: { error: "Registration service unavailable" },
        })
      : route.fulfill({
          status: 201,
          json: { token: "test-only-token", user },
        });
  });
  await page.goto("/register");
  await fillRegistration(page);
  await page.locator('button[type="submit"]').click();
  await page.getByRole("button", { name: "I Confirm - Proceed" }).click();
  await expect(
    page.getByText("Registration service unavailable", { exact: true }).first(),
  ).toBeVisible();
  await expect(page).toHaveURL("/register");
  await page.locator('button[type="submit"]').click();
  await page.getByRole("button", { name: "I Confirm - Proceed" }).click();
  await expect(page).toHaveURL("/dashboard");
  expect(attempts).toBe(2);
});

test("registration uses existing validation, age gate, payload and loading state", async ({
  page,
}) => {
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  let payload;
  await page.route("**/auth/register", async (route) => {
    payload = route.request().postDataJSON();
    await gate;
    await route.fulfill({
      status: 201,
      json: { token: "test-only-token", user },
    });
  });
  await page.goto("/register");
  await fillRegistration(page);
  await page.locator('input[name="confirmPassword"]').fill("Mismatch123!");
  await page.locator('button[type="submit"]').click();
  await expect(
    page.getByText("Passwords do not match", { exact: true }),
  ).toBeVisible();
  expect(payload).toBeUndefined();
  await page
    .locator('input[name="confirmPassword"]')
    .fill("TestOnly-Password123!");
  await page.locator('button[type="submit"]').click();
  await expect(
    page.getByRole("heading", { name: "Age Verification Required" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "I Confirm - Proceed" }).click();
  await expect(page.locator('button[type="submit"]')).toBeDisabled();
  expect(payload).toMatchObject({
    email: user.email,
    first_name: "Landing",
    last_name: "Test",
    date_of_birth: "1990-01-01",
  });
  release();
  await expect(page).toHaveURL("/dashboard");
});

test("login failure stays on the form with an error and retries safely", async ({
  page,
}) => {
  let attempts = 0;
  await page.route("**/auth/login", (route) => {
    attempts++;
    return attempts === 1
      ? route.fulfill({ status: 401, json: { error: "Invalid credentials" } })
      : route.fulfill({ json: { token: "test-only-token", user } });
  });
  await page.goto("/login?returnTo=%2Fai-picks");
  await page.locator('input[name="email"]').fill(user.email);
  await page.locator('input[name="password"]').fill("TestOnly-Password123!");
  await page.locator('button[type="submit"]').click();
  await expect(
    page.getByText("Invalid credentials", { exact: true }).first(),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/login\?/);
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL("/ai-picks");
  expect(attempts).toBe(2);
});

test("protected destination survives switching account forms and login", async ({
  page,
}) => {
  let attempts = 0;
  await page.route("**/auth/login", (route) => {
    attempts++;
    return route.fulfill({ json: { token: "test-only-token", user } });
  });
  await page.goto("/profile");
  await expect(page).toHaveURL("/login");
  await page.getByRole("link", { name: "Register here" }).click();
  await expect(page).toHaveURL("/register");
  await expect(page.locator('input[name="firstName"]')).toBeVisible();
  await page.getByRole("link", { name: /Login here/ }).click();
  await expect(page).toHaveURL("/login");
  await page.locator('input[name="email"]').fill(user.email);
  await page.locator('input[name="password"]').fill("TestOnly-Password123!");
  await expect(page.locator('input[name="email"]')).toHaveValue(user.email);
  await expect(page.locator('input[name="password"]')).toHaveValue(
    "TestOnly-Password123!",
  );
  await page.locator('button[type="submit"]').click();
  await expect.poll(() => attempts).toBe(1);
  await expect(page).toHaveURL("/profile");
});

test("authenticated visitors keep the landing and reject unsafe return URLs", async ({
  page,
}) => {
  test.setTimeout(60000);
  await page.addInitScript((user) => {
    sessionStorage.setItem("token", "test-only-token");
    sessionStorage.setItem("betting_user_data", JSON.stringify(user));
  }, user);
  await page.goto("/");
  await expect(page.locator(".fh-landing")).toBeVisible();
  await page.locator(".landing-nav .landing-login").click();
  await expect(page).toHaveURL("/dashboard");
  for (const unsafe of [
    "https://example.test",
    "//example.test",
    "/\\example.test",
    "/%2fexample.test",
    "/login",
    "/x/../register",
    "/%256cogin",
  ]) {
    await page.goto(`/login?returnTo=${encodeURIComponent(unsafe)}`);
    await expect(page).toHaveURL("/dashboard");
  }
  await page.goto("/register?returnTo=%2Fsport%2Ffootball%2Fscores");
  await expect(page).toHaveURL("/sport/football/scores");
});
