// Return destinations never leave this SPA or re-enter an authentication form.
export function safeReturnTo(value: unknown): string {
  if (
    typeof value !== "string" ||
    value.length > 2048 ||
    !value.startsWith("/") ||
    value.startsWith("//")
  )
    return "/dashboard";
  let decoded: string;
  try {
    decoded = decodeURIComponent(value);
  } catch {
    return "/dashboard";
  }
  if (
    /[\\\u0000-\u0020\u007f]/.test(decoded) ||
    decoded.startsWith("//") ||
    /%[0-9a-f]{2}/i.test(decoded)
  )
    return "/dashboard";
  const destination = new URL(decoded, "https://return.invalid");
  if (destination.origin !== "https://return.invalid") return "/dashboard";
  const path = destination.pathname.toLowerCase().replace(/\/+$/, "");
  if (path === "/login" || path === "/register") return "/dashboard";
  return value;
}
