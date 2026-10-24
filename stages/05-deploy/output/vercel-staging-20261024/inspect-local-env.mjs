// fallow-ignore-file unused-file -- Manual redacted inventory command, not application code.
// Prints names and validation flags only; never prints credentials or URL values.
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../../../', import.meta.url));
function readEnv(service) {
  const file = resolve(root, service, '.env');
  const entries = {};
  if (!existsSync(file)) return entries;
  for (const line of readFileSync(file, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)$/);
    if (!match) continue;
    entries[match[1]] = match[2].replace(/^(['"])(.*)\1$/, '$2');
  }
  return entries;
}
function databaseFlags(value, expected) {
  if (!value) return { configured: false };
  try {
    const url = new URL(value);
    return {
      configured: true,
      postgres_scheme: ['postgres:', 'postgresql:'].includes(url.protocol),
      expected_database: decodeURIComponent(url.pathname.slice(1)) === expected,
      neon_host: url.hostname.endsWith('.neon.tech'),
      pooled_host: url.hostname.includes('-pooler.'),
      tls_requested: ['require', 'verify-ca', 'verify-full'].includes(url.searchParams.get('sslmode')),
    };
  } catch { return { configured: true, valid_url: false }; }
}
const backend = readEnv('backend');
const pipeline = readEnv('pipeline');
const frontend = readEnv('frontend');
console.log(JSON.stringify({
  note: 'Local .env inventory only; not the hosted Vercel environment. No database connection made.',
  frontend: {
    keys: Object.keys(frontend).sort(),
    api_url_configured: Boolean(frontend.VITE_API_URL),
    api_url_uses_https: frontend.VITE_API_URL?.startsWith('https:') ?? false,
  },
  backend: {
    keys: Object.keys(backend).sort(),
    database: databaseFlags(backend.DATABASE_URL, 'football_heritage'),
    rag_database: databaseFlags(backend.RAG_DATABASE_URL, 'football_betting'),
    run_migrations_explicitly_disabled: backend.RUN_MIGRATIONS === 'false',
    demo_wallet_funding_enabled: backend.ALLOW_DEMO_WALLET_FUNDING === 'true',
    jwt_secret_valid_length: (backend.JWT_SECRET?.length ?? 0) >= 32,
    encryption_key_valid_bytes: Buffer.byteLength(backend.ENCRYPTION_KEY ?? '') === 32,
    pipeline_token_configured: Boolean(backend.PIPELINE_INTERNAL_TOKEN),
  },
  pipeline: {
    keys: Object.keys(pipeline).sort(),
    database: databaseFlags(pipeline.DATABASE_URL, 'football_betting'),
    heritage_database: databaseFlags(pipeline.HERITAGE_DATABASE_URL, 'football_heritage'),
    backend_internal_token_matches: Boolean(backend.PIPELINE_INTERNAL_TOKEN)
      && backend.PIPELINE_INTERNAL_TOKEN === pipeline.PIPELINE_INTERNAL_TOKEN,
  },
}, null, 2));
