"""Run isolated HTTP verification against locally cached FPL data."""
import json
import socket
import threading
import time
import urllib.request
import urllib.error
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn
from fastapi import FastAPI
from api.routers.fpl import router

app = FastAPI()
app.include_router(router)
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
thread.start()

def request(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)

try:
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started, "Verification server did not start"
    status, advice = request("/fpl/advice")
    assert status == 200, advice
    team = advice["optimal_team"]
    payload = dict(squad_ids=[p["id"] for p in team["players"]], starter_ids=[p["id"] for p in team["starting_xi"]], captain_id=team["captain"]["id"], vice_captain_id=team["vice_captain"]["id"])
    status, evaluated = request("/fpl/team/evaluate", payload)
    assert status == 200, evaluated
    assert evaluated["total_cost"] == team["total_cost"]
    assert evaluated["expected_points"] == team["expected_points"]
    payload["captain_id"] = payload["vice_captain_id"]
    invalid_status, invalid = request("/fpl/team/evaluate", payload)
    assert invalid_status == 422, invalid
    print(json.dumps({"valid_team": status, "invalid_captains": invalid_status, "cost": evaluated["total_cost"], "expected_points": evaluated["expected_points"]}))
finally:
    server.should_exit = True
    thread.join(timeout=10)
    sock.close()
