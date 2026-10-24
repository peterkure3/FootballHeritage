// fallow-ignore-file unused-file -- Manual, read-only hosted configuration diagnostic.
// CLI output is parsed in memory; environment values are never printed or saved.
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';

const teamId = 'team_PbpiKdM3J9zfUN4UpZnixHZy';
const cli = join(process.env.APPDATA, 'npm/node_modules/vercel/dist/vc.js');
function get(endpoint) {
  const output = execFileSync(process.execPath, [cli, 'api', endpoint,
    '--method', 'GET', '--scope', teamId, '--non-interactive'], {
    encoding: 'utf8', timeout: 45000, maxBuffer: 8 * 1024 * 1024,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const data = JSON.parse(output);
  return data.result ?? data;
}
function publicUrlFlags(entry) {
  if (entry.key !== 'VITE_API_URL' || !['plain', 'system'].includes(entry.type)) return undefined;
  try {
    const url = new URL(entry.value);
    return { parsed: true, https: url.protocol === 'https:', local: ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname), allowed_path: ['/', '/api/v1', '/api/v1/'].includes(url.pathname) };
  } catch { return { parsed: false }; }
}
const results = [];
for (const [service, id] of [['frontend', 'prj_T0Aus4LHcFJJRMNKtmdVXLRbd5ad'], ['backend', 'prj_0r4mFmPbEpDGrvHKLPK76tXuKxdh']]) {
  try {
    const project = get(`/v9/projects/${id}?teamId=${teamId}`);
    const env = get(`/v10/projects/${id}/env?teamId=${teamId}&decrypt=false`);
    const deployments = get(`/v7/deployments?projectId=${id}&teamId=${teamId}&limit=5`);
    const latestId = deployments.deployments?.[0]?.uid ?? deployments.deployments?.[0]?.id;
    const latest = latestId ? get(`/v13/deployments/${latestId}?teamId=${teamId}`) : {};
    results.push({ service,
      project: { id: project.id, name: project.name, rootDirectory: project.rootDirectory,
        framework: project.framework, buildCommand: project.buildCommand,
        installCommand: project.installCommand, outputDirectory: project.outputDirectory,
        nodeVersion: project.nodeVersion, productionBranch: project.link?.productionBranch },
      latestBuildSettings: { rootDirectory: latest.projectSettings?.rootDirectory,
        framework: latest.projectSettings?.framework,
        sourceFilesOutsideRootDirectory: latest.projectSettings?.sourceFilesOutsideRootDirectory,
        builders: latest.builds?.map(build => ({ src: build.src, use: build.use })) },
      environment: (env.envs ?? []).map(entry => ({ key: entry.key, type: entry.type,
        target: entry.target, gitBranch: entry.gitBranch, customEnvironmentIds: entry.customEnvironmentIds,
        publicApiUrlFlags: publicUrlFlags(entry) })),
      deployments: (deployments.deployments ?? []).map(entry => ({ id: entry.uid ?? entry.id,
        url: entry.url, state: entry.state ?? entry.readyState, target: entry.target,
        gitSha: entry.meta?.githubCommitSha, gitBranch: entry.meta?.githubCommitRef })),
    });
  } catch (error) {
    results.push({ service, error: 'Read-only CLI request failed', code: error.status ?? error.code });
  }
}
console.log(JSON.stringify(results, null, 2));
