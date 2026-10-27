"""Real independent-process auth checks, only in a disposable loopback database."""

import json
import os
import secrets
import socket
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

import psycopg2
from dotenv import dotenv_values
from psycopg2 import sql
from psycopg2.extensions import parse_dsn
from verify_durable_gateway_http import verify as verify_durable_gateway
from verify_published_picks_http import verify as verify_published_picks
from verify_published_rag_http import verify as verify_published_rag

ROOT = Path(__file__).resolve().parents[1]


def request(
    base: str,
    path: str,
    *,
    method: str = "GET",
    data=None,
    token=None,
    extra_headers=None,
):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if extra_headers:
        headers.update(extra_headers)
    body = None if data is None else json.dumps(data).encode("utf-8")
    try:
        response = urlopen(
            Request(base + path, data=body, headers=headers, method=method), timeout=15
        )
    except HTTPError as error:
        response = error
    with response:
        payload = response.read()
        return response.status, json.loads(payload) if payload else None


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def start(binary: Path, environment: dict, log, processes: list):
    port = free_port()
    process = subprocess.Popen(
        [
            str(binary),
            "--ignored",
            "--exact",
            "session_tests::serve_http_fixture",
            "--nocapture",
        ],
        cwd=ROOT / "backend",
        env={**environment, "PORT": str(port)},
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    processes.append(process)
    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError("Test API failed to start; inspect the private test log")
        try:
            if request(base, "/ready")[0] == 200:
                return base, process
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.25)
    raise RuntimeError("Test API readiness timed out")


