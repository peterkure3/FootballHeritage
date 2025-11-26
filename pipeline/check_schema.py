"""Utility script to inspect/validate pipeline database schema."""

import argparse
import sys
from contextlib import closing
from typing import Dict, Iterable, List, Set

import psycopg2

from config import DATABASE_URI


TABLE_REQUIRED_COLUMNS: Dict[str, Set[str]] = {
    "matches": {
        "match_id",
        "competition",
        "season",
        "date",
        "home_team",
        "away_team",
        "status",
    },
    "odds": {
        "match_id",
        "bookmaker",
        "home_win",
        "draw",
        "away_win",
    },
    "nba_games": {
        "game_id",
        "sport_key",
        "sport",
        "sport_title",
        "commence_time",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "completed",
        "last_update",
        "source_file",
        "updated_at",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dsn",
        default=DATABASE_URI,
        help="PostgreSQL connection string (default: value from config.DATABASE_URI)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List tables in the public schema",
    )
    parser.add_argument(
        "--table",
        action="append",
        default=[],
        metavar="NAME",
        help="Show columns for a specific table (can be used multiple times)",
    )
    parser.add_argument(
        "--ensure",
        action="append",
        default=[],
        metavar="NAME",
        help="Ensure a table (and required columns, if known) exist; exits 1 on failure",
    )
    return parser.parse_args()


def list_tables(cur) -> List[str]:
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
    )
    tables = [row[0] for row in cur.fetchall()]
    print("Tables in pipeline database:")
    for table in tables:
        print(f"  - {table}")
    return tables


def get_columns(cur, table_name: str) -> List[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return [row[0] for row in cur.fetchall()]


def show_columns(cur, table_name: str) -> None:
    columns = get_columns(cur, table_name)
    if not columns:
        print(f"Table '{table_name}' not found.")
        return
    print(f"\n{table_name} columns:")
    for column in columns:
        print(f"  - {column}")


def table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        (table_name,),
    )
    return cur.fetchone()[0]


def ensure_table(cur, table_name: str, required_columns: Iterable[str]) -> bool:
    ok = True
    if not table_exists(cur, table_name):
        print(f"ERROR: Table '{table_name}' does not exist.")
        return False

    if required_columns:
        actual_columns = set(get_columns(cur, table_name))
        missing_columns = set(required_columns) - actual_columns
        if missing_columns:
            ok = False
            print(
                "ERROR: Table '{table}' is missing columns: {cols}".format(
                    table=table_name,
                    cols=", ".join(sorted(missing_columns)),
                )
            )
        else:
            print(f"Table '{table_name}' has all required columns.")
    else:
        print(f"Table '{table_name}' exists.")
    return ok


def default_report(cur) -> None:
    list_tables(cur)
    show_columns(cur, "matches")
    if table_exists(cur, "odds"):
        show_columns(cur, "odds")


def main() -> None:
    args = parse_args()
    exit_code = 0

    with closing(psycopg2.connect(args.dsn)) as conn:
        with conn.cursor() as cur:
            performed = False

            if args.list:
                performed = True
                list_tables(cur)

            for table in args.table:
                performed = True
                show_columns(cur, table)

            for ensure_target in args.ensure:
                performed = True
                required = TABLE_REQUIRED_COLUMNS.get(ensure_target, set())
                if not ensure_table(cur, ensure_target, required):
                    exit_code = 1

            if not performed:
                default_report(cur)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
