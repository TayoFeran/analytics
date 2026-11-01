"""<Project> project: load <source> <what> into MotherDuck bronze tables.

Usage (from the repo root):
    uv run --group pipelines python pipelines/<project>/load_<source>_<what>.py

    # prod_dwh: only the scheduled daily-pipeline workflow does this
    MOTHERDUCK_DATABASE=prod_dwh \
        uv run --group pipelines python pipelines/<project>/load_<source>_<what>.py

TEMPLATE: copied from .claude/skills/add-project/templates/load_source_template.py.
Replace every <placeholder> and TODO, then delete this paragraph. Keep the safety
checks: allowed databases, fetch-before-connect, stop on 0 rows, one transaction, UTC.
"""

import os
from datetime import UTC, datetime
from typing import Any

import duckdb
import requests
from dotenv import load_dotenv

load_dotenv()

# Same name as pipelines/<project>/ and dbt gold/<project>/ (lowercase snake_case)
PROJECT = "<project>"
SOURCE = "<source>"

TOKEN = os.getenv("MOTHERDUCK_TOKEN")
# TODO: if the source needs a key, read it here, add it to .env.example and as a GitHub secret
# API_KEY = os.getenv("<SOURCE>_API_KEY")

# Which MotherDuck database to load: dev_dwh for local work, prod_dwh only for the
# scheduled job. Restricted to known names so a typo can't create a stray database.
DATABASE = os.getenv("MOTHERDUCK_DATABASE", "dev_dwh")
ALLOWED_DATABASES = {"dev_dwh", "prod_dwh"}

# bronze is shared by every project, so table names start with <project>_<source>_.
# Created if missing, so dev_dwh and prod_dwh are set up by code, not by hand.
TABLE = f"{PROJECT}_{SOURCE}_<what>"
BRONZE_DDL = {
    TABLE: """
        <column_1>      VARCHAR,
        <column_2>      DOUBLE,
        extracted_at    TIMESTAMP
    """,
}

# One extracted row, keyed by bronze column name (same order as BRONZE_DDL)
Row = dict[str, Any]


def utc_now() -> datetime:
    """Current UTC time without a timezone, for bronze TIMESTAMP columns.

    DuckDB converts a timezone-aware value to the machine's local time before storing it
    in a plain TIMESTAMP, so laptop runs would be stored in local time. A naive UTC value
    is stored as-is everywhere.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def fetch_rows() -> list[Row]:
    """Fetch everything from the source. TODO: replace with the real API calls.

    Return one dict per row with exactly the bronze column names as keys.
    """
    extracted_at = utc_now()
    resp = requests.get("<https://api.example.com/endpoint>", timeout=30)
    resp.raise_for_status()
    return [
        {
            "<column_1>": item["<field_1>"],
            "<column_2>": float(item["<field_2>"]),
            "extracted_at": extracted_at,
        }
        for item in resp.json()
    ]


def ensure_bronze(con: duckdb.DuckDBPyConnection) -> None:
    con.sql(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    con.sql(f"CREATE SCHEMA IF NOT EXISTS {DATABASE}.bronze")
    for table, columns in BRONZE_DDL.items():
        con.sql(f"CREATE TABLE IF NOT EXISTS {DATABASE}.bronze.{table} ({columns})")


def replace_table(con: duckdb.DuckDBPyConnection, table: str, rows: list[Row]) -> None:
    """Replace all rows of one bronze table. Call inside a transaction."""
    columns = list(rows[0])
    placeholders = ", ".join("?" for _ in columns)
    con.execute(f"DELETE FROM {DATABASE}.bronze.{table}")
    con.executemany(
        f"INSERT INTO {DATABASE}.bronze.{table} ({', '.join(columns)}) VALUES ({placeholders})",
        [tuple(r[c] for c in columns) for r in rows],
    )


def main() -> None:
    if DATABASE not in ALLOWED_DATABASES:
        raise SystemExit(
            f"Error: MOTHERDUCK_DATABASE={DATABASE!r}, expected one of {sorted(ALLOWED_DATABASES)}"
        )
    if not TOKEN:
        raise SystemExit("Error: MOTHERDUCK_TOKEN is not set")

    # Fetch everything before touching MotherDuck, so an API failure changes nothing.
    # An empty response means an API problem, not "no data": loading it would empty bronze.
    rows = fetch_rows()
    if not rows:
        raise SystemExit(f"Error: 0 rows fetched for {TABLE}; bronze left unchanged")
    print(f"{TABLE}: {len(rows)} rows fetched")

    print(f"Loading into {DATABASE}")
    con = duckdb.connect(f"md:?motherduck_token={TOKEN}")
    ensure_bronze(con)

    # One transaction: if the insert fails, the old rows stay
    con.execute("BEGIN TRANSACTION")
    try:
        replace_table(con, TABLE, rows)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    result = con.sql(f"SELECT COUNT(*) FROM {DATABASE}.bronze.{TABLE}").fetchone()
    print(f"{DATABASE}.bronze.{TABLE}: {result[0] if result else 0} rows")


if __name__ == "__main__":
    main()
