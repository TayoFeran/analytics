"""Nigeria project: load FAAC monthly allocation workbooks into MotherDuck bronze tables.

Reads every data/nigeria/faac/<year>/<year> <Mon> Disbursement.xlsx and loads the Income
and Deduction sheets as written: one row per state row, plus the file, year and month it
came from. Business rules (state spelling, recomputed totals, net-amount fallback) live in
the dbt silver and gold models, not here.

Usage (from the repo root):
    uv run --group pipelines python pipelines/nigeria/load_faac_allocations.py

    # prod_dwh: only the scheduled daily-pipeline workflow does this
    MOTHERDUCK_DATABASE=prod_dwh \
        uv run --group pipelines python pipelines/nigeria/load_faac_allocations.py
"""

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import openpyxl
from dotenv import load_dotenv

load_dotenv()

PROJECT = "nigeria"
SOURCE = "faac"

TOKEN = os.getenv("MOTHERDUCK_TOKEN")

# Which MotherDuck database to load: dev_dwh for local work, prod_dwh only for the
# scheduled job. Restricted to known names so a typo can't create a stray database.
DATABASE = os.getenv("MOTHERDUCK_DATABASE", "dev_dwh")
ALLOWED_DATABASES = {"dev_dwh", "prod_dwh"}

# The workbooks live in the repo, so adding a month is a commit
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / PROJECT / SOURCE

INCOME_TABLE = f"{PROJECT}_{SOURCE}_income_sheet"
DEDUCTION_TABLE = f"{PROJECT}_{SOURCE}_deduction_sheet"

# Columns are read by position and every header is checked against these layouts. A file
# with any other layout stops the run: a new layout needs a human look, not a guess.
# (The Fabric notebooks matched headers "fuzzily", which mapped the wrong column in the
# files where column 8 of the Deduction sheet is mislabelled; see below.)
Layout = list[tuple[str | None, str]]

INCOME_LAYOUT: Layout = [
    ("Beneficiaries", "beneficiary"),
    ("LGs", "lgs"),
    ("Statutory Allocation", "statutory_allocation"),
    ("Oil Derivation", "oil_derivation"),
    ("Exchange Gain Difference", "exchange_gain_difference"),
    ("Total Ecology Fund", "total_ecology_fund"),
    ("Gross VAT Allocation", "gross_vat_allocation"),
    ("Others Income", "others_income"),
    ("Total Gross Amount", "total_gross_amount"),
]
DEDUCTION_LAYOUT: Layout = [
    ("Beneficiaries", "beneficiary"),
    ("LGs", "lgs"),
    ("External Debt", "external_debt"),
    ("Contractual Obligation (ISPO)", "contractual_obligation_ispo"),
    ("Other Deductions (see Note)", "other_deductions_note"),
    ("Transfer of 50% to NDDC/HYPPADEC", "transfer_nddc_hyppadec"),
    ("Deduction", "deduction_misc"),
    # Every November and December file from 2020 to 2023 labels this column
    # "Others Income". It is the same deduction column (all zeros in those files).
    ("Others Deduction", "other_deduction"),
    # In this sheet "Total Gross Amount" is the TOTAL OF DEDUCTIONS, not a gross amount
    ("Total Gross Amount", "total_deductions"),
    # The net amount after deductions has no header at all: the column after the total
    (None, "net_amount_after_deductions"),
]
# Header variants accepted per sheet, mapped to the label in the layout above
DEDUCTION_ALIASES = {"Others Income": "Others Deduction"}

