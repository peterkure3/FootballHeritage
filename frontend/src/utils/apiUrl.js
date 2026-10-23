export function apiBase(value) {
  const base = String(value || "")
    .trim()
    .replace(/\/+$/, "")
    .replace(/(?:\/api\/v1)+$/, "");
  if (!base) throw new Error("API URL must be configured");
  return `${base}/api/v1`;
}
