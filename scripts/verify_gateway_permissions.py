"""Least-privilege contract, confined to the disposable loopback HTTP database."""

import uuid

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import parse_dsn


def verify(destination, stream, executor, check):
    from sync.gateway import prewarm, run_one

    settings = parse_dsn(destination)
    if settings.get("host") not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ) or not settings.get("dbname", "").startswith("fh_auth_http_test_"):
        raise ValueError(
            "Restricted role tests require the harness's disposable database"
        )
    role_name = "fh_gateway_test_" + uuid.uuid4().hex
    policy_name = "gateway_test_" + uuid.uuid4().hex
    owner = psycopg2.connect(destination)
    worker = None
    created = False
    try:
        with owner, owner.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
                ).format(sql.Identifier(role_name))
            )
            created = True
            for statement in (
                "GRANT USAGE ON SCHEMA published,public TO {}",
                "GRANT SELECT ON published.sources,published.gateway_jobs TO {}",
                "GRANT INSERT ON published.gateway_jobs TO {}",
                "GRANT UPDATE(state,attempts,lease_token,lease_until,response,response_status,generated_at,fresh_until,created_at) ON published.gateway_jobs TO {}",
                "GRANT SELECT(id,role,is_active,locked_until) ON users TO {}",
            ):
                cursor.execute(sql.SQL(statement).format(sql.Identifier(role_name)))
            cursor.execute(
                "ALTER TABLE published.gateway_jobs ENABLE ROW LEVEL SECURITY"
            )
            cursor.execute(
                sql.SQL(
                    "CREATE POLICY {} ON published.gateway_jobs TO {} USING(stream_id={}) WITH CHECK(stream_id={})"
                ).format(
                    sql.Identifier(policy_name),
                    sql.Identifier(role_name),
                    sql.Literal(stream),
                    sql.Literal(stream),
                )
            )
        worker = psycopg2.connect(destination)
        with worker, worker.cursor() as cursor:
            cursor.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role_name)))
        # Exercise the real queue SQL under a role that cannot own or mutate a source.
        prewarm(worker, stream)
        outcome = run_one(worker, stream, executor, raise_errors=True)
        check(
            outcome["gateway"] == "published",
            "Restricted worker must publish a legitimate queued result",
        )
        denied = 0
        for statement in (
            "SELECT email FROM users LIMIT 1",
            "SELECT * FROM auth_sessions LIMIT 1",
            "UPDATE wallets SET updated_at=NOW() WHERE FALSE",
            "DELETE FROM published.records WHERE FALSE",
            "TRUNCATE published.gateway_jobs",
            "UPDATE published.sources SET enabled=FALSE WHERE FALSE",
        ):
            try:
                with worker, worker.cursor() as cursor:
                    cursor.execute(statement)
            except psycopg2.Error as error:
                check(
                    error.pgcode == "42501",
                    "Forbidden operation must fail on privilege checks",
                )
                denied += 1
            else:
                raise AssertionError(
                    "Restricted gateway worker unexpectedly has forbidden privileges"
                )
        with worker, worker.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM published.gateway_jobs WHERE stream_id<>%s",
                (stream,),
            )
            check(cursor.fetchone()[0] == 0, "Worker cannot read another stream's jobs")
        return {
            "restricted_worker_denials": denied,
            "restricted_worker_published": True,
        }
    finally:
        if worker is not None:
            worker.close()
        if created:
            with owner, owner.cursor() as cursor:
                cursor.execute(
                    sql.SQL(
                        "DROP POLICY IF EXISTS {} ON published.gateway_jobs"
                    ).format(sql.Identifier(policy_name))
                )
                cursor.execute(
                    "ALTER TABLE published.gateway_jobs DISABLE ROW LEVEL SECURITY"
                )
                cursor.execute(
                    sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role_name))
                )
                cursor.execute(
                    sql.SQL("DROP ROLE {}").format(sql.Identifier(role_name))
                )
        owner.close()
