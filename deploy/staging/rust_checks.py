"""Run Rust checks against only the generated local staging test database."""
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
values = dict(line.split("=", 1) for line in (root / ".staging/secrets.env").read_text().splitlines())
env = {**os.environ, "SQLX_OFFLINE": "true", "CARGO_INCREMENTAL": "0",
       "CARGO_TARGET_DIR": str(root / ".staging/rust-target"),
       "CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_PROFILE_TEST_DEBUG": "0",
       "FEATURE_TEST_DATABASE_URL": "postgresql://staging_owner:" + values["STAGING_DB_PASSWORD"] + "@127.0.0.1:15439/fh_staging_tests"}
command = ["cargo", "test", "--locked", "--bin", "football-heritage-backend", "-j", "2"]
if len(sys.argv) > 1 and sys.argv[1] == "build":
    command = ["cargo", "build", "--locked", "--bin", "football-heritage-backend", "--bin", "migrate", "-j", "2"]
with (root / ".staging" / ("rust-build.log" if "build" in command else "rust-tests.log")).open("w") as log:
    result = subprocess.run(command, cwd=root / "backend", env=env, stdout=log, stderr=subprocess.STDOUT)
print("Rust", command[1], "exit:", result.returncode, "; evidence in .staging/")
raise SystemExit(result.returncode)
