"""Windows-only isolated PostgreSQL fallback for DB tests, not container evidence."""
from pathlib import Path
import os
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".staging"
DATA = STATE / "postgres-native"
BIN = Path(r"C:\Program Files\PostgreSQL\16\bin")
values = dict(line.split("=", 1) for line in (STATE / "secrets.env").read_text().splitlines())
env = {**os.environ, **values, "PGPASSWORD": values["STAGING_DB_PASSWORD"]}

def run(name, *args, **kwargs):
    if name == "pg_ctl":
        # The detached postmaster can inherit capture pipes on Windows.
        return subprocess.run([str(BIN / "pg_ctl.exe"), *map(str, args)],
                              env=env, check=True, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=45, **kwargs)
    return subprocess.run([str(BIN / (name + ".exe")), *map(str, args)],
                          env=env, check=True, capture_output=True, text=True, **kwargs)

if len(sys.argv) > 1 and sys.argv[1] == "stop":
    run("pg_ctl", "-D", DATA, "-m", "fast", "stop", "-w")
    print("Stopped only the isolated native staging database.")
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "start":
    if not (DATA / "PG_VERSION").exists():
        raise SystemExit("No previously initialized staging cluster exists.")
    run("pg_ctl", "-D", DATA, "-l", STATE / "postgres-native.log", "-o", "-h 127.0.0.1 -p 15439", "start", "-w")
    print("Restarted only the isolated native staging cluster.")
    raise SystemExit(0)

if DATA.exists():
    raise SystemExit("Existing isolated database retained. Use pg_ctl status; initialization is never repeated.")
with socket.socket() as probe:
    if probe.connect_ex(("127.0.0.1", 15439)) == 0:
        raise SystemExit("Port 15439 is occupied; no existing database will be used.")
password = STATE / "init-password"
try:
    descriptor = os.open(password, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(values["STAGING_DB_PASSWORD"])
    run("initdb", "-D", DATA, "-U", "staging_owner", "--pwfile", password,
        "--auth-host=scram-sha-256", "--auth-local=scram-sha-256", "--encoding=UTF8", "--locale=C")
finally:
    password.unlink(missing_ok=True)
run("pg_ctl", "-D", DATA, "-l", STATE / "postgres-native.log", "-o", "-h 127.0.0.1 -p 15439", "start", "-w")
run("psql", "-h", "127.0.0.1", "-p", "15439", "-U", "staging_owner", "-d", "postgres",
    "-v", "ON_ERROR_STOP=1", "-f", ROOT / "deploy/staging/postgres-init.sql")
print("Initialized new PostgreSQL 16 cluster on 127.0.0.1:15439 with isolated staging databases.")
