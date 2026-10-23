"""Generate credentials for a new isolated local staging stack; never overwrite."""
from pathlib import Path
import os
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[2]
destination = ROOT / ".staging" / "secrets.env"
destination.parent.mkdir(exist_ok=True)
keys = (
    "DB_PASSWORD", "API_PASSWORD", "PIPELINE_PASSWORD", "READONLY_PASSWORD",
    "JWT_SECRET", "PIPELINE_TOKEN", "CHATBOT_TOKEN", "ADMIN_PASSWORD",
)
if destination.exists():
    print("Existing local staging configuration retained; no credentials changed.")
else:
    values = {"STAGING_" + key: secrets.token_hex(32) for key in keys}
    values["STAGING_ENCRYPTION_KEY"] = secrets.token_hex(16)
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as target:
        target.writelines(f"{key}={value}\n" for key, value in values.items())
    if os.name == "nt":
        # Restrict the new file to its current owner without printing any values.
        owner = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True)
        import csv
        sid = next(csv.reader([owner.strip()]))[1]
        subprocess.run(["icacls", str(destination), "/inheritance:r", "/grant:r", f"*{sid}:F"], check=True, capture_output=True)
    print("Created private .staging/secrets.env for local staging only.")
