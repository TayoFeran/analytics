import duckdb
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("MOTHERDUCK_TOKEN")

con = duckdb.connect(f"md:?motherduck_token={TOKEN}")

con.sql("CREATE DATABASE IF NOT EXISTS analytics")
con.sql("CREATE SCHEMA IF NOT EXISTS analytics.nigeria")

# Replacing the earlier single combined table with two, split by grain
con.sql("DROP TABLE IF EXISTS analytics.nigeria.econ_metric")

con.sql("""
    CREATE TABLE IF NOT EXISTS analytics.nigeria.econ_metric_monthly (
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
    CREATE TABLE IF NOT EXISTS analytics.nigeria.econ_metric_annual (
        country_code    VARCHAR,
        country_name    VARCHAR,
        indicator_code  VARCHAR,
        indicator_name  VARCHAR,
        year            INTEGER,
        value           DOUBLE,
        extracted_at    TIMESTAMP
    )
""")

print(con.sql("DESCRIBE analytics.nigeria.econ_metric_monthly").fetchall())
print(con.sql("DESCRIBE analytics.nigeria.econ_metric_annual").fetchall())