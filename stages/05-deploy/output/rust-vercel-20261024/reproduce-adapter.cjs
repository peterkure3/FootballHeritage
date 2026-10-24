// fallow-ignore-file unused-file -- Manual diagnostic entrypoint; command is documented below.
// Read-only regression probe for @vercel/rust's config dereference.
// Run from the repository root: node stages/05-deploy/output/rust-vercel-20261024/reproduce-adapter.cjs
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const configPath = path.resolve('backend/.cargo/config.toml');
const parsed = spawnSync('py', ['-3', '-c',
  'import json,sys,tomllib; print(json.dumps(tomllib.load(open(sys.argv[1], "rb"))))',
  configPath], { encoding: 'utf8' });
if (parsed.status !== 0) throw new Error(parsed.stderr);
const config = JSON.parse(parsed.stdout);
const before = structuredClone(config);
delete before.build;
// Exact expression in upstream packages/rust/src/standalone-server.ts.
const adapterRead = cargoBuildConfiguration => cargoBuildConfiguration?.build.target;
assert.throws(() => adapterRead(before), /Cannot read properties of undefined \(reading 'target'\)/);
try { adapterRead(before); } catch (error) { console.log('Before: ' + error.stack); }
assert.equal(adapterRead(config), undefined);
console.log('After: target is undefined; adapter retains the default host artifact path.');
assert.deepEqual(config.build, {});
console.log('PASS: empty [build] fixes the dereference without forcing a Rust target.');