KEY_COLUMNS = {
    "source_file": "VARCHAR",
    "disbursement_year": "INTEGER",
    "disbursement_month": "INTEGER",
    "sheet_row": "INTEGER",
    "beneficiary": "VARCHAR",
}
BRONZE_DDL = {
    INCOME_TABLE: [*KEY_COLUMNS.items()]
    + [(name, "DOUBLE") for _, name in INCOME_LAYOUT[1:]]
    + [("extracted_at", "TIMESTAMP")],
    DEDUCTION_TABLE: [*KEY_COLUMNS.items()]
    + [(name, "DOUBLE") for _, name in DEDUCTION_LAYOUT[1:]]
    + [("extracted_at", "TIMESTAMP")],
}

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}  # fmt: skip
FILE_NAME = re.compile(r"^(\d{4}) ([A-Za-z]{3})[a-z]* Disbursement\.xlsx$")

# One extracted row, keyed by bronze column name
Row = dict[str, Any]


def utc_now() -> datetime:
    """Current UTC time without a timezone, for bronze TIMESTAMP columns.

    DuckDB converts a timezone-aware value to the machine's local time before storing it
    in a plain TIMESTAMP, so laptop runs would be stored in local time. A naive UTC value
    is stored as-is everywhere.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_header(value: Any, aliases: dict[str, str]) -> str | None:
    """Header text with whitespace collapsed (the source has '  Statutory' and '   (see')."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    return aliases.get(text, text) or None


