"""Read-only endpoint verification against a saved NFL candidate."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "pipeline"))

from fastapi import FastAPI
import json
import socket
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
import uvicorn
from api.routers.sport_models import router
from models.sport_predict import catalog

app = FastAPI()
app.include_router(router)
run = next(r for r in catalog() if r["sports"].get("nfl", {}).get("status") == "candidate")
sock = socket.socket()
sock.bind(("127.0.0.1", 0))
base = f"http://127.0.0.1:{sock.getsockname()[1]}/sport-models/teams?"
server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
thread.start()
try:
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    with urlopen(base + urlencode({
        "candidate_id": run["candidate_id"], "sport": "nfl", "league": "americanfootball_nfl",
    }), timeout=20) as response:
        teams = json.load(response)["teams"]
        assert "Kansas City Chiefs" in teams and "Buffalo Bills" in teams
        print({"status": response.status, "candidate": run["candidate_id"], "teams": len(teams)})
    try:
        urlopen(base + urlencode({"candidate_id": "../outside", "sport": "nfl"}), timeout=20)
        raise AssertionError("Invalid candidate was accepted")
    except HTTPError as exc:
        assert exc.code == 422
        print({"invalid_candidate_status": exc.code})
finally:
    server.should_exit = True
    thread.join(timeout=10)
    sock.close()
