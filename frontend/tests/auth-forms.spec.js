import { test, expect } from "@playwright/test";

// Test-only API fixture. These presentation checks do not create real accounts.
test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/**", (route) => route.fulfill({ json: [] }));
});

for (const width of [1440, 900, 390]) {
  for (const route of ["login", "register"]) {
    test(`${route} form matches landing design at ${width}px`, async ({
      page,
    }, info) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(`/${route}`);
      await expect(page.getByRole("main")).toBeVisible();
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(
        route === "login" ? "Welcome back." : "Make the game yours.",
      );
      const styles = await page.locator(".fh-auth").evaluate((main) => ({
        background: getComputedStyle(main).backgroundColor,
        heading: getComputedStyle(main.querySelector("h1")).fontFamily,
        button: getComputedStyle(main.querySelector('button[type="submit"]'))
          .backgroundColor,
        inputSize: getComputedStyle(main.querySelector("input")).fontSize,
        overflow: document.documentElement.scrollWidth > window.innerWidth,
      }));
      expect(styles.background).toBe("rgb(244, 245, 238)");
      expect(styles.heading).toContain("Georgia");
      expect(styles.button).toBe("rgb(28, 81, 49)");
      expect(styles.inputSize).toBe("16px");
      expect(styles.overflow).toBe(false);
      await expect(page.locator('input[name="email"]')).toHaveAttribute(
        "autocomplete",
        "email",
      );
      if (route === "register") {
        const first = await page
          .locator('input[name="firstName"]')
          .boundingBox();
        const last = await page.locator('input[name="lastName"]').boundingBox();
        expect(
          width > 600 ? Math.abs(first.y - last.y) < 2 : last.y > first.y,
        ).toBe(true);
      }
      await page.screenshot({
        path: info.outputPath(`${route}-${width}.png`),
        fullPage: true,
      });
    });
  }
}

for (const route of ["login", "register"]) {
  test(`${route} password controls and inline errors are accessible`, async ({
    page,
  }) => {
    await page.goto(`/${route}`);
    const password = page.locator('input[name="password"]');
    await password.fill("TestOnly123!");
    await page
      .getByRole("button", { name: "Show password", exact: true })
      .click();
    await expect(password).toHaveAttribute("type", "text");
    const toggle = page.getByRole("button", {
      name: "Hide password",
      exact: true,
    });
    await password.focus();
    await page.keyboard.press("Tab");
    await expect(toggle).toBeFocused();
    expect(
      await toggle.evaluate((button) => getComputedStyle(button).outlineStyle),
    ).toBe("solid");
    await page.keyboard.press("Enter");
    await expect(password).toHaveAttribute("type", "password");
    if (route === "register") {
      await page
        .getByRole("button", { name: "Show confirm password", exact: true })
        .click();
      await expect(
        page.locator('input[name="confirmPassword"]'),
      ).toHaveAttribute("type", "text");
    }
    await password.fill("");
    await page.locator('button[type="submit"]').click();
    const email = page.locator('input[name="email"]');
    await expect(email).toHaveAttribute("aria-invalid", "true");
    await expect(email).toHaveAttribute("aria-describedby", "email-error");
    await expect(page.locator("#email-error")).toHaveAttribute("role", "alert");
    await expect(page.locator("#email-error")).toBeVisible();
    await expect(password).toHaveAttribute("aria-invalid", "true");
    if (route === "register") {
      await expect(page.locator('input[name="terms"]')).toHaveAttribute(
        "aria-describedby",
        "terms-error",
      );
      await expect(page.locator("#terms-error")).toBeVisible();
      await expect(page.locator('input[name="dob"]')).toHaveAttribute(
        "aria-describedby",
        "dob-hint dob-error",
      );
    }
  });
}
