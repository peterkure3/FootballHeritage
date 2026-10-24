export function apiBase(value) {
  const base = String(value || "")
    .trim()
    .replace(/\/+$/, "")
    .replace(/(?:\/api\/v1)+$/, "");
  if (!base) throw new Error("API URL must be configured");
  return `${base}/api/v1`;
}

export function productionApiBase(value) {
  if (!value || !String(value).trim()) {
    throw new Error('VITE_API_URL is required for production builds.');
  }
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error('VITE_API_URL must be a valid HTTPS API URL.');
  }
  if (url.protocol !== 'https:' || !url.hostname
    || ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
    || url.username || url.password || url.search || url.hash
    || !['', '/', '/api/v1', '/api/v1/'].includes(url.pathname)) {
    throw new Error('VITE_API_URL must be a public HTTPS API origin or its /api/v1 URL, without credentials, query strings or fragments.');
  }
  return apiBase(value);
}
