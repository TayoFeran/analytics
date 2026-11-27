"""Nigeria project: load the FAAC figures read from the OAGF reports into MotherDuck bronze.

refine_faac_reports.py reads the original OAGF reports into CSV files in
data/nigeria/faac/oagf/. This script loads those files as written: every printed figure in
long form (month, state or council, column, amount), with the columns' printed headers, the
reports they came from and the known mistakes in them. Grouping columns into revenue lines
and computing totals happen in dbt (silver/nigeria/faac_oagf/, gold/nigeria/).

Usage (from the repo root):
    uv run --group pipelines python pipelines/nigeria/load_faac_oagf_reports.py

    # prod_dwh: only the scheduled daily-pipeline workflow does this
    MOTHERDUCK_DATABASE=prod_dwh \
        uv run --group pipelines python pipelines/nigeria/load_faac_oagf_reports.py
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

PROJECT = "nigeria"
SOURCE = "faac_oagf"

TOKEN = os.getenv("MOTHERDUCK_TOKEN")

# Which MotherDuck database to load: dev_dwh for local work, prod_dwh only for the
# scheduled job. Restricted to known names so a typo can't create a stray database.
DATABASE = os.getenv("MOTHERDUCK_DATABASE", "dev_dwh")
ALLOWED_DATABASES = {"dev_dwh", "prod_dwh"}

# The CSV files live in the repo, so adding a month is a commit
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / PROJECT / "faac" / "oagf"

# Bronze table -> (CSV files relative to DATA_DIR, columns and types as in the files).
# Types are given, not guessed: a guess from the first rows could read column_id "14a" or
# an empty lga_sn wrongly.
TABLES: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "reports": (
        "reports.csv",
        [
            ("shared_month", "VARCHAR"),
            ("source_type", "VARCHAR"),
            ("file_name", "VARCHAR"),
            ("sha256", "VARCHAR"),
            ("page", "INTEGER"),
            ("reader_version", "VARCHAR"),
        ],
    ),
    "state_columns": (
        "columns.csv",
        [
            ("shared_month", "VARCHAR"),
            ("position", "INTEGER"),
            ("column_id", "VARCHAR"),
            ("column_header", "VARCHAR"),
            ("header_key", "VARCHAR"),
        ],
    ),
    "state_figures": (
        "state_figures/*.csv",
        [
            ("shared_month", "VARCHAR"),
            ("row_number", "INTEGER"),
            ("beneficiary", "VARCHAR"),
            ("row_type", "VARCHAR"),
            ("lgc_count", "INTEGER"),
            ("column_id", "VARCHAR"),
            ("amount", "DECIMAL(18,2)"),
        ],
    ),
    "lga_columns": (
        "lga_columns.csv",
        [
            ("shared_month", "VARCHAR"),
            ("position", "INTEGER"),
            ("column_id", "VARCHAR"),
            ("column_header", "VARCHAR"),
            ("header_key", "VARCHAR"),
        ],
    ),
    "lga_figures": (
        "lga_figures/*/*.csv",
        [
            ("shared_month", "VARCHAR"),
            ("state", "VARCHAR"),
            ("lga_sn", "INTEGER"),
            ("lga", "VARCHAR"),
            ("row_type", "VARCHAR"),
            ("column_id", "VARCHAR"),
            ("amount", "DECIMAL(18,2)"),
        ],
    ),
    "known_report_errors": (
        "known_report_errors.csv",
        [("shared_month", "VARCHAR"), ("state", "VARCHAR"), ("error", "VARCHAR")],
    ),
    "notes": ("notes.csv", [("shared_month", "VARCHAR"), ("note", "VARCHAR")]),
}


def bronze_name(table: str) -> str:
    return f"{PROJECT}_{SOURCE}_{table}"


def utc_now() -> datetime:
    """Current UTC time without a timezone, for bronze TIMESTAMP columns.

    DuckDB converts a timezone-aware value to the machine's local time before storing it
    in a plain TIMESTAMP, so laptop runs would be stored in local time. A naive UTC value
    is stored as-is everywhere.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def stage_all(con: duckdb.DuckDBPyConnection) -> None:
    """Read every CSV file into a local in-memory table, checking each has rows.

    Everything is read before MotherDuck is touched, so a missing or broken file changes
    nothing. Uploading a staged table with one INSERT ... SELECT takes seconds; inserting
    half a million rows one by one would take hours.
    """
    loaded_at = utc_now()
    for table, (pattern, columns) in TABLES.items():
        files = sorted(DATA_DIR.glob(pattern))
        if not files:
            raise SystemExit(f"Error: no files match {DATA_DIR / pattern}; bronze left unchanged")
        types = ", ".join(f"'{name}': '{kind}'" for name, kind in columns)
        paths = ", ".join(f"'{path.as_posix()}'" for path in files)
        con.execute(
            f"CREATE OR REPLACE TABLE memory.main.{table} AS "
            f"SELECT *, ?::TIMESTAMP AS loaded_at FROM read_csv([{paths}], header = true, "
            f"columns = {{{types}}}, auto_detect = false)",
            [loaded_at],
        )
        result = con.sql(f"SELECT COUNT(*) FROM memory.main.{table}").fetchone()
        rows = result[0] if result else 0
        if rows == 0:
            raise SystemExit(f"Error: 0 rows in {pattern}; bronze left unchanged")
        print(f"{pattern}: {len(files)} file(s), {rows} rows")


def ensure_bronze(con: duckdb.DuckDBPyConnection) -> None:
    con.sql(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    con.sql(f"CREATE SCHEMA IF NOT EXISTS {DATABASE}.bronze")
    for table, (_, columns) in TABLES.items():
        definition = ", ".join(f"{name} {kind}" for name, kind in columns)
        con.sql(
            f"CREATE TABLE IF NOT EXISTS {DATABASE}.bronze.{bronze_name(table)} "
            f"({definition}, loaded_at TIMESTAMP)"
        )


def replace_table(con: duckdb.DuckDBPyConnection, table: str) -> None:
    """Replace one bronze table with its staged rows. Call inside a transaction."""
    columns = ", ".join([name for name, _ in TABLES[table][1]] + ["loaded_at"])
    target = f"{DATABASE}.bronze.{bronze_name(table)}"
    con.execute(f"DELETE FROM {target}")
    con.execute(f"INSERT INTO {target} ({columns}) SELECT {columns} FROM memory.main.{table}")


def main() -> None:
    if DATABASE not in ALLOWED_DATABASES:
        raise SystemExit(
            f"Error: MOTHERDUCK_DATABASE={DATABASE!r}, expected one of {sorted(ALLOWED_DATABASES)}"
        )
    if not TOKEN:
        raise SystemExit("Error: MOTHERDUCK_TOKEN is not set")

    con = duckdb.connect(":memory:")
    stage_all(con)

    print(f"Loading into {DATABASE}")
    # The MotherDuck extension reads MOTHERDUCK_TOKEN from the environment. Never put the
    # token in the connection string: DuckDB echoes it in error messages.
    con.execute("ATTACH 'md:'")
    ensure_bronze(con)

    # One transaction for all tables: a failure keeps the previous load intact, and the
    # figures never get out of step with their column headers
    con.execute("BEGIN TRANSACTION")
    try:
        for table in TABLES:
            replace_table(con, table)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    for table in TABLES:
        result = con.sql(f"SELECT COUNT(*) FROM {DATABASE}.bronze.{bronze_name(table)}").fetchone()
        print(f"{DATABASE}.bronze.{bronze_name(table)}: {result[0] if result else 0} rows")


if __name__ == "__main__":
    main()
