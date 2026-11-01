"""Nigeria project: load World Bank indicators into MotherDuck bronze tables.

Usage (from the repo root):
    uv run --group pipelines python pipelines/nigeria/load_world_bank_indicators.py

    # prod_dwh: only the scheduled daily-pipeline workflow does this
    MOTHERDUCK_DATABASE=prod_dwh \
        uv run --group pipelines python pipelines/nigeria/load_world_bank_indicators.py
"""

import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import duckdb
import requests
from dotenv import load_dotenv

load_dotenv()

WB_BASE = "https://api.worldbank.org/v2"
COUNTRY = "NGA"
COUNTRY_NAME = "Nigeria"

ANNUAL_INDICATORS = {
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "SP.POP.TOTL": "Population, total",
}

MONTHLY_INDICATORS = {
    "DPANUSSPB": "Official exchange rate (LCU per US$, monthly)",
    "CPTOTNSXN": "CPI price index, not seasonally adjusted",
}

TOKEN = os.getenv("MOTHERDUCK_TOKEN")

# Which MotherDuck database to load: dev_dwh for local work, prod_dwh only for the
# scheduled job. Restricted to known names so a typo can't create a stray database.
DATABASE = os.getenv("MOTHERDUCK_DATABASE", "dev_dwh")
ALLOWED_DATABASES = {"dev_dwh", "prod_dwh"}

# bronze is shared by every project, so table names start with <project>_<source>_.
# Bronze tables this script owns. Created if missing, so a new database (like prod_dwh)
# is set up by code instead of by hand. Types match the original dev_dwh tables.
BRONZE_DDL = {
    "nigeria_world_bank_indicators_annual": """
        country_code    VARCHAR,
        country_name    VARCHAR,
        indicator_code  VARCHAR,
        indicator_name  VARCHAR,
        year            INTEGER,
        value           DOUBLE,
        extracted_at    TIMESTAMP
    """,
    "nigeria_world_bank_indicators_monthly": """
        country_code    VARCHAR,
        country_name    VARCHAR,
        indicator_code  VARCHAR,
        indicator_name  VARCHAR,
        year            INTEGER,
        month           INTEGER,
        value           DOUBLE,
        extracted_at    TIMESTAMP
    """,
}

# One extracted observation, keyed by bronze column name
Row = dict[str, Any]


