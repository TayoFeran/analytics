import os
import time
from datetime import UTC, datetime

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

# Bronze tables this script owns. Created if missing, so a new database (like prod_dwh)
# is set up by code instead of by hand. Types match the original dev_dwh tables.
BRONZE_DDL = {
    "nigeria_econ_metric_annual": """
        country_code    VARCHAR,
        country_name    VARCHAR,
        indicator_code  VARCHAR,
        indicator_name  VARCHAR,
        year            INTEGER,
        value           DOUBLE,
        extracted_at    TIMESTAMP
    """,
    "nigeria_econ_metric_monthly": """
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


def _get(url, params, max_retries=3):
    for attempt in range(1, max_retries + 1):
        resp = requests.get(url, params=params, timeout=30)
        if resp.ok:
            return resp.json()
        if attempt == max_retries:
            resp.raise_for_status()
        time.sleep(1.5 * attempt)


def fetch_annual(indicator_code, start_year=1990, end_year=None):
    end_year = end_year or datetime.now(UTC).year
    url = f"{WB_BASE}/country/{COUNTRY}/indicator/{indicator_code}"
    params = {"format": "json", "date": f"{start_year}:{end_year}", "per_page": 1000}
    payload = _get(url, params)
    rows = payload[1] or []
    extracted_at = datetime.now(UTC)
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


def fetch_monthly(indicator_code, start_year=2010, end_year=None):
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
    extracted_at = datetime.now(UTC)
    parsed = []
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


def ensure_bronze(con):
    con.sql(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    con.sql(f"CREATE SCHEMA IF NOT EXISTS {DATABASE}.bronze")
    for table, columns in BRONZE_DDL.items():
        con.sql(f"CREATE TABLE IF NOT EXISTS {DATABASE}.bronze.{table} ({columns})")


def main():
    if DATABASE not in ALLOWED_DATABASES:
        raise SystemExit(
            f"Error: MOTHERDUCK_DATABASE={DATABASE!r}, expected one of {sorted(ALLOWED_DATABASES)}"
        )
    if not TOKEN:
        raise SystemExit("Error: MOTHERDUCK_TOKEN is not set")

    print(f"Loading into {DATABASE}")
    con = duckdb.connect(f"md:?motherduck_token={TOKEN}")
    ensure_bronze(con)

    annual_rows = []
    for code in ANNUAL_INDICATORS:
        annual_rows.extend(fetch_annual(code))

    monthly_rows = []
    for code in MONTHLY_INDICATORS:
        monthly_rows.extend(fetch_monthly(code))

    print(f"Annual rows fetched: {len(annual_rows)}")
    print(f"Monthly rows fetched: {len(monthly_rows)}")

    # Replace both tables in one transaction: if any insert fails, the old rows stay
    # instead of leaving bronze empty for the next dbt run.
    con.execute("BEGIN TRANSACTION")
    try:
        load_rows(con, annual_rows, monthly_rows)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    print("Done.")
    for table in BRONZE_DDL:
        count = con.sql(f"SELECT COUNT(*) FROM {DATABASE}.bronze.{table}").fetchone()[0]
        print(f"{DATABASE}.bronze.{table}: {count} rows")


def load_rows(con, annual_rows, monthly_rows):
    con.execute(f"DELETE FROM {DATABASE}.bronze.nigeria_econ_metric_annual")
    con.execute(f"DELETE FROM {DATABASE}.bronze.nigeria_econ_metric_monthly")

    if annual_rows:
        con.executemany(
            f"""
            INSERT INTO {DATABASE}.bronze.nigeria_econ_metric_annual
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

    if monthly_rows:
        con.executemany(
            f"""
            INSERT INTO {DATABASE}.bronze.nigeria_econ_metric_monthly
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


if __name__ == "__main__":
    main()
