import os

import duckdb
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("MOTHERDUCK_TOKEN")

con = duckdb.connect(f"md:?motherduck_token={TOKEN}")

# Remove the old pre-restructure setup
con.sql("DROP SCHEMA IF EXISTS analytics.nigeria CASCADE")

# New warehouse: dev_dwh, schemas by medallion layer instead of by country
con.sql("CREATE DATABASE IF NOT EXISTS dev_dwh")
con.sql("CREATE SCHEMA IF NOT EXISTS dev_dwh.bronze")
con.sql("CREATE SCHEMA IF NOT EXISTS dev_dwh.silver")
con.sql("CREATE SCHEMA IF NOT EXISTS dev_dwh.analytics")

# Bronze only here — silver and analytics tables will be created by dbt models later
con.sql("""
    CREATE TABLE IF NOT EXISTS dev_dwh.bronze.nigeria_econ_metric_monthly (
        country_code    VARCHAR,
        country_name    VARCHAR,
        indicator_code  VARCHAR,
        indicator_name  VARCHAR,
        year            INTEGER,
        month           INTEGER,
        value           DOUBLE,
        extracted_at    TIMESTAMP
    )
""")

con.sql("""
    CREATE TABLE IF NOT EXISTS dev_dwh.bronze.nigeria_econ_metric_annual (
        country_code    VARCHAR,
        country_name    VARCHAR,
        indicator_code  VARCHAR,
        indicator_name  VARCHAR,
        year            INTEGER,
        value           DOUBLE,
        extracted_at    TIMESTAMP
    )
""")

print(con.sql("DESCRIBE dev_dwh.bronze.nigeria_econ_metric_monthly").fetchall())
print(con.sql("DESCRIBE dev_dwh.bronze.nigeria_econ_metric_annual").fetchall())