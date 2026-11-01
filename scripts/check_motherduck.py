"""Check that the MotherDuck token in .env works, and list the databases it can see.

Usage (from the repo root):
    uv run --group pipelines python scripts/check_motherduck.py
"""

import os

import duckdb
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    token = os.getenv("MOTHERDUCK_TOKEN")
    if not token:
        raise SystemExit("Error: MOTHERDUCK_TOKEN is not set (copy .env.example to .env)")

    con = duckdb.connect(f"md:?motherduck_token={token}")
    databases = [row[0] for row in con.sql("SHOW DATABASES").fetchall()]
    print(f"Connected. Databases: {', '.join(databases)}")


if __name__ == "__main__":
    main()
