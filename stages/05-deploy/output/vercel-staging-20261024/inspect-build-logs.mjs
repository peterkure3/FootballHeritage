// fallow-ignore-file unused-file -- Read-only build diagnostics; never invokes deployed functions.
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const cli = join(process.env.APPDATA, 'npm/node_modules/vercel/dist/vc.js');
function redact(value) {
  return value.replace(/postgres(?:ql)?:\/\/[^\s"'<>]+/gi, '[REDACTED_DATABASE_URL]')
    .replace(/(Bearer\s+)[A-Za-z0-9._-]+/gi, '$1[REDACTED]')
    .replace(/((?:[A-Z_]*(?:SECRET|TOKEN|PASSWORD|API_KEY)|DATABASE_URL|ENCRYPTION_KEY)\s*[=:]\s*)[^\s,;]+/g, '$1[REDACTED]')
    .replace(/gh[pousr]_[A-Za-z0-9]+/g, '[REDACTED_GITHUB_CREDENTIAL]');
}
for (const [label, id] of [
  ['frontend-error', 'dpl_BtjTUS5CYdaaFs9JjzynMToDnb7L'],
  ['backend-error', 'dpl_5fhxaLCTjrweSYTNCRkuVtY5Pni6'],
  ['backend-ready', 'dpl_CFnEdRV2orRTDMAUYHDAuczyBR5R'],
]) {
  let output;
  try {
    output = execFileSync(process.execPath, [cli, 'inspect', id, '--logs', '--scope', 'peterkure3s-projects', '--non-interactive'], {
      encoding: 'utf8', timeout: 45000, maxBuffer: 8 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (error) { output = `${error.stdout ?? ''}\n${error.stderr ?? ''}`; }
  const safe = redact(output);
  writeFileSync(fileURLToPath(new URL(`hosted-${label}.log`, import.meta.url)), safe);
  console.log(JSON.stringify({ label, deployment: id, logLines: safe.split(/\r?\n/).length,
    relevantLines: safe.split(/\r?\n/).filter(line => /error|failed|VITE_API_URL|entrypoint|Cargo|rust|Root|build|Build/i.test(line)).slice(-45),
  }, null, 2));
}
