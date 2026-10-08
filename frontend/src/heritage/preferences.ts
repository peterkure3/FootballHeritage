import { useSyncExternalStore } from "react";
import useAuthStore from "../stores/authStore";
const subscribe = (callback: () => void) => {
  window.addEventListener("storage", callback);
  window.addEventListener("heritage-preferences", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("heritage-preferences", callback);
  };
};
export function usePreferences(kind: "stories" | "teams") {
  const { user, isAuthenticated } = useAuthStore();
  const key =
    isAuthenticated && user?.id != null ? `fh:${user.id}:${kind}` : "";
  const snapshot = useSyncExternalStore(
    subscribe,
    () => {
      try {
        return key ? localStorage.getItem(key) || "[]" : "[]";
      } catch {
        return "[]";
      }
    },
    () => "[]",
  );
  let values: string[] = [];
  try {
    const parsed: unknown = JSON.parse(snapshot);
    if (Array.isArray(parsed))
      values = parsed.filter(
        (value): value is string => typeof value === "string",
      );
  } catch {
    /* Ignore corrupt device preferences. */
  }
  const toggle = (value: string) => {
    if (!key) return;
    const next = values.includes(value)
      ? values.filter((item) => item !== value)
      : [...values, value];
    try {
      localStorage.setItem(key, JSON.stringify(next));
      window.dispatchEvent(new Event("heritage-preferences"));
    } catch {
      window.alert(
        "Device storage is unavailable; this preference could not be saved.",
      );
    }
  };
  return { values, toggle, authenticated: !!key };
}