def stop(process) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    source = os.getenv("SESSION_TEST_DATABASE_URL") or dotenv_values(
        ROOT / "pipeline/.env"
    ).get("DATABASE_URL")
    if not source or parse_dsn(source).get("host") not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        raise SystemExit("Use a loopback PostgreSQL URL for HTTP auth verification")
    parsed = urlsplit(source)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise SystemExit("A PostgreSQL URL is required")
    database = "fh_auth_http_test_" + uuid.uuid4().hex
    destination = urlunsplit(parsed._replace(path="/" + database))
    admin = psycopg2.connect(source)
    admin.autocommit = True
    processes = []
    created = False
    logs = ROOT / ".release/auth-http"
    logs.mkdir(parents=True, exist_ok=True)
    environment = {
        **os.environ,
        "MIGRATION_DATABASE_URL": destination,
        "DATABASE_URL": destination,
        "APP_ENV": "production",
        "AUTH_HTTP_FIXTURE_MODE": "enabled",
        "RUN_MIGRATIONS": "false",
        "HOST": "127.0.0.1",
        "HTTPS_ENABLED": "false",
        "HTTP_WORKERS": "1",
        "DB_MAX_CONNECTIONS": "3",
        "JWT_SECRET": secrets.token_hex(32),
        "ENCRYPTION_KEY": secrets.token_hex(16),
        "JWT_EXPIRATION_HOURS": "24",
        "SESSION_TIMEOUT_MINUTES": "30",
        "MAX_LOGIN_ATTEMPTS": "5",
        "ACCOUNT_LOCK_MINUTES": "15",
        "PIPELINE_INTERNAL_TOKEN": secrets.token_hex(32),
        "PIPELINE_API_URL": "http://127.0.0.1:1/api/v1",
        "PUBLICATION_STREAM_ID": str(uuid.uuid4()),
        # Must be ignored entirely in production, including URL parsing.
        "RAG_DATABASE_URL": "invalid-legacy-rag-url-must-not-be-used",
        "RAG_CHAT_MODE": "grounded",
        "RAG_GEMINI_API_KEY": "",
        "GEMINI_API_KEY": "",
        "ALLOWED_ORIGINS": "https://web.example.test",
        "LOGIN_RATE_LIMIT_PER_MINUTE": "100",
        "REGISTER_RATE_LIMIT_PER_HOUR": "100",
        "ALLOW_DEMO_WALLET_FUNDING": "false",
    }
    try:
        with admin.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database))
            )
        created = True
        subprocess.run(
            [
                "cargo",
                "build",
                "--locked",
                "--bin",
                "migrate",
            ],
            cwd=ROOT / "backend",
            check=True,
        )
        metadata = subprocess.run(
            ["cargo", "metadata", "--no-deps", "--format-version", "1"],
            cwd=ROOT / "backend",
            capture_output=True,
            text=True,
            check=True,
        )
        target = Path(json.loads(metadata.stdout)["target_directory"]) / "debug"
        suffix = ".exe" if os.name == "nt" else ""
        compilation = subprocess.run(
            [
                "cargo",
                "test",
                "--locked",
                "--bin",
                "football-heritage-backend",
                "--no-run",
                "--message-format=json",
            ],
            cwd=ROOT / "backend",
            capture_output=True,
            text=True,
            check=True,
        )
        artifacts = [
            json.loads(line)
            for line in compilation.stdout.splitlines()
            if line.startswith("{")
        ]
        executables = [
            item["executable"]
            for item in artifacts
            if item.get("reason") == "compiler-artifact"
            and item.get("profile", {}).get("test")
            and item.get("executable")
            and item.get("target", {}).get("name") == "football-heritage-backend"
        ]
        check(len(executables) == 1, "Expected one isolated API test executable")
        binary = Path(executables[0])
        subprocess.run(
            [str(target / ("migrate" + suffix))],
            cwd=ROOT / "backend",
            env=environment,
            check=True,
        )
        subprocess.run(
            [str(target / ("migrate" + suffix))],
            cwd=ROOT / "backend",
            env=environment,
            check=True,
        )
        with (logs / "api.log").open("w", encoding="utf-8") as log:
            first, first_process = start(binary, environment, log, processes)
            second, _ = start(binary, environment, log, processes)
            credentials = {
                "email": "auth-http-test@example.test",
                "password": "Test-only!" + secrets.token_hex(12),
            }
            status, registered = request(
                first,
                "/api/v1/auth/register",
                method="POST",
                data={
                    **credentials,
                    "first_name": "Test",
                    "last_name": "Account",
                    "date_of_birth": "1990-01-01",
                },
            )
            check(status == 201, "Registration must create a test account")
            token = registered["token"]
            status, logged_in = request(
                first, "/api/v1/auth/login", method="POST", data=credentials
            )
            check(status == 200, "Login must return a token")
            other = logged_in["token"]
            verify_published_picks(
                second,
                other,
                destination,
                environment["PUBLICATION_STREAM_ID"],
                request,
                check,
            )
            verify_published_rag(
                second,
                other,
                destination,
                environment["PUBLICATION_STREAM_ID"],
                request,
                check,
            )
            gateway_base, _ = start(binary, environment, log, processes)
            readers = [start(binary, environment, log, processes) for _ in range(4)]
            verify_durable_gateway(
                gateway_base,
                other,
                destination,
                environment["PUBLICATION_STREAM_ID"],
                request,
                check,
                source,
                [reader_base for reader_base, _ in readers],
            )
            for _, reader_process in readers:
                stop(reader_process)
            check(
                request(second, "/api/v1/user/profile", token=token)[0] == 200,
                "Another API process must accept the registered session",
            )
            check(
                request(second, "/api/v1/user/profile", token=other)[0] == 200,
                "Another API process must accept the login session",
            )
            stop(first_process)
            restarted, _ = start(binary, environment, log, processes)
            check(
                request(restarted, "/api/v1/user/profile", token=token)[0] == 200,
                "Cold process must accept the existing session",
            )
            check(
                request(second, "/api/v1/auth/logout", method="POST", token=token)[0]
                == 200,
                "Logout must succeed",
            )
            check(
                request(restarted, "/api/v1/user/profile", token=token)[0] == 401,
                "Revocation must apply to all processes",
            )
            check(
                request(restarted, "/api/v1/user/profile", token=other)[0] == 200,
                "Unrelated session must remain active",
            )
            check(
                request(restarted, "/api/v1/auth/logout", method="POST", token=token)[0]
                == 200,
                "Logout must remain idempotent",
            )
            account_setup = ("users", "wallets", "gambling_limits", "auth_sessions")
            fault = psycopg2.connect(destination)
            try:
                with fault, fault.cursor() as cursor:
                    baseline = []
                    for table in account_setup:
                        cursor.execute(
                            sql.SQL("SELECT count(*) FROM {}").format(
                                sql.Identifier(table)
                            )
                        )
                        baseline.append(cursor.fetchone()[0])
                    cursor.execute("""CREATE FUNCTION test_reject_session() RETURNS trigger LANGUAGE plpgsql AS $$
                        BEGIN RAISE EXCEPTION 'test-only session write rejection'; END; $$;
                        CREATE TRIGGER test_reject_session BEFORE INSERT ON auth_sessions
                        FOR EACH ROW EXECUTE FUNCTION test_reject_session()""")
                new_account = {
                    **credentials,
                    "email": "auth-rollback-test@example.test",
                    "first_name": "Test",
                    "last_name": "Rollback",
                    "date_of_birth": "1990-01-01",
                }
                failed_status, _ = request(
                    restarted, "/api/v1/auth/register", method="POST", data=new_account
                )
                check(
                    failed_status == 500,
                    "Injected session failure must reject registration",
                )
                with fault, fault.cursor() as cursor:
                    after_failure = []
                    for table in account_setup:
                        cursor.execute(
                            sql.SQL("SELECT count(*) FROM {}").format(
                                sql.Identifier(table)
                            )
                        )
                        after_failure.append(cursor.fetchone()[0])
                    check(
                        after_failure == baseline,
                        "Failed registration must roll back account, wallet, limits and session",
                    )
                    cursor.execute(
                        "DROP TRIGGER test_reject_session ON auth_sessions; DROP FUNCTION test_reject_session()"
                    )
                retry_status, _ = request(
                    restarted, "/api/v1/auth/register", method="POST", data=new_account
                )
                check(
                    retry_status == 201,
                    "The same account registration must succeed after recovery",
                )
                with fault, fault.cursor() as cursor:
                    after_retry = []
                    for table in account_setup:
                        cursor.execute(
                            sql.SQL("SELECT count(*) FROM {}").format(
                                sql.Identifier(table)
                            )
                        )
                        after_retry.append(cursor.fetchone()[0])
                    check(
                        after_retry == [count + 1 for count in baseline],
                        "Recovered registration must create exactly one of each account record",
                    )
            finally:
                fault.close()
            wrong = {
                "email": new_account["email"],
                "password": "known-wrong-test-password",
            }
            endpoints = [second, restarted, second, restarted, second]
            with ThreadPoolExecutor(max_workers=5) as executor:
                failures = list(
                    executor.map(
                        lambda endpoint: request(
                            endpoint, "/api/v1/auth/login", method="POST", data=wrong
                        )[0],
                        endpoints,
                    )
                )
            check(
                all(code == 401 for code in failures),
                "Five failed-password requests must be rejected",
            )
            verification = psycopg2.connect(destination)
            try:
                with verification, verification.cursor() as cursor:
                    cursor.execute(
                        "SELECT failed_login_attempts,locked_until>NOW() FROM users WHERE email=%s",
                        (new_account["email"],),
                    )
                    check(
                        cursor.fetchone() == (5, True),
                        "Concurrent failed logins must atomically enforce the lock threshold",
                    )
            finally:
                verification.close()
            check(
                request(
                    restarted,
                    "/api/v1/auth/login",
                    method="POST",
                    data={
                        "email": new_account["email"],
                        "password": credentials["password"],
                    },
                )[0]
                == 423,
                "Locked account must reject even a correct password",
            )
            print(
                json.dumps(
                    {
                        "register": 201,
                        "login": 200,
                        "independent_process_profile": 200,
                        "cold_restart_profile": 200,
                        "revoked_profile": 401,
                        "other_session_profile": 200,
                        "idempotent_logout": 200,
                        "python_http_dependency": False,
                        "registration_rollback_verified": True,
                        "registration_retry": 201,
                        "concurrent_lock_threshold_verified": True,
                        "published_ai_picks_http_python_parity": True,
                        "published_ai_picks_pagination_freshness_and_withdrawal": True,
                        "published_rag_provenance_pagination_history_and_withdrawal": True,
                    }
                )
            )
        return 0
    finally:
        for process in processes:
            stop(process)
        if created:
            # Only the exact database created by this invocation is removed.
            with admin.cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                        sql.Identifier(database)
                    )
                )
        admin.close()


if __name__ == "__main__":
    raise SystemExit(main())
