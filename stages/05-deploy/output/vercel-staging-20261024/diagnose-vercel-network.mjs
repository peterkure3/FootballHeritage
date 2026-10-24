// fallow-ignore-file unused-file -- Read-only manual network diagnostic.
import dns from 'node:dns/promises';
import https from 'node:https';

function errorDetails(error) {
  return {
    name: error?.name, code: error?.code, message: error?.message,
    cause: error?.cause ? errorDetails(error.cause) : undefined,
    errors: error?.errors?.map(errorDetails),
  };
}
console.log(JSON.stringify({
  node: process.version,
  networkEnvironmentNames: Object.keys(process.env).filter(key => /PROXY|CA_CERT|TLS|CERT_FILE|NODE_OPTIONS/i.test(key)),
}));
for (const host of ['api.vercel.com', 'vercel.com']) {
  try { console.log(JSON.stringify({ host, dns: await dns.lookup(host, { all: true }) })); }
  catch (error) { console.log(JSON.stringify({ host, dnsError: errorDetails(error) })); }
}
await Promise.all(['https://vercel.com/.well-known/openid-configuration', 'https://api.vercel.com/v2/user', 'https://vercel.com'].map(async url => {
  const start = Date.now();
  try {
    const response = await fetch(url, { redirect: 'manual', signal: AbortSignal.timeout(12000) });
    console.log(JSON.stringify({ method: 'fetch', url, status: response.status, milliseconds: Date.now() - start }));
    await response.body?.cancel();
  } catch (error) { console.log(JSON.stringify({ method: 'fetch', url, milliseconds: Date.now() - start, error: errorDetails(error) })); }
}));
await Promise.all(['vercel.com', 'api.vercel.com'].map(host => new Promise(resolve => {
  const start = Date.now();
  const request = https.get({ hostname: host, path: host === 'vercel.com' ? '/.well-known/openid-configuration' : '/v2/user', family: 4 }, response => {
    console.log(JSON.stringify({ method: 'https-ipv4', host, status: response.statusCode, milliseconds: Date.now() - start }));
    response.destroy(); resolve();
  });
  request.setTimeout(12000, () => request.destroy(new Error('HTTPS request timeout')));
  const deadline = setTimeout(() => request.destroy(new Error('HTTPS total timeout')), 15000);
  request.on('error', error => {
    console.log(JSON.stringify({ method: 'https-ipv4', host, milliseconds: Date.now() - start, error: errorDetails(error) }));
    resolve();
  });
  request.on('close', () => clearTimeout(deadline));
})));
