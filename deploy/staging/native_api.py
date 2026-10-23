"""Run a native local staging API when Docker is unavailable; never a release image."""
from pathlib import Path
import os
import socket
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
state = root / ".staging"
values = dict(line.split("=", 1) for line in (state / "secrets.env").read_text().splitlines())
binary = state / "rust-target/debug/football-heritage-backend.exe"
for port in (18888,):
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"Port {port} occupied; no existing API will be reused.")
env = {**os.environ, "APP_ENV": "production", "DEPLOYMENT_ENV": "local-staging",
       "HOST": "127.0.0.1", "PORT": "18888", "HTTPS_ENABLED": "false",
       "RUN_MIGRATIONS": "false", "DB_MAX_CONNECTIONS": "10",
       "JWT_SECRET": values["STAGING_JWT_SECRET"], "ENCRYPTION_KEY": values["STAGING_ENCRYPTION_KEY"],
       "DATABASE_URL": "postgresql://fh_api:" + values["STAGING_API_PASSWORD"] + "@127.0.0.1:15439/fh_staging_app",
       "MIGRATION_DATABASE_URL": "postgresql://staging_owner:" + values["STAGING_DB_PASSWORD"] + "@127.0.0.1:15439/fh_staging_app",
       "RAG_DATABASE_URL": "postgresql://fh_readonly:" + values["STAGING_READONLY_PASSWORD"] + "@127.0.0.1:15439/fh_staging_predictions",
       "RAG_MODEL_VERSION": "staging-fixture", "RAG_CHAT_MODE": "grounded",
       "PIPELINE_API_URL": "http://127.0.0.1:15555/api/v1",
       "PIPELINE_INTERNAL_TOKEN": values["STAGING_PIPELINE_TOKEN"],
       "ALLOWED_ORIGINS": "https://staging.footballheritage.test:18443",
       "ALLOW_DEMO_WALLET_FUNDING": "false", "LOGIN_RATE_LIMIT_PER_MINUTE": "100",
       "REGISTER_RATE_LIMIT_PER_HOUR": "100", "RUST_LOG": "info"}
with (state / "native-migrate.log").open("w") as log:
    result = subprocess.run([str(binary.with_name("migrate.exe"))], env=env, cwd=root / "backend", stdout=log, stderr=log, timeout=120)
if result.returncode:
    raise SystemExit("Isolated staging migration failed; inspect private migration log.")
# The privileged migration URL must not be inherited by the serving process.
env.pop("MIGRATION_DATABASE_URL")
if len(sys.argv) > 1 and sys.argv[1] == "migrate-only":
    print("Isolated application migrations completed.")
else:
    with (state / "native-api.log").open("w") as log:
        process = subprocess.Popen([str(binary)], cwd=root / "backend", env=env, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    (state / "native-api.pid").write_text(str(process.pid))
    print("Started isolated native API; PID recorded privately. This is not container verification.")