def utc_now() -> datetime:
    """Current UTC time without a timezone, for the bronze TIMESTAMP columns.

    DuckDB converts a timezone-aware value to the machine's local time before storing it
    in a plain TIMESTAMP. Laptop runs in Lagos (UTC+1) were stored an hour ahead of the
    GitHub Actions runs (UTC). A naive UTC value is stored as-is everywhere.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def _get(url: str, params: dict[str, Any], max_retries: int = 3) -> Any:
    """Return the parsed JSON body, retrying failed requests with a growing pause.

    Args:
        url: World Bank API endpoint.
        params: Query string parameters.
        max_retries: Attempts before the last HTTP error is raised.
    """
    for attempt in range(1, max_retries + 1):
        resp = requests.get(url, params=params, timeout=30)
        if resp.ok:
            return resp.json()
        if attempt == max_retries:
            resp.raise_for_status()
        time.sleep(1.5 * attempt)
    raise RuntimeError(f"No response from {url} after {max_retries} attempts")


def fetch_annual(
    indicator_code: str, start_year: int = 1990, end_year: int | None = None
) -> list[Row]:
    """Fetch one annual indicator for Nigeria, skipping years without a value.

    Args:
        indicator_code: World Bank code, a key of ANNUAL_INDICATORS.
        start_year: First year to request.
        end_year: Last year to request; defaults to the current year.
    """
    end_year = end_year or datetime.now(UTC).year
    url = f"{WB_BASE}/country/{COUNTRY}/indicator/{indicator_code}"
    params = {"format": "json", "date": f"{start_year}:{end_year}", "per_page": 1000}
    payload = _get(url, params)
    rows = payload[1] or []
    extracted_at = utc_now()
    return [
        {
            "country_code": COUNTRY,
            "country_name": COUNTRY_NAME,
            "indicator_code": indicator_code,
            "indicator_name": ANNUAL_INDICATORS[indicator_code],
            "year": int(r["date"]),
            "value": float(r["value"]),
            "extracted_at": extracted_at,
        }
        for r in rows
        if r.get("value") is not None
    ]


def fetch_monthly(
    indicator_code: str, start_year: int = 2010, end_year: int | None = None
) -> list[Row]:
    """Fetch one monthly indicator for Nigeria, skipping months without a value.

    Args:
        indicator_code: World Bank code, a key of MONTHLY_INDICATORS.
        start_year: First year to request.
        end_year: Last year to request; defaults to the current year.
    """
    end_year = end_year or datetime.now(UTC).year
    url = f"{WB_BASE}/country/{COUNTRY}/indicator/{indicator_code}"
    params = {
        "format": "json",
        "source": 15,
        "date": f"{start_year}M01:{end_year}M12",
        "per_page": 1000,
    }
    payload = _get(url, params)
    rows = payload[1] or []
    extracted_at = utc_now()
    parsed: list[Row] = []
    for r in rows:
        if r.get("value") is None:
            continue
        year_str, month_str = r["date"].split("M")
        parsed.append(
            {
                "country_code": COUNTRY,
                "country_name": COUNTRY_NAME,
                "indicator_code": indicator_code,
                "indicator_name": MONTHLY_INDICATORS[indicator_code],
                "year": int(year_str),
                "month": int(month_str),
                "value": float(r["value"]),
                "extracted_at": extracted_at,
            }
        )
    return parsed


def fetch_all(indicators: dict[str, str], fetch: Callable[[str], list[Row]]) -> list[Row]:
    """Fetch every indicator, stopping before any load if one comes back empty.

    An empty response means an API problem, not "no data": loading it would wipe that
    indicator from bronze and empty the gold table built on it.

    Args:
        indicators: Indicator codes to fetch, mapped to their names.
        fetch: fetch_annual or fetch_monthly.
    """
    rows: list[Row] = []
    for code, name in indicators.items():
        fetched = fetch(code)
        if not fetched:
            raise SystemExit(f"Error: 0 rows fetched for {code} ({name}); bronze left unchanged")
        print(f"{code}: {len(fetched)} rows")
        rows.extend(fetched)
    return rows


def ensure_bronze(con: duckdb.DuckDBPyConnection) -> None:
    con.sql(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    con.sql(f"CREATE SCHEMA IF NOT EXISTS {DATABASE}.bronze")
    for table, columns in BRONZE_DDL.items():
        con.sql(f"CREATE TABLE IF NOT EXISTS {DATABASE}.bronze.{table} ({columns})")


def load_rows(
    con: duckdb.DuckDBPyConnection, annual_rows: list[Row], monthly_rows: list[Row]
) -> None:
    """Replace both bronze tables. Call inside a transaction."""
    con.execute(f"DELETE FROM {DATABASE}.bronze.nigeria_world_bank_indicators_annual")
    con.execute(f"DELETE FROM {DATABASE}.bronze.nigeria_world_bank_indicators_monthly")

    con.executemany(
        f"""
        INSERT INTO {DATABASE}.bronze.nigeria_world_bank_indicators_annual
        (country_code, country_name, indicator_code, indicator_name, year, value, extracted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["country_code"],
                r["country_name"],
                r["indicator_code"],
                r["indicator_name"],
                r["year"],
                r["value"],
                r["extracted_at"],
            )
            for r in annual_rows
        ],
    )

    con.executemany(
        f"""
        INSERT INTO {DATABASE}.bronze.nigeria_world_bank_indicators_monthly
        (country_code, country_name, indicator_code, indicator_name,
         year, month, value, extracted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["country_code"],
                r["country_name"],
                r["indicator_code"],
                r["indicator_name"],
                r["year"],
                r["month"],
                r["value"],
                r["extracted_at"],
            )
            for r in monthly_rows
        ],
    )


def main() -> None:
    if DATABASE not in ALLOWED_DATABASES:
        raise SystemExit(
            f"Error: MOTHERDUCK_DATABASE={DATABASE!r}, expected one of {sorted(ALLOWED_DATABASES)}"
        )
    if not TOKEN:
        raise SystemExit("Error: MOTHERDUCK_TOKEN is not set")

    # Fetch everything before touching MotherDuck, so an API failure changes nothing
    annual_rows = fetch_all(ANNUAL_INDICATORS, fetch_annual)
    monthly_rows = fetch_all(MONTHLY_INDICATORS, fetch_monthly)

    print(f"Loading into {DATABASE}")
    con = duckdb.connect(f"md:?motherduck_token={TOKEN}")
    ensure_bronze(con)

    # Replace both tables in one transaction: if any insert fails, the old rows stay
    # instead of leaving bronze empty for the next dbt run.
    con.execute("BEGIN TRANSACTION")
    try:
        load_rows(con, annual_rows, monthly_rows)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    for table in BRONZE_DDL:
        result = con.sql(f"SELECT COUNT(*) FROM {DATABASE}.bronze.{table}").fetchone()
        count = result[0] if result else 0
        print(f"{DATABASE}.bronze.{table}: {count} rows")


if __name__ == "__main__":
    main()
