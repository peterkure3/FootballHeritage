"""Read-only privileges/migration checks plus a deliberately rejected audit UPDATE."""
from pathlib import Path
import json
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

root = Path(__file__).resolve().parents[2]
values = dict(line.split("=", 1) for line in (root / ".staging/secrets.env").read_text().splitlines())
engine = create_engine("postgresql://fh_api:" + values["STAGING_API_PASSWORD"] + "@127.0.0.1:15439/fh_staging_app")
with engine.connect() as connection:
    checks = {
        "runtime_cannot_create_public_objects": not connection.scalar(text("SELECT has_schema_privilege(current_user,'public','CREATE')")),
        "runtime_cannot_truncate_audit": not connection.scalar(text("SELECT has_table_privilege(current_user,'feature_audit_logs','TRUNCATE')")),
        "runtime_cannot_rewrite_migrations": not connection.scalar(text("SELECT has_table_privilege(current_user,'_sqlx_migrations','UPDATE')")),
        "complete_migration_chain": connection.scalar(text("SELECT COUNT(*) FROM _sqlx_migrations WHERE success")) == len(list((root / "backend/migrations").glob("*.sql"))),
        "unique_wallet_owner_index": bool(connection.scalar(text("SELECT indisunique FROM pg_index WHERE indexrelid='wallets_unique_user_id'::regclass"))),
    }
with engine.connect() as connection:
    transaction = connection.begin()
    try:
        # A populated audit row must be immutable to the actual runtime role.
        connection.execute(text("UPDATE feature_audit_logs SET action='forbidden-test' WHERE id=(SELECT MIN(id) FROM feature_audit_logs)"))
    except DBAPIError:
        checks["runtime_audit_update_rejected"] = True
    else:
        checks["runtime_audit_update_rejected"] = False
    finally:
        transaction.rollback()
engine.dispose()
(root / ".staging/database-results.json").write_text(json.dumps(checks, indent=2))
print(json.dumps(checks))
raise SystemExit(0 if all(checks.values()) else 1)
