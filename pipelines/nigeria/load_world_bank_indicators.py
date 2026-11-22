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
    # Naira GDP and real growth: dollar GDP moves with the exchange rate, so it can't show growth
    "NY.GDP.MKTP.CN": "GDP (current LCU)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
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

# How old the World Bank rows may get while the API is down before the run fails.
# CPI, FX and GDP change monthly or yearly, so a few days late is harmless, but a
# longer outage must fail loudly rather than leave the site quietly out of date.
MAX_STALE_DAYS = 7

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


class WorldBankUnavailable(Exception):
    """The World Bank API is down or answering badly; bronze is left as it is."""


def _get(url: str, params: dict[str, Any], max_retries: int = 5) -> Any:
    """Return the parsed JSON body, retrying outages with a doubling pause.

    The API has had outages lasting days (timeouts and 502s, November 2026), so a
    failure here is usually theirs. A 4xx other than 429 means our request is wrong,
    which retrying can't fix, so it fails at once.

    Args:
        url: World Bank API endpoint.
        params: Query string parameters.
        max_retries: Attempts before giving up with WorldBankUnavailable.
    """
    problem = ""
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
        except requests.RequestException as e:
            problem = f"{type(e).__name__}: {e}"
        else:
            if resp.ok:
                try:
                    return resp.json()
                except ValueError:
                    # The API sometimes sends an HTML or XML error page with status 200
                    problem = "response was not JSON"
            elif resp.status_code >= 500 or resp.status_code == 429:
                problem = f"HTTP {resp.status_code}"
            else:
                resp.raise_for_status()
        if attempt < max_retries:
            wait = 10 * 2 ** (attempt - 1)
            print(f"Attempt {attempt} failed ({problem}), retrying in {wait}s")
            time.sleep(wait)
    raise WorldBankUnavailable(f"{url}: {problem} after {max_retries} attempts")


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
            raise WorldBankUnavailable(f"0 rows fetched for {code} ({name})")
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


def keep_existing_rows(con: duckdb.DuckDBPyConnection, reason: str) -> None:
    """Let the run carry on with the rows already in bronze, unless they're too old.

    Without this, one World Bank outage stopped the FAAC load, dbt and the website
    deploy for a week. The age check stops a long outage going unnoticed.

    Args:
        con: Open MotherDuck connection.
        reason: What went wrong with the API, for the log.
    """
    # The older of the two tables decides, so neither can go stale unnoticed
    last_loads: list[datetime] = []
    for table in BRONZE_DDL:
        result = con.sql(f"SELECT MAX(extracted_at) FROM {DATABASE}.bronze.{table}").fetchone()
        if result and result[0] is not None:
            last_loads.append(result[0])
    if len(last_loads) < len(BRONZE_DDL):
        raise SystemExit(f"Error: World Bank API unavailable and no rows in bronze ({reason})")

    age_days = (utc_now() - min(last_loads)).total_seconds() / 86400
    if age_days > MAX_STALE_DAYS:
        raise SystemExit(
            f"Error: World Bank API unavailable and bronze was last loaded {age_days:.1f} days "
            f"ago, more than {MAX_STALE_DAYS} ({reason})"
        )

    message = (
        f"World Bank API unavailable, kept the rows loaded {age_days:.1f} days ago "
        f"(fails after {MAX_STALE_DAYS} days): {reason}"
    )
    print(f"Warning: {message}")
    # A yellow annotation on the run summary, so a green run still shows the problem
    if os.getenv("GITHUB_ACTIONS") == "true":
        print(f"::warning title=World Bank API unavailable::{message}")


def main() -> None:
    if DATABASE not in ALLOWED_DATABASES:
        raise SystemExit(
            f"Error: MOTHERDUCK_DATABASE={DATABASE!r}, expected one of {sorted(ALLOWED_DATABASES)}"
        )
    if not TOKEN:
        raise SystemExit("Error: MOTHERDUCK_TOKEN is not set")

    # Fetch everything before touching MotherDuck, so an API failure changes nothing
    try:
        annual_rows = fetch_all(ANNUAL_INDICATORS, fetch_annual)
        monthly_rows = fetch_all(MONTHLY_INDICATORS, fetch_monthly)
    except WorldBankUnavailable as e:
        api_problem = str(e)
    else:
        api_problem = ""

    # The MotherDuck extension reads MOTHERDUCK_TOKEN from the environment. Never put the
    # token in the connection string: DuckDB echoes it in error messages.
    con = duckdb.connect("md:")
    ensure_bronze(con)

    if api_problem:
        keep_existing_rows(con, api_problem)
        return

    print(f"Loading into {DATABASE}")

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
