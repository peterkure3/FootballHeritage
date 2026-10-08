// Read-only live-service check: no API mocks, account creation or financial writes.
// Start `npm run preview -- --host localhost --port 3000`, or set LIVE_UI_ORIGIN.
import { chromium } from "playwright";
import assert from "node:assert/strict";

const origin = process.env.LIVE_UI_ORIGIN || "http://localhost:3000";
const rustApi = process.env.LIVE_RUST_API || "http://localhost:8888/api/v1";
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  const runtimeErrors = [];
  page.on("pageerror", (error) => runtimeErrors.push(error.message));
  const fixturesResponse = page.waitForResponse(
    (response) => response.url().includes("/api/v1/matches?"),
    { timeout: 90000 },
  );
  page.on("requestfailed", (request) =>
    console.error(
      "Request failed:",
      request.url(),
      request.failure()?.errorText,
    ),
  );
  await page.goto(`${origin}/sport/football/scores`, {
    waitUntil: "domcontentloaded",
  });
  const response = await fixturesResponse;
  assert.equal(response.status(), 200);
  const fixtures = await response.json();
  assert.ok(
    Array.isArray(fixtures) && fixtures.length,
    "Live fixture data is required for this check.",
  );
  await page.locator(".fh-match").first().waitFor({ timeout: 30000 });
  assert.deepEqual(runtimeErrors, []);
  const protectedResponse = await page.request.get(`${rustApi}/ai-picks`);
  assert.equal(
    protectedResponse.status(),
    401,
    "AI Picks must reject unauthenticated reads.",
  );
  console.log(
    JSON.stringify(
      {
        fixtureApi: response.url(),
        returnedFixtures: fixtures.length,
        visibleMatches: await page.locator(".fh-match").count(),
        firstMatch: await page.locator(".fh-match").first().innerText(),
        unauthenticatedAiStatus: protectedResponse.status(),
        runtimeErrors,
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
