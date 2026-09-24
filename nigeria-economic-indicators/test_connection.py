import duckdb
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("MOTHERDUCK_TOKEN")

con = duckdb.connect(f"md:?motherduck_token={TOKEN}")
print(con.sql("SHOW DATABASES").fetchall())