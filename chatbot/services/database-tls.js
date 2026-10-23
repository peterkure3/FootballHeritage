// Local staging uses an isolated Docker network. Remote databases verify TLS.
export function databaseTls(env = process.env) {
  if (env.PGSSLMODE === 'disable') {
    if (env.NODE_ENV === 'production' && env.DEPLOYMENT_ENV !== 'local-staging') {
      throw new Error('Disabling database TLS is restricted to isolated local staging.');
    }
    return false;
  }
  return env.NODE_ENV === 'production'
    ? { rejectUnauthorized: true, ...(env.PGSSLROOTCERT_PEM ? { ca: env.PGSSLROOTCERT_PEM } : {}) }
    : false;
}
