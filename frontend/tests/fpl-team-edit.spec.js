import { defaultApiFixture } from './feature-fixture.js';
import { test, expect } from "@playwright/test";

const positions = [
  "GKP",
  "GKP",
  ...Array(5).fill("DEF"),
  ...Array(5).fill("MID"),
  ...Array(3).fill("FWD"),
];
const players = positions.map((position, index) => ({
  id: index + 1,
  web_name: `Player ${index + 1}`,
  team_name: `Club ${index % 5}`,
  position,
  price: 5,
  expected_points: 4,
  status: "a",
}));
const starterIds = [1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15];
const replacement = {
  ...players[12],
  id: 16,
  web_name: "Replacement",
  team_name: "New Club",
  price: 6,
};
const team = {
  players,
  starting_xi: players.filter((p) => starterIds.includes(p.id)),
  bench: players.filter((p) => !starterIds.includes(p.id)),
  captain: players[12],
  vice_captain: players[13],
  total_cost: 75,
  budget_remaining: 25,
  expected_points: 48,
  formation: { DEF: 3, MID: 4, FWD: 3 },
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("token")) {
      sessionStorage.setItem("token", "test-token");
      sessionStorage.setItem(
        "betting_user_data",
        JSON.stringify({ id: "fpl-user", email: "fpl@example.com" }),
      );
    }
  });
  await page.route("**/api/v1/**", defaultApiFixture);
  await page.route("**/user/profile", (route) =>
    route.fulfill({ json: { id: "fpl-user", email: "fpl@example.com" } }),
  );
  await page.route("**/fpl/advice", (route) =>
    route.fulfill({ json: { gameweek: 9, optimal_team: team } }),
  );
  await page.route("**/fpl/players?*", (route) =>
    route.fulfill({ json: [...players, replacement] }),
  );
});

for (const width of [1440, 390]) {
  test(`edit, save, reload, cancel and reset a team at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    let submitted;
    await page.route("**/fpl/team/evaluate", (route) => {
      submitted = route.request().postDataJSON();
      const selected = [...players, replacement].filter((p) =>
        submitted.squad_ids.includes(p.id),
      );
      return route.fulfill({
        json: {
          ...team,
          players: selected,
          starting_xi: selected.filter((p) =>
            submitted.starter_ids.includes(p.id),
          ),
          bench: selected.filter((p) => !submitted.starter_ids.includes(p.id)),
          captain: selected.find((p) => p.id === submitted.captain_id),
          vice_captain: selected.find(
            (p) => p.id === submitted.vice_captain_id,
          ),
          total_cost: 76,
          budget_remaining: 24,
        },
      });
    });
    await page.goto("/fpl-advisor");
    await page.getByRole("button", { name: "Edit team", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Edit team", exact: true });
    await dialog.getByLabel("Find replacements").fill("Replacement");
    await dialog
      .getByLabel("Replace Player 13", { exact: true })
      .selectOption("16");
    await expect(dialog).toContainText("Cost: £76.0m");
    await dialog.getByLabel("Captain", { exact: true }).selectOption("14");
    await dialog.getByLabel("Vice-captain", { exact: true }).selectOption("16");
    const bounds = await dialog.boundingBox();
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    await dialog
      .getByRole("button", { name: "Save team", exact: true })
      .click();
    await expect(dialog).toHaveCount(0);
    expect(submitted.squad_ids).toContain(16);
    expect(submitted.squad_ids).not.toContain(13);
    expect(submitted.captain_id).toBe(14);
    expect(submitted.vice_captain_id).toBe(16);
    await expect(page.locator(".fpl-team-toolbar")).toContainText("My team");
    await expect(page.locator(".fpl-pitch")).toContainText("Replacement");
    await page.reload();
    await expect(page.locator(".fpl-pitch")).toContainText("Replacement");
    await page.getByRole("button", { name: "Edit team", exact: true }).click();
    await dialog
      .getByLabel("Replace Replacement", { exact: true })
      .selectOption("13");
    await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(page.locator(".fpl-pitch")).toContainText("Replacement");
    await page
      .getByRole("button", { name: "Use suggested team", exact: true })
      .click();
    await expect(page.locator(".fpl-team-toolbar")).toContainText(
      "Suggested team",
    );
    await expect(page.locator(".fpl-pitch")).not.toContainText("Replacement");
    await page.reload();
    await expect(page.locator(".fpl-team-toolbar")).toContainText(
      "Suggested team",
    );
  });
}

test("invalid draft stays open and catalog failures can retry", async ({
  page,
}) => {
  await page.route("**/fpl/players?*", (route) =>
    route.fulfill({ status: 503, json: {} }),
  );
  await page.route("**/fpl/team/evaluate", (route) =>
    route.fulfill({
      status: 422,
      json: { detail: "Select 11 different starters from your squad." },
    }),
  );
  await page.goto("/fpl-advisor");
  await page.getByRole("button", { name: "Edit team", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Edit team", exact: true });
  await expect(dialog.getByRole("alert")).toContainText(
    "Could not load players",
  );
  await expect(
    dialog.getByRole("button", { name: "Save team", exact: true }),
  ).toBeDisabled();
  await page.route("**/fpl/players?*", (route) =>
    route.fulfill({ json: players }),
  );
  await dialog.getByRole("button", { name: "Retry", exact: true }).click();
  await dialog.getByLabel("Start Player 13", { exact: true }).uncheck();
  await dialog.getByRole("button", { name: "Save team", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText(
    "Select 11 different starters",
  );
  await expect(page.locator(".fpl-team-toolbar")).toContainText(
    "Suggested team",
  );
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Edit team", exact: true }),
  ).toBeFocused();
});
