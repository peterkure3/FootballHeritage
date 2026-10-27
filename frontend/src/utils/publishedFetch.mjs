// Only the explicit publication protocol is polled; ordinary 202 responses pass through.
export async function publishedFetch(fetcher, url, options = {}, maxWaitMs = 60000) {
  const headers = new Headers(options.headers);
  const path = new URL(url, 'https://application.invalid').pathname;
  if ((path.includes('/pipeline/') || path.endsWith('/intelligence/refresh')) && !headers.has('Idempotency-Key')) {
    headers.set('Idempotency-Key', crypto.randomUUID());
  }
  const config = { ...options, headers };
  const deadline = Date.now() + maxWaitMs;
  let response = await fetcher(url, config);
  while (response.status === 202 && response.headers.get('X-Gateway-Pending') === '1') {
    if (Date.now() >= deadline) {
      return Response.json({ error: { code: 'PUBLICATION_PENDING', message: 'This output is still being prepared. Try again shortly.' } }, { status: 503 });
    }
    const delay = Math.min(Math.max(Number(response.headers.get('Retry-After')) || 2, 1), 5) * 1000;
    await new Promise((resolve, reject) => {
      const signal = config.signal;
      const abort = () => { clearTimeout(timer); reject(signal.reason ?? new DOMException('Aborted', 'AbortError')); };
      const timer = setTimeout(() => { signal?.removeEventListener('abort', abort); resolve(); }, Math.min(delay, Math.max(0, deadline - Date.now())));
      if (signal?.aborted) abort();
      else signal?.addEventListener('abort', abort, { once: true });
    });
    response = await fetcher(url, config);
  }
  return response;
}
