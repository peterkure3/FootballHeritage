"""Verify native restart persistence/session loss; not graceful OCI shutdown."""
from pathlib import Path
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[2]
values = dict(line.split("=", 1) for line in (root / ".staging/secrets.env").read_text().splitlines())

def request(path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("http://127.0.0.1:18888" + path, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    return response.code, json.loads(response.read())

login = {"email": "user@staging.example.test", "password": values["STAGING_ADMIN_PASSWORD"]}
status, session = request("/api/v1/auth/login", body=login)
assert status == 200
result = subprocess.run(["powershell.exe", "-NoProfile", "-File", str(root / "deploy/staging/stop_native.ps1"), "-Service", "api"], capture_output=True, text=True)
assert result.returncode == 0, "Refused to stop process; inspect staging PID identity"
subprocess.run([sys.executable, str(root / "deploy/staging/native_api.py")], check=True)
for _ in range(30):
    try:
        if request("/ready")[0] == 200:
            break
    except OSError:
        pass
    time.sleep(0.2)
results = {
    "native_forced_restart_readiness": request("/ready")[0] == 200,
    "prior_process_session_rejected": request("/api/v1/user/profile", token=session["token"])[0] == 401,
    "fresh_login_after_restart": request("/api/v1/auth/login", body=login)[0] == 200,
    "graceful_container_shutdown_verified": False,
}
(root / ".staging/restart-results.json").write_text(json.dumps(results, indent=2))
print(json.dumps(results))
raise SystemExit(0 if all(value for key, value in results.items() if key != "graceful_container_shutdown_verified") else 1)
