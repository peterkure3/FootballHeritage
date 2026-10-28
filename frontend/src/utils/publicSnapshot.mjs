// Only settled, public prediction evidence uses this cache; never prices or accounts.
const MAX_AGE_MS = 120000;
export function publicSnapshot(queryKey, load, storage) {
  const key = `fh-public-evidence-v1:${JSON.stringify(queryKey)}`;
  let saved;
  try {
    storage ??= globalThis.sessionStorage;
    const value = JSON.parse(storage?.getItem(key) ?? 'null');
    const age = Date.now() - value?.updatedAt;
    if (age >= 0 && age < MAX_AGE_MS && value?.data != null) saved = value;
  } catch { /* Storage can be unavailable or contain an older invalid entry. */ }
  return {
    initialData: saved?.data,
    initialDataUpdatedAt: saved?.updatedAt,
    staleTime: 0,
    refetchOnMount: 'always',
    queryFn: async (context) => {
      const data = await load(context);
      try {
        storage?.setItem(key, JSON.stringify({ data, updatedAt: Date.now() }));
      } catch { /* A full or disabled cache must not prevent fresh data loading. */ }
      return data;
    },
  };
}
