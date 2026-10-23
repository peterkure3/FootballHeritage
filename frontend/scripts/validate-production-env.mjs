import { loadEnv } from 'vite';

const env = { ...loadEnv('production', process.cwd(), ''), ...process.env };
const value = env.VITE_API_URL;
let valid = false;
try {
  const url = new URL(value);
  valid = url.protocol === 'https:' && !!url.hostname && !['localhost','127.0.0.1','[::1]'].includes(url.hostname)
    && !url.username && !url.password && !url.search && !url.hash
    && ['', '/', '/api/v1', '/api/v1/'].includes(url.pathname);
} catch { /* Fail without echoing configuration values. */ }
if (!valid) throw new Error('Set VITE_API_URL to the production HTTPS API origin or its /api/v1 URL.');
if (Object.keys(env).some(key => /^VITE_.*(?:SECRET|TOKEN|PASSWORD|PRIVATE_KEY|API_KEY)$/.test(key))) {
  throw new Error('Secret-like VITE variables are forbidden: browser bundles are public.');
}
console.log('Production frontend configuration validated.');
