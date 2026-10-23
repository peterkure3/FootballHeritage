"""Acceptance checks restricted to this workstation's isolated staging API."""
from pathlib import Path
import json
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
VALUES = dict(line.split("=", 1) for line in (ROOT / ".staging/secrets.env").read_text().splitlines())
ACCOUNTS = json.loads((ROOT / ".staging/accounts.json").read_text())
RESULTS = []

def request(path, method="GET", body=None, token=None, headers=None, port=18888):
    fields = {"Content-Type": "application/json", **(headers or {})}
    if token:
        fields["Authorization"] = "Bearer " + token
    req = urllib.request.Request(f"http://127.0.0.1:{port}" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None, headers=fields)
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    raw = response.read().decode()
    try:
        content = json.loads(raw)
    except ValueError:
        content = raw
    return response.code, content, response.headers

def check(name, condition):
    RESULTS.append({"check": name, "passed": bool(condition)})
    print(("PASS " if condition else "FAIL ") + name)

def login(name):
    status, body, _ = request("/api/v1/auth/login", "POST", {
        "email": ACCOUNTS[name]["email"], "password": VALUES["STAGING_ADMIN_PASSWORD"]})
    check(name + " login", status == 200 and isinstance(body.get("token"), str))
    return body["token"]

admin = login("admin")
user = login("user")
restricted = login("restricted")
recovery = login("recovery")
prefix = "/api/v1"
status, registry, _ = request(prefix + "/admin/features", token=admin)
check("admin authorization", status == 200)
saved = {row["key"]: row for row in registry["features"]}
role = next(row["enabled"] for row in registry["roles"] if row["key"] == "wallet" and row["role"] == "user")
target = prefix + "/admin/users/" + ACCOUNTS["restricted"]["id"] + "/features/wallet"
status, policy, _ = request(prefix + "/admin/users/" + ACCOUNTS["restricted"]["id"] + "/features", token=admin)
override = policy["overrides"].get("wallet")

def patch(key, body, token=admin):
    return request(prefix + "/admin/features/" + key, "PATCH", body, token)[0]

try:
    for path in ("/health", "/ready"):
        check(path, request(path)[0] == 200)
    check("unauthorized admin rejected", request(prefix + "/admin/features", token=user)[0] == 403)
    check("anonymous metrics rejected", request("/metrics")[0] in (401, 403))
    check("ordinary metrics rejected", request("/metrics", token=user)[0] == 403)
    check("admin metrics accessible", request("/metrics", token=admin)[0] == 200)
    check("global disable mutation", patch("wallet", {"enabled": False}) == 200)
    status, body, _ = request(prefix + "/wallet/balance", token=user)
    check("global direct API denied", status == 403 and body["error"]["code"] == "FEATURE_DISABLED")
    patch("wallet", {"enabled": True, "emergency_disabled": False})
    check("user override mutation", request(target, "PATCH", {"enabled": False}, admin)[0] == 200)
    check("selected user denied", request(prefix + "/wallet/balance", token=restricted)[0] == 403)
    check("other user retains access", request(prefix + "/wallet/balance", token=user)[0] == 200)
    check("role restriction mutation", patch("wallet/roles/user", {"enabled": False}) == 200)
    check("role restriction enforced", request(prefix + "/wallet/balance", token=user)[0] == 403)
    patch("wallet/roles/user", {"enabled": True})
    patch("wallet", {"emergency_disabled": True})
    check("emergency denies superadmin", request(prefix + "/wallet/balance", token=admin)[0] == 403)
    patch("wallet", {"emergency_disabled": False})
    patch("maintenance", {"enabled": True})
    check("maintenance denies products", request(prefix + "/wallet/balance", token=user)[0] == 403)
    check("maintenance keeps recovery controls accessible", request(prefix + "/admin/features", token=recovery)[0] == 200)
    check("recovery clears maintenance", patch("maintenance", {"enabled": False}, recovery) == 200)
    check("unknown feature rejected", patch("not-a-real-feature", {"enabled": True}) == 404)
    status, audit, _ = request(prefix + "/admin/features/audit", token=admin)
    check("audit history includes actor target timestamp", status == 200 and any(
        row.get("administrator_id") == ACCOUNTS["admin"]["id"] and row.get("target") and row.get("created_at") for row in audit))
    for path in ("/wallet/deposit", "/wallet/withdraw", "/betting/bets", "/parlay/place"):
        status, body, _ = request(prefix + path, "POST", {"amount": 1}, admin)
        check("production money block " + path, status == 403 and body["error"]["code"] == "FEATURE_DISABLED")
    for token in (None, "incorrect"):
        headers = {"Origin": "https://staging.footballheritage.test:18443"}
        if token:
            headers["X-Internal-Token"] = token
        check("private Python rejects " + (token or "missing token"), request(prefix + "/health", headers=headers, port=15555)[0] == 403)
    check("private Python accepts gateway token", request(prefix + "/health", headers={"X-Internal-Token": VALUES["STAGING_PIPELINE_TOKEN"]}, port=15555)[0] == 200)
    check("Rust private Python gateway", request(prefix + "/pipeline/matches", token=user)[0] == 200)
    check("sports endpoint", request(prefix + "/sports", token=user)[0] == 200)
    chat = {"messages": [{"role": "user", "content": "Show the evidence for Staging Home versus Staging Away"}], "sport": "Football"}
    status, reply, _ = request(prefix + "/ai-picks/chat", "POST", chat, user)
    check("active Rust RAG chat and persistence", status == 200 and reply.get("conversation_id") and reply.get("reply"))
    if status == 200:
        check("RAG conversation reload", request(prefix + "/ai-picks/conversations/" + reply["conversation_id"], token=user)[0] == 200)
    patch("ai_chat", {"emergency_disabled": True})
    check("Rust RAG emergency restriction", request(prefix + "/ai-picks/chat", "POST", chat, admin)[0] == 403)
    for origin, expected in (("https://staging.footballheritage.test:18443", True), ("https://evil.example.test", False)):
        status, _, headers = request(prefix + "/admin/features/wallet", "OPTIONS", headers={
            "Origin": origin, "Access-Control-Request-Method": "PATCH", "Access-Control-Request-Headers": "authorization,content-type"})
        check("CORS " + ("allowed" if expected else "denied"), (status in (200, 204) and headers.get("Access-Control-Allow-Origin") == origin) if expected else status == 400)
    check("logout", request(prefix + "/auth/logout", "POST", {}, user)[0] == 200)
    check("logged out session rejected", request(prefix + "/user/profile", token=user)[0] == 401)
finally:
    for key in ("wallet", "maintenance", "ai_chat"):
        patch(key, {field: saved[key][field] for field in ("enabled", "emergency_disabled", "maintenance_allowed")})
    patch("wallet/roles/user", {"enabled": role})
    request(target, "PATCH", {"enabled": override}, admin)
    (ROOT / ".staging/smoke-results.json").write_text(json.dumps(RESULTS, indent=2))
raise SystemExit(0 if all(row["passed"] for row in RESULTS) else 1)
