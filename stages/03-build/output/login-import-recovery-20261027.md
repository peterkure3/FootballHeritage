# Login import recovery — 2026-10-27

Root cause confirmed in the affected browser: `/src/pages/Login.jsx` returned HTTP 200 from memory cache with `Content-Type: text/html`, `Server: nginx/1.27.5`, and response date 2026-10-27 08:02:44 UTC. The active Vite server returned HTTP 200 text/javascript without an nginx header. Disabling cache in DevTools and reloading restored the login form, confirmed by the user. How the earlier nginx response entered this browser cache was not established.

A separate recovery defect was reproduced: ErrorBoundary's Try Again reset component state, but React.lazy retained the rejected module promise. Restoring network access did not recover the page.

Updated ErrorBoundary to reload the current URL when retrying recognized module/chunk loading errors. Ordinary render errors retain the existing boundary reset. Reload is user-triggered; no automatic reload loop is introduced.

Verification: Chromium regression test initially aborted the Login module, restored access, clicked Try Again, and verified the Login form and returnTo query survive. Failed before the fix; passed afterward. The test now reproduces the user's more specific evidence: an HTTP 200 text/html response for the module. Targeted ESLint and the production build (including TypeScript) passed. No authentication submission or database changes were performed.

Follow-up: direct requests to localhost and IPv6 loopback returned HTTP 200 text/javascript. Only one listener was found on port 5173 (IPv6 loopback). Repository search found no service-worker registration. Browser-control initialization failed, so the user supplied the affected browser's response headers. A hard reload alone did not resolve the issue; DevTools Disable cache plus reload did. Restarted only the verified local Vite process with `--force --port 5173 --strictPort`. A fresh browser check after restart confirmed HTTP 200 text/javascript and a visible login form. The HTML MIME-response regression test also passed.

Fallow was unavailable locally (`npx --no-install fallow --summary` reported a missing package); dependency tracing used repository search.
