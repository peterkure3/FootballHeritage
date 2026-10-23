// Inspect anonymous page loads and public fixture requests in isolated browsers.
import { chromium } from "playwright";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const [targetsFile, outputDirectory] = process.argv.slice(2);
if (!targetsFile || !outputDirectory)
  throw new Error(
    "Usage: node capture-bookmaker-network.mjs TARGETS.json OUTPUT_DIRECTORY",
  );
const targets = JSON.parse(await readFile(targetsFile, "utf8"));
await mkdir(outputDirectory, { recursive: false });
const browser = await chromium.launch({ headless: true });
const privateKey =
  /password|authorization|cookie|secret|api.?key|token|session|email|phone/i;
function scrub(value) {
  if (Array.isArray(value)) return value.map(scrub);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        privateKey.test(key) ? "<redacted>" : scrub(item),
      ]),
    );
  return value;
}
function safeURL(value) {
  const url = new URL(value);
  for (const key of url.searchParams.keys())
    if (privateKey.test(key)) url.searchParams.set(key, "<redacted>");
  return url.href;
}
async function inspect(target) {
  const report = {
    bookmaker: target.bookmaker,
    region: target.region ?? null,
    source_url: target.url,
    requests: [],
    scripts: [],
    failures: [],
  };
  if (!target.url) return { ...report, status: "source_verification_pending" };
  const directory = path.join(outputDirectory, target.bookmaker);
  await mkdir(directory);
  const context = await browser.newContext();
  context.setDefaultTimeout(10000);
  const page = await context.newPage();
  const pending = [];
  const seen = new Set();
  page.on("response", (response) => {
    const request = response.request();
    const type = request.resourceType();
    const identity = request.method() + " " + safeURL(request.url());
    if (seen.has(identity)) return;
    const ownScript =
      type === "script" &&
      new URL(request.url()).hostname === new URL(page.url()).hostname;
    const data =
      ["xhr", "fetch"].includes(type) &&
      /odds|sport|fixture|event|competition|league|market|match|offer|coupon|games|prematch/i.test(
        request.url(),
      );
    if (!ownScript && !data) return;
    if (
      (ownScript ? report.scripts.length : report.requests.length) >=
      (ownScript ? 8 : 60)
    )
      return;
    seen.add(identity);
    const item = {
      url: safeURL(request.url()),
      method: request.method(),
      status: response.status(),
      observed_at: new Date().toISOString(),
    };
    (ownScript ? report.scripts : report.requests).push(item);
    pending.push(
      (async () => {
        const headers = await request.allHeaders();
        item.headers = Object.fromEntries(
          Object.entries(headers)
            .filter(([key]) =>
              [
                "accept",
                "content-type",
                "origin",
                "referer",
                "x-pawa-brand",
                "x-pawa-language",
              ].includes(key),
            )
            .map(([key, value]) => [
              key,
              key === "referer" ? safeURL(value) : value,
            ]),
        );
        item.requires_session = Boolean(
          headers.authorization ||
          headers.cookie ||
          /<redacted>/.test(item.url),
        );
        if (request.postData()) {
          try {
            item.body = scrub(JSON.parse(request.postData()));
          } catch {
            item.body = "<non-JSON body; review required>";
          }
        }
        const body = await response.body();
        if (body.length > 8_000_000) {
          item.body_status = "exceeds_capture_limit";
          return;
        }
        if (ownScript) {
          item.capture = `script_${report.scripts.indexOf(item)}.js`;
          await writeFile(path.join(directory, item.capture), body);
        } else {
          try {
            const value = JSON.parse(body.toString("utf8"));
            item.shape = Array.isArray(value)
              ? "array"
              : Object.keys(value ?? {}).slice(0, 20);
            item.capture = `response_${report.requests.indexOf(item)}.json`;
            await writeFile(
              path.join(directory, item.capture),
              JSON.stringify(scrub(value), null, 2),
            );
          } catch {
            item.body_status = "not_JSON";
          }
        }
      })().catch((error) => {
        item.capture_error = error.name;
      }),
    );
  });
  page.on("requestfailed", (request) => {
    if (
      ["document", "xhr", "fetch"].includes(request.resourceType()) &&
      report.failures.length < 10
    )
      report.failures.push({
        url: safeURL(request.url()),
        error: request.failure()?.errorText,
      });
  });
  try {
    const response = await page.goto(target.url, {
      waitUntil: "domcontentloaded",
      timeout: 20000,
    });
    report.http_status = response?.status();
    await page.waitForTimeout(7000);
    report.final_url = safeURL(page.url());
    report.title = await page.title();
    report.visible_text = (await page.locator("body").innerText()).slice(
      0,
      2500,
    );
    report.status =
      /just a moment|access denied|verify you are human|blocked/i.test(
        report.title,
      )
        ? "access_challenge"
        : "inspected";
    try {
      await page.screenshot({
        path: path.join(directory, "page.png"),
        timeout: 10000,
      });
    } catch {
      report.screenshot_status = "unavailable";
    }
  } catch (error) {
    report.status = "navigation_failed";
    report.error_type = error.name;
  }
  await Promise.race([
    Promise.allSettled(pending),
    new Promise((resolve) => setTimeout(resolve, 10000)),
  ]);
  await context.close();
  await writeFile(
    path.join(directory, "network.json"),
    JSON.stringify(report, null, 2),
  );
  process.stdout.write(
    JSON.stringify({
      bookmaker: report.bookmaker,
      status: report.status,
      requests: report.requests.length,
      json: report.requests.filter((r) => r.capture).length,
    }) + "\n",
  );
  return report;
}
const reports = [];
try {
  for (let index = 0; index < targets.length; index += 2) {
    const results = await Promise.allSettled(
      targets.slice(index, index + 2).map(inspect),
    );
    for (let offset = 0; offset < results.length; offset++) {
      const result = results[offset];
      reports.push(
        result.status === "fulfilled"
          ? result.value
          : {
              bookmaker: targets[index + offset].bookmaker,
              status: "capture_failed",
              error_type: result.reason?.name,
            },
      );
    }
    await writeFile(
      path.join(outputDirectory, "report.json"),
      JSON.stringify(reports, null, 2),
    );
  }
} finally {
  await browser.close();
}
