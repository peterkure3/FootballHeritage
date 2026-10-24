import { loadEnv } from 'vite';
import { pathToFileURL } from 'node:url';
import { productionApiBase } from '../src/utils/apiUrl.js';

export function validateProductionEnv(env) {
  const base = productionApiBase(env.VITE_API_URL);
  if (Object.keys(env).some(key => /^VITE_.*(?:SECRET|TOKEN|PASSWORD|PRIVATE_KEY|API_KEY)$/.test(key))) {
    throw new Error('Secret-like VITE variables are forbidden: browser bundles are public.');
  }
  return base;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    validateProductionEnv({ ...loadEnv('production', process.cwd(), ''), ...process.env });
    console.log('Production frontend configuration validated.');
  } catch (error) {
    console.error(error.message);
    console.error('Set VITE_API_URL in the frontend Vercel project for the deployment scope (Preview or Production), including any branch override. The URL must point to the Rust API, not Vite or FastAPI.');
    process.exitCode = 1;
  }
}
