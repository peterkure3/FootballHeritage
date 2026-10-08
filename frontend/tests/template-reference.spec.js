import { test, expect } from "@playwright/test";
import { createServer } from "node:http";
import { existsSync, readFileSync } from "node:fs";
import { resolve, extname, sep } from "node:path";
import { fileURLToPath } from "node:url";

// Serve the supplied, already-built reference locally for a visual/token cross-check.
// It is not imported into the application or substituted for production data.
const root = fileURLToPath(
  new URL(
    "../../footballheritage-ai-picks/footballheritage/dist/",
    import.meta.url,
  ),
);
const imageRoot = fileURLToPath(new URL("../public/images/", import.meta.url));
const photos = {
  "1522778119026-d647f0596c20": "stadium.jpg",
  "1574629810360-7efbbe195018": "football.jpg",
  "1546519638-68e109498ffc": "basketball.jpg",
  "1517466787929-bc90951d0974": "pitch.jpg",
  "1566577739112-5180d4bf9390": "nfl.jpg",
};
test("desktop visual tokens agree with supplied template", async ({
  page,
}, testInfo) => {
  test.skip(
    !existsSync(resolve(root, "index.html")),
    "The supplied reference build is not present.",
  );
  const server = createServer((req, res) => {
    const pathname = new URL(req.url, "http://localhost").pathname;
    const path = resolve(
      root,
      `.${pathname === "/" ? "/index.html" : pathname}`,
    );
    if (!path.startsWith(resolve(root) + sep) || !existsSync(path)) {
      res.writeHead(404);
      res.end();
      return;
    }
    const types = {
      ".html": "text/html",
      ".js": "application/javascript",
      ".css": "text/css",
    };
    res.setHeader(
      "Content-Type",
      types[extname(path)] || "application/octet-stream",
    );
    res.end(readFileSync(path));
  });
  await new Promise((resolveReady) =>
    server.listen(0, "127.0.0.1", resolveReady),
  );
  try {
    await page.setViewportSize({ width: 1440, height: 1000 });
    // Same template photos, served locally to avoid external network timing.
    await page.route("**/images.unsplash.com/**", (route) => {
      const photo = Object.entries(photos).find(([id]) =>
        route.request().url().includes(id),
      );
      return photo
        ? route.fulfill({
            contentType: "image/jpeg",
            body: readFileSync(resolve(imageRoot, photo[1])),
          })
        : route.abort();
    });
    const address = server.address();
    await page.goto(`http://127.0.0.1:${address.port}/`);
    await expect(page.locator(".intro h1")).toBeVisible();
    const reference = await page.evaluate(() => ({
      navbar: getComputedStyle(document.querySelector(".nav-header"))
        .backgroundColor,
      surface: getComputedStyle(document.documentElement).backgroundColor,
      heading: getComputedStyle(document.querySelector(".intro h1")).fontFamily,
      size: getComputedStyle(document.querySelector(".intro h1")).fontSize,
      gap: getComputedStyle(document.querySelector(".layout")).gap,
    }));
    await page.locator("img").evaluateAll(async (images) => {
      await Promise.all(
        images.map((image) => {
          image.loading = "eager";
          return image.decode().catch(() => {});
        }),
      );
    });
    await page.screenshot({
      path: testInfo.outputPath("supplied-template-desktop.png"),
      fullPage: true,
    });
    await page.route("**/api/v1/**", (route) => route.fulfill({ json: [] }));
    await page.goto("/app");
    await expect(page.locator(".fh-intro h1")).toBeVisible();
    const actual = await page.evaluate(() => ({
      navbar: getComputedStyle(document.querySelector(".fh-nav"))
        .backgroundColor,
      surface: getComputedStyle(document.documentElement).backgroundColor,
      heading: getComputedStyle(document.querySelector(".fh-intro h1"))
        .fontFamily,
      size: getComputedStyle(document.querySelector(".fh-intro h1")).fontSize,
      gap: getComputedStyle(document.querySelector(".fh-layout")).gap,
    }));
    expect(actual.navbar).toBe(reference.navbar);
    expect(actual.surface).toBe(reference.surface);
    expect(actual.heading).toContain("Georgia");
    expect(reference.heading).toContain("Georgia");
    expect(actual.size).toBe(reference.size);
    expect(actual.gap).toBe(reference.gap);
    await page.locator("img").evaluateAll(async (images) => {
      await Promise.all(
        images.map((image) => {
          image.loading = "eager";
          return image.decode().catch(() => {});
        }),
      );
    });
    await page.screenshot({
      path: testInfo.outputPath("integrated-desktop.png"),
      fullPage: true,
    });
  } finally {
    await new Promise((resolveClose) => server.close(resolveClose));
  }
});
