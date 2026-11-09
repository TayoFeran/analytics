"""Nigeria Data website: export the data the site shows from MotherDuck to JSON files.

Runs every queries/<name>.sql against MotherDuck and writes src/data/<name>.json, which
Astro reads when it builds the pages. To add data to the site, add a .sql file: this
script doesn't need to change. Also writes src/data/export_info.json (when the export
ran, from which database, and how many rows each file has).

Usage (from the repo root):
    uv run --group pipelines python dashboards/nigeria-data-web/export_site_data.py

    # prod_dwh: only the scheduled daily-pipeline workflow does this
    MOTHERDUCK_DATABASE=prod_dwh \
        uv run --group pipelines python dashboards/nigeria-data-web/export_site_data.py
"""

import json
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
from dotenv import load_dotenv

load_dotenv()

SITE_DIR = Path(__file__).resolve().parent
QUERY_DIR = SITE_DIR / "queries"
OUTPUT_DIR = SITE_DIR / "src" / "data"

DATABASE = os.getenv("MOTHERDUCK_DATABASE", "dev_dwh")
ALLOWED_DATABASES = {"dev_dwh", "prod_dwh"}


def to_json_value(value: Any) -> Any:
    """Turn DuckDB result values into types JSON can hold."""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def run_query(con: duckdb.DuckDBPyConnection, sql_file: Path) -> list[dict[str, Any]]:
    result = con.sql(sql_file.read_text(encoding="utf-8"))
    columns = result.columns
    return [
        {column: to_json_value(value) for column, value in zip(columns, row, strict=True)}
        for row in result.fetchall()
    ]


def main() -> None:
    if DATABASE not in ALLOWED_DATABASES:
        raise SystemExit(
            f"Error: MOTHERDUCK_DATABASE={DATABASE!r}, expected one of {sorted(ALLOWED_DATABASES)}"
        )
    if not os.getenv("MOTHERDUCK_TOKEN"):
        raise SystemExit("Error: MOTHERDUCK_TOKEN is not set")

    sql_files = sorted(QUERY_DIR.glob("*.sql"))
    if not sql_files:
        raise SystemExit(f"Error: no .sql files in {QUERY_DIR}")

    print(f"Exporting from {DATABASE}")
    # The MotherDuck extension reads MOTHERDUCK_TOKEN from the environment. Never put the
    # token in the connection string: DuckDB echoes it in error messages.
    con = duckdb.connect(":memory:")
    con.execute("ATTACH 'md:'")
    # Lets the queries say datamart.x instead of naming the database, so the same SQL
    # runs against dev_dwh and prod_dwh.
    con.execute(f"USE {DATABASE}")

    # Run every query before writing anything, so a failure never leaves a mix of old and
    # new files behind.
    results: dict[str, list[dict[str, Any]]] = {}
    for sql_file in sql_files:
        rows = run_query(con, sql_file)
        # An empty result would publish an empty page, so stop instead
        if not rows:
            raise SystemExit(f"Error: {sql_file.name} returned no rows")
        results[sql_file.stem] = rows

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in results.items():
        path = OUTPUT_DIR / f"{name}.json"
        # Compact JSON: these files are downloaded on mobile data
        path.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
        print(f"Wrote {path.name} ({len(rows)} rows, {path.stat().st_size // 1024} KB)")

    info = {
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "database": DATABASE,
        "files": {name: len(rows) for name, rows in results.items()},
    }
    (OUTPUT_DIR / "export_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"Wrote {len(results)} data files and export_info.json")


if __name__ == "__main__":
    main()
