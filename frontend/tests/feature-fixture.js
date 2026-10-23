// Explicit browser-test permissions. Never imported by application code.
export const featureAccess = {
  features: Object.fromEntries(
    [
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
    ].map((key) => [key, true]),
  ),
};

export function defaultApiFixture(route) {
  return route.fulfill({
    json:
      new URL(route.request().url()).pathname === "/api/v1/me/features"
        ? featureAccess
        : [],
  });
}
