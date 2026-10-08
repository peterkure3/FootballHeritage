// Opt-in local integration test: creates ONE isolated account using the real forms.
// Credentials exist only in memory. No mocks, bets, deposits or provider calls.
import { chromium } from "playwright";
import { randomBytes, randomUUID } from "node:crypto";
import assert from "node:assert/strict";

if (process.env.LIVE_AUTH_WRITE !== "1") {
  console.log(
    "Not run: set LIVE_AUTH_WRITE=1 to permit creation of one local test account.",
  );
  process.exit(0);
}
const origin = process.env.LIVE_UI_ORIGIN || "http://localhost:3000";
const rustApi = process.env.LIVE_RUST_API || "http://localhost:8888/api/v1";
assert.ok(
  ["localhost", "127.0.0.1"].includes(new URL(origin).hostname),
  "Only local frontend testing is permitted.",
);
assert.ok(
  ["localhost", "127.0.0.1"].includes(new URL(rustApi).hostname),
  "Only local API testing is permitted.",
);
assert.equal(
  (await fetch(`${rustApi.replace(/\/api\/v1\/?$/, "")}/health`)).status,
  200,
);
const email = `landing-qa-${Date.now()}-${randomUUID().slice(0, 8)}@example.test`;
const password = `Qa!9-${randomBytes(24).toString("hex")}`;
const browser = await chromium.launch();
let accountId;
try {
  const page = await browser.newPage();
  await page.goto(origin);
  await page
    .getByRole("link", { name: "Create your account", exact: true })
    .click();
  await page.locator('input[name="firstName"]').fill("LandingQA");
  await page.locator('input[name="lastName"]').fill("LocalTest");
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  await page.locator('input[name="confirmPassword"]').fill(password);
  await page.locator('input[name="dob"]').fill("1990-01-01");
  await page.locator('input[name="terms"]').check();
  await page.locator('button[type="submit"]').click();
  const registration = page.waitForResponse(
    (response) => response.url() === `${rustApi}/auth/register`,
    { timeout: 30000 },
  );
  await page.getByRole("button", { name: "I Confirm - Proceed" }).click();
  const registerResponse = await registration;
  assert.equal(
    registerResponse.status(),
    201,
    `Real registration failed; isolated account email: ${email}`,
  );
  accountId = (await registerResponse.json()).user.id;
  await page.waitForURL(`${origin}/dashboard`);
  await page.getByRole("heading", { name: /Welcome back/ }).waitFor();
  await page.getByRole("button", { name: "Account for LandingQA" }).click();
  await page
    .locator("#menu-account")
    .getByRole("button", { name: "Log out", exact: true })
    .click();
  await page.waitForURL(`${origin}/login`);
  await page.goto(`${origin}/login?returnTo=${encodeURIComponent("/profile")}`);
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(password);
  const login = page.waitForResponse(
    (response) => response.url() === `${rustApi}/auth/login`,
    { timeout: 30000 },
  );
  await page.locator('button[type="submit"]').click();
  assert.equal((await login).status(), 200);
  await page.waitForURL(`${origin}/profile`);
  await page.reload();
  await page.waitForURL(`${origin}/profile`);
  await page.getByRole("button", { name: "Account for LandingQA" }).waitFor();
  console.log(
    JSON.stringify(
      {
        registration: 201,
        defaultRedirect: "/dashboard",
        login: 200,
        validatedReturn: "/profile",
        refresh: "authenticated",
        accountId,
        testEmail: email,
        note: "One isolated dev account retained for manual removal; no credentials logged and no wagers/deposits.",
      },
      null,
      2,
    ),
  );
} catch (error) {
  console.error(
    JSON.stringify({
      testEmail: email,
      accountId,
      note: "If registration created a record, remove only this isolated test account through approved administration.",
    }),
  );
  throw error;
} finally {
  await browser.close();
}
