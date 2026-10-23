"""Start an isolated API, exercise actual saved sport candidates, then stop it."""

import argparse
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import subprocess
import sys
import time

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--port", type=int, default=5562)
    parser.add_argument("--basketball-leagues", action="store_true")
    parser.add_argument("--americanfootball-leagues", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(args.port)],
                               cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{args.port}/api/v1/sport-models"
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("Isolated API failed to start; check port and API dependencies")
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(.5)
        else:
            raise RuntimeError("API startup timed out")
        assert any(run["candidate_id"] == args.candidate_id for run in response.json()["runs"])
        kickoff = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        cases = [("basketball", "basketball_nba", "Boston Celtics", "Los Angeles Lakers", 200),
                 ("football", None, "Arsenal", "Chelsea", 200),
                 ("americanfootball", "americanfootball_nfl", "Seattle Seahawks", "New England Patriots", 503),
                 ("basketball", "basketball_ncaab", "Duke Blue Devils", "North Carolina Tar Heels", 422)]
        if args.basketball_leagues:
            cases = [("wnba", "basketball_wnba", "New York Liberty", "Las Vegas Aces", 200),
                     ("ncaab", "basketball_ncaab", "Duke Blue Devils", "North Carolina Tar Heels", 200),
                     ("ncaabw", "basketball_wncaab", "South Carolina Gamecocks", "Iowa Hawkeyes", 200),
                     ("wnba", "basketball_nba", "New York Liberty", "Las Vegas Aces", 422)]
        if args.americanfootball_leagues:
            cases = [("nfl", "americanfootball_nfl", "Kansas City Chiefs", "Buffalo Bills", 200),
                     ("ncaaf", "americanfootball_ncaaf", "Alabama", "Georgia", 200),
                     ("nfl", "americanfootball_ncaaf", "Kansas City Chiefs", "Buffalo Bills", 422),
                     ("ncaaf", "americanfootball_ncaaf", "Unknown Team", "Georgia", 422)]
        for sport, league, home, away, expected in cases:
            response = requests.post(url + "/preview", json={"candidate_id": args.candidate_id, "sport": sport,
                "league": league, "home_team": home, "away_team": away, "kickoff": kickoff}, timeout=30)
            assert response.status_code == expected, (sport, response.status_code, response.text)
            if expected == 200:
                result = response.json()
                assert result["sport"] == sport and result["active"] is False
                assert math.isclose(sum(result["probabilities"].values()), 1.)
                if sport == "nfl":
                    assert result["probability_basis"] == "CONDITIONAL_ON_NO_FINAL_TIE"
                    assert result["settlement_rule"] == "INCLUDING_OVERTIME_TIES_VOID"
                print(result, flush=True)
            print(f"{sport} / {league}: HTTP {response.status_code}", flush=True)
        print("Sport model API smoke checks passed", flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
