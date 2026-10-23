"""Private loopback Python fallback; no ingestion or training is started."""
from pathlib import Path
import os
import socket
import subprocess

root = Path(__file__).resolve().parents[2]
state = root / ".staging"
values = dict(line.split("=", 1) for line in (state / "secrets.env").read_text().splitlines())
with socket.socket() as probe:
    if probe.connect_ex(("127.0.0.1", 15555)) == 0:
        raise SystemExit("Port 15555 occupied; no existing Python service will be reused.")
env = {**os.environ, "APP_ENV": "production", "MODEL_VERSION": "staging-fixture",
       "PIPELINE_INTERNAL_TOKEN": values["STAGING_PIPELINE_TOKEN"],
       "DATABASE_URL": "postgresql://fh_pipeline:" + values["STAGING_PIPELINE_PASSWORD"] + "@127.0.0.1:15439/fh_staging_predictions",
       "HERITAGE_DATABASE_URL": "postgresql://fh_api:" + values["STAGING_API_PASSWORD"] + "@127.0.0.1:15439/fh_staging_app"}
with (state / "native-pipeline.log").open("w") as log:
    process = subprocess.Popen([str(state / "python/Scripts/python.exe"), "-m", "uvicorn", "api.main:app",
                                "--host", "127.0.0.1", "--port", "15555"],
                               cwd=root / "pipeline", env=env, stdout=log, stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
(state / "native-pipeline.pid").write_text(str(process.pid))
print("Started token-protected Python gateway on loopback only; no workers or training started.")
