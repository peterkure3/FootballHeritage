import assert from 'node:assert/strict';
import { test } from 'node:test';
import { publicSnapshot } from '../src/utils/publicSnapshot.mjs';

test('public evidence restores only recent data for the exact query', async () => {
  const entries = new Map();
  const storage = { getItem: key => entries.get(key), setItem: (key, value) => entries.set(key, value) };
  const key = ['history', { page: 1 }];
  const load = async () => ({ predictions: [] });
  assert.equal(publicSnapshot(key, load, storage).initialData, undefined);
  await publicSnapshot(key, load, storage).queryFn({});
  assert.deepEqual(publicSnapshot(key, load, storage).initialData, { predictions: [] });
  assert.equal(publicSnapshot(['history', { page: 2 }], load, storage).initialData, undefined);
  const cacheKey = [...entries.keys()][0];
  for (const updatedAt of [Date.now() - 120001, Date.now() + 10000]) {
    entries.set(cacheKey, JSON.stringify({ data: {}, updatedAt }));
    assert.equal(publicSnapshot(key, load, storage).initialData, undefined);
  }
  entries.set(cacheKey, 'invalid JSON');
  assert.equal(publicSnapshot(key, load, storage).initialData, undefined);
});

test('disabled storage never blocks a fresh response', async () => {
  const storage = { getItem() { throw Error('disabled'); }, setItem() { throw Error('disabled'); } };
  const options = publicSnapshot(['history'], async () => ({ predictions: [] }), storage);
  assert.equal(options.initialData, undefined);
  assert.deepEqual(await options.queryFn({}), { predictions: [] });
});
