"""Read-only live audit of the API endpoints used by the Predictions page."""
import json
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests
from sqlalchemy import text


def main():
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "5563"],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = "http://127.0.0.1:5563/api/v1"
    output = {"audited_at": datetime.now(timezone.utc).isoformat(), "endpoints": {}}
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("Isolated API exited before startup")
            try:
                if requests.get(base + "/sport-models", timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(.5)
        else:
            raise RuntimeError("API startup timed out")
        matches = []
        for endpoint in ["/health", "/matches?limit=30", "/predictions/accuracy-data?days=30", "/predictions/history-data?page_size=5", "/predictions/history-data?page_size=5&result_filter=correct"]:
            try:
                response = requests.get(base + endpoint, timeout=20)
                data = response.json()
                output["endpoints"][endpoint] = {"status": response.status_code, "data": data}
                if endpoint.startswith("/matches") and response.status_code == 200:
                    matches = data
            except requests.RequestException as exc:
                output["endpoints"][endpoint] = {"error": type(exc).__name__}
        output["prediction_coverage"] = []
        for match in matches:
            response = requests.get(base + f"/predictions/{match['match_id']}", timeout=20)
            output["prediction_coverage"].append({"match_id": match["match_id"], "status": response.status_code, "prediction": response.json() if response.status_code == 200 else None})
        sys.path.insert(0, str(root))
        from api.db import get_db_connection
        queries = {
            "evaluation_provenance_30_days": """
                SELECT COUNT(*) AS prediction_rows, COUNT(DISTINCT m.match_id) AS fixtures,
                    COUNT(*) FILTER (WHERE p.created_at < m.date) AS pre_kickoff_rows,
                    COUNT(*) FILTER (WHERE p.created_at >= m.date) AS at_or_after_kickoff_rows,
                    COUNT(*) FILTER (WHERE m.date IS NULL) AS unknown_kickoff_rows
                FROM matches m JOIN predictions p ON m.match_id = p.match_id
                WHERE m.result IS NOT NULL AND (m.date IS NULL OR m.date >= NOW() - INTERVAL '30 days')
            """,
            "odds_inventory": """
                SELECT COUNT(*) AS rows, COUNT(DISTINCT match_id) AS fixtures,
                    MIN(home_win) AS minimum_home_odds, MAX(home_win) AS maximum_home_odds,
                    MAX(updated_at) AS newest_quote_at
                FROM odds
            """,
            "next_upcoming_fixtures": """
                SELECT match_id, home_team, away_team, date, status
                FROM matches WHERE date > NOW() AND status NOT IN ('FINISHED', 'CANCELLED')
                ORDER BY date ASC LIMIT 5
            """,
        }
        output["database_checks"] = {}
        with get_db_connection().connect() as connection:
            for name, query in queries.items():
                output["database_checks"][name] = [dict(row) for row in connection.execute(text(query)).mappings()]
        destination = root.parent / "stages/03-build/output/predictions-page-live-audit-20261009.json"
        destination.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"report": str(destination), "endpoint_statuses": {key: value.get("status", value.get("error")) for key, value in output["endpoints"].items()}, "matches": len(matches), "predictions_available": sum(item["status"] == 200 for item in output["prediction_coverage"])}))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
