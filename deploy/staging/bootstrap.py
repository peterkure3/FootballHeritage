"""Synthetic fixtures and two recovery admins in the isolated local DBs only."""
from pathlib import Path
import json
import os
import sys
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[2]
values = dict(line.split("=", 1) for line in (root / ".staging/secrets.env").read_text().splitlines())
sys.path.insert(0, str(root / "pipeline"))
owner = "postgresql://staging_owner:" + values["STAGING_DB_PASSWORD"] + "@127.0.0.1:15439/"
os.environ["DATABASE_URL"] = owner + "fh_staging_predictions"
os.environ["HERITAGE_DATABASE_URL"] = owner + "fh_staging_app"
from sqlalchemy import create_engine, text
from etl.load_to_db import ensure_schema_exists

predictions = create_engine(owner + "fh_staging_predictions")
ensure_schema_exists(predictions)
with predictions.begin() as connection:
    connection.execute(text("""INSERT INTO matches(match_id,competition,date,home_team,away_team,status,data_source)
        VALUES(990000001,'Staging League',(NOW() AT TIME ZONE 'UTC')+INTERVAL '1 day','Staging Home','Staging Away','SCHEDULED','synthetic-staging')
        ON CONFLICT(match_id) DO UPDATE SET date=EXCLUDED.date"""))
    if not connection.scalar(text("SELECT COUNT(*) FROM predictions WHERE match_id=990000001 AND model_version='staging-fixture'")):
        connection.execute(text("""INSERT INTO predictions(match_id,model_version,winner,home_prob,draw_prob,away_prob)
            VALUES(990000001,'staging-fixture','home_win',0.6,0.25,0.15)"""))
        connection.execute(text("INSERT INTO odds(match_id,bookmaker,home_win,draw,away_win) VALUES(990000001,'Synthetic Test Book',2,4,5)"))
    connection.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO fh_readonly"))
predictions.dispose()

accounts = {}
application = create_engine(owner + "fh_staging_app")
for name in ("admin", "recovery", "user", "restricted"):
    email = name + "@staging.example.test"
    body = {"email": email, "password": values["STAGING_ADMIN_PASSWORD"], "first_name": "Staging",
            "last_name": name, "date_of_birth": "1990-01-01", "phone": None, "address": None}
    request = urllib.request.Request("http://127.0.0.1:18888/api/v1/auth/register", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    with application.connect() as connection:
        exists = connection.scalar(text("SELECT id FROM users WHERE email=:email"), {"email": email})
    if not exists:
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status not in (200, 201):
                    raise RuntimeError("Staging registration failed")
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"Staging {name} registration returned HTTP {error.code}") from None
    with application.begin() as connection:
        role = "superadmin" if name in ("admin", "recovery") else "user"
        identifier = connection.scalar(text("UPDATE users SET role=:role WHERE email=:email RETURNING id"), {"role": role, "email": email})
        accounts[name] = {"email": email, "id": str(identifier)}
with application.begin() as connection:
    connection.execute(text("REVOKE ALL ON _sqlx_migrations FROM fh_api"))
    connection.execute(text("GRANT SELECT ON _sqlx_migrations TO fh_api"))
application.dispose()
(root / ".staging/accounts.json").write_text(json.dumps(accounts, indent=2))
print("Synthetic predictions and isolated test accounts prepared; no real-money or provider operations performed.")