def to_number(value: Any, where: str) -> float | None:
    """Turn a cell into a number. Blank stays NULL; '1,234' and '-' are handled."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{where}: unexpected boolean {value!r}")
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in ("", "-"):
        return None
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"{where}: not a number: {value!r}") from None


def parse_file_name(path: Path) -> tuple[int, int]:
    """Year and month from '<year> <Mon> Disbursement.xlsx', checked against its folder."""
    match = FILE_NAME.match(path.name)
    if not match or match.group(2).lower() not in MONTHS:
        raise ValueError(f"{path.name}: expected '<year> <Mon> Disbursement.xlsx'")
    year, month = int(match.group(1)), MONTHS[match.group(2).lower()]
    if path.parent.name != str(year):
        raise ValueError(f"{path.name}: is in folder {path.parent.name}, expected {year}")
    return year, month


def read_sheet(
    workbook: Any, sheet: str, layout: Layout, path: Path, aliases: dict[str, str]
) -> list[Row]:
    """Read one sheet by column position, after checking its header row."""
    matches = [name for name in workbook.sheetnames if name.strip().lower() == sheet.lower()]
    if len(matches) != 1:
        raise ValueError(f"{path.name}: expected one '{sheet}' sheet, found {workbook.sheetnames}")
    rows = list(workbook[matches[0]].iter_rows(values_only=True))
    header = [normalize_header(v, aliases) for v in rows[0]] + [None] * len(layout)
    expected = [label for label, _ in layout]
    if header[: len(layout)] != expected:
        raise ValueError(
            f"{path.name} [{sheet}]: unexpected header {header[: len(layout)]}, expected {expected}"
        )

    year, month = parse_file_name(path)
    extracted_at = utc_now()
    parsed: list[Row] = []
    for number, values in enumerate(rows[1:], start=2):
        cells = list(values) + [None] * len(layout)
        if cells[0] is None or not str(cells[0]).strip():
            continue  # blank rows between and after the states
        row: Row = {
            "source_file": path.name,
            "disbursement_year": year,
            "disbursement_month": month,
            "sheet_row": number,
            "beneficiary": str(cells[0]).strip(),
        }
        for position, (_, column) in enumerate(layout[1:], start=1):
            row[column] = to_number(cells[position], f"{path.name} [{sheet}] row {number}")
        row["extracted_at"] = extracted_at
        parsed.append(row)
    if not parsed:
        raise ValueError(f"{path.name} [{sheet}]: no rows")
    return parsed


def read_all() -> tuple[list[Row], list[Row]]:
    """Parse every workbook. Any problem stops the run before MotherDuck is touched."""
    files = sorted(DATA_DIR.glob("*/*.xlsx"))
    files = [f for f in files if not f.name.startswith("~$")]  # Excel lock files
    if not files:
        raise SystemExit(f"Error: no workbooks found in {DATA_DIR}")
    income: list[Row] = []
    deduction: list[Row] = []
    for path in files:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            income.extend(read_sheet(workbook, "Income", INCOME_LAYOUT, path, {}))
            deduction.extend(
                read_sheet(workbook, "Deduction", DEDUCTION_LAYOUT, path, DEDUCTION_ALIASES)
            )
        except ValueError as error:
            raise SystemExit(f"Error: {error}; bronze left unchanged") from None
        finally:
            workbook.close()
    print(f"{len(files)} workbooks: {len(income)} income rows, {len(deduction)} deduction rows")
    return income, deduction


def ensure_bronze(con: duckdb.DuckDBPyConnection) -> None:
    con.sql(f"CREATE DATABASE IF NOT EXISTS {DATABASE}")
    con.sql(f"CREATE SCHEMA IF NOT EXISTS {DATABASE}.bronze")
    for table, columns in BRONZE_DDL.items():
        definition = ", ".join(f"{name} {kind}" for name, kind in columns)
        con.sql(f"CREATE TABLE IF NOT EXISTS {DATABASE}.bronze.{table} ({definition})")


def stage_table(con: duckdb.DuckDBPyConnection, table: str, rows: list[Row]) -> None:
    """Put the rows in a local in-memory table first.

    Inserting thousands of rows one by one into MotherDuck means one network round trip
    per row (minutes). Staging locally and then copying with a single INSERT ... SELECT
    uploads each table in one go (seconds).
    """
    columns = BRONZE_DDL[table]
    definition = ", ".join(f"{name} {kind}" for name, kind in columns)
    con.execute(f"CREATE OR REPLACE TABLE memory.main.{table} ({definition})")
    con.executemany(
        f"INSERT INTO memory.main.{table} VALUES ({', '.join('?' for _ in columns)})",
        [tuple(r[name] for name, _ in columns) for r in rows],
    )


def replace_table(con: duckdb.DuckDBPyConnection, table: str) -> None:
    """Replace one bronze table with its staged rows. Call inside a transaction."""
    columns = ", ".join(name for name, _ in BRONZE_DDL[table])
    con.execute(f"DELETE FROM {DATABASE}.bronze.{table}")
    con.execute(
        f"INSERT INTO {DATABASE}.bronze.{table} ({columns}) "
        f"SELECT {columns} FROM memory.main.{table}"
    )


def main() -> None:
    if DATABASE not in ALLOWED_DATABASES:
        raise SystemExit(
            f"Error: MOTHERDUCK_DATABASE={DATABASE!r}, expected one of {sorted(ALLOWED_DATABASES)}"
        )
    if not TOKEN:
        raise SystemExit("Error: MOTHERDUCK_TOKEN is not set")

    # Parse everything before touching MotherDuck, so a bad file changes nothing
    income, deduction = read_all()

    print(f"Loading into {DATABASE}")
    # Local in-memory database for staging, with MotherDuck attached next to it
    # The MotherDuck extension reads MOTHERDUCK_TOKEN from the environment. Never put the
    # token in the connection string: DuckDB echoes it in error messages.
    con = duckdb.connect(":memory:")
    con.execute("ATTACH 'md:'")
    ensure_bronze(con)
    stage_table(con, INCOME_TABLE, income)
    stage_table(con, DEDUCTION_TABLE, deduction)

    # One transaction for both tables: a failure keeps the previous load intact
    con.execute("BEGIN TRANSACTION")
    try:
        replace_table(con, INCOME_TABLE)
        replace_table(con, DEDUCTION_TABLE)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    for table in BRONZE_DDL:
        result = con.sql(f"SELECT COUNT(*) FROM {DATABASE}.bronze.{table}").fetchone()
        print(f"{DATABASE}.bronze.{table}: {result[0] if result else 0} rows")


if __name__ == "__main__":
    main()
