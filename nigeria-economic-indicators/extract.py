import time
import os
from datetime import datetime, timezone

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

def _get(url, params, max_retries=3):
    for attempt in range(1, max_retries + 1):
        resp = requests.get(url, params=params, timeout=30)
        if resp.ok:
            return resp.json()
        if attempt == max_retries:
            resp.raise_for_status()
        time.sleep(1.5 * attempt)

def fetch_annual(indicator_code, start_year=1990, end_year=None):
    end_year = end_year or datetime.now(timezone.utc).year
    url = f"{WB_BASE}/country/{COUNTRY}/indicator/{indicator_code}"
    params = {"format": "json", "date": f"{start_year}:{end_year}", "per_page": 1000}
    payload = _get(url, params)
    rows = payload[1] or []
    extracted_at = datetime.now(timezone.utc)
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
    end_year = end_year or datetime.now(timezone.utc).year
    url = f"{WB_BASE}/country/{COUNTRY}/indicator/{indicator_code}"
    params = {
        "format": "json",
        "source": 15,
        "date": f"{start_year}M01:{end_year}M12",
        "per_page": 1000,
    }
    payload = _get(url, params)
    rows = payload[1] or []
    extracted_at = datetime.now(timezone.utc)
    parsed = []
    for r in rows:
        if r.get("value") is None:
            continue
        year_str, month_str = r["date"].split("M")
        parsed.append({
            "country_code": COUNTRY,
            "country_name": COUNTRY_NAME,
            "indicator_code": indicator_code,
            "indicator_name": MONTHLY_INDICATORS[indicator_code],
            "year": int(year_str),
            "month": int(month_str),
            "value": float(r["value"]),
            "extracted_at": extracted_at,
        })
    return parsed

def main():
    con = duckdb.connect(f"md:?motherduck_token={TOKEN}")

    annual_rows = []
    for code in ANNUAL_INDICATORS:
        annual_rows.extend(fetch_annual(code))

    monthly_rows = []
    for code in MONTHLY_INDICATORS:
        monthly_rows.extend(fetch_monthly(code))

    print(f"Annual rows fetched: {len(annual_rows)}")
    print(f"Monthly rows fetched: {len(monthly_rows)}")

    # Truncate-and-reload: bronze is a full snapshot of the source, not an
    # append log, so every run clears out the old data before loading fresh.
    con.sql("DELETE FROM analytics.nigeria.econ_metric_annual")
    con.sql("DELETE FROM analytics.nigeria.econ_metric_monthly")

    if annual_rows:
        con.executemany(
            """
            INSERT INTO analytics.nigeria.econ_metric_annual
            (country_code, country_name, indicator_code, indicator_name, year, value, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [(r["country_code"], r["country_name"], r["indicator_code"], r["indicator_name"], r["year"], r["value"], r["extracted_at"]) for r in annual_rows],
        )

    if monthly_rows:
        con.executemany(
            """
            INSERT INTO analytics.nigeria.econ_metric_monthly
            (country_code, country_name, indicator_code, indicator_name, year, month, value, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(r["country_code"], r["country_name"], r["indicator_code"], r["indicator_name"], r["year"], r["month"], r["value"], r["extracted_at"]) for r in monthly_rows],
        )

    print("Done.")
    print("Annual count:", con.sql("SELECT COUNT(*) FROM analytics.nigeria.econ_metric_annual").fetchall())
    print("Monthly count:", con.sql("SELECT COUNT(*) FROM analytics.nigeria.econ_metric_monthly").fetchall())

if __name__ == "__main__":
    main()