# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "7a83841c-158d-46f4-a100-6fff975adc24",
# META       "default_lakehouse_name": "Data_lake",
# META       "default_lakehouse_workspace_id": "d71c970d-8937-4534-9d94-2c86745bb502",
# META       "known_lakehouses": [
# META         {
# META           "id": "7a83841c-158d-46f4-a100-6fff975adc24"
# META         }
# META       ]
# META     },
# META     "warehouse": {
# META       "default_warehouse": "5b1d0458-7304-a6d8-4ad4-a6ca625583c4",
# META       "known_warehouses": [
# META         {
# META           "id": "5b1d0458-7304-a6d8-4ad4-a6ca625583c4",
# META           "type": "Datawarehouse"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# =============================================================================
# FAAC Monthly Income Pipeline
# =============================================================================
# Reads all refined FAAC Excel files (2020-2026) from the Lakehouse,
# merges them into one clean table, and writes to the Fabric Warehouse.
#
# File location pattern:
#   Data_lake/Files/FAAC/Refined/{year}/{filename}.xlsx
#
# Target table:  DWH.dbo.faac_monthly_income
# Sheet used:    "income" (the inflow sheet)
#
# Adapted from an earlier standalone prototype script for the
# analytics_engineering Fabric workspace. Logic unchanged; only the
# lakehouse/warehouse names and source path were updated.
# =============================================================================

import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, LongType, DoubleType
)

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

LAKEHOUSE_NAME  = "Data_lake"
WAREHOUSE_NAME  = "DWH"
TARGET_TABLE    = "dbo.faac_monthly_income"
SHEET_NAME      = "Income"   # Matches the actual tab name in your files
YEARS_TO_LOAD   = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Base path to the FAAC folder inside your Lakehouse Files
# This is the local mount path — always available inside a Fabric notebook
BASE_PATH = "/lakehouse/default/Files/FAAC/Refined"

# ─── COLUMN MAPPING ───────────────────────────────────────────────────────────
# Maps exactly what NBS calls each column → clean snake_case name for the table
# Adjust the left-hand side if any column name in your files is slightly different

COLUMN_MAP = {
    "Beneficiaries":          "state",
    "LGs":                    "lg_count",
    "Statutory Allocation":   "statutory_allocation",
    "Oil Derivation":         "oil_derivation",
    "Exchange Gain Difference": "exchange_gain_difference",
    "Total Ecology Fund":     "total_ecology_fund",
    "Gross VAT Allocation":   "gross_vat_allocation",
    "Others Income":          "others_income",
    "Total Gross Amount":     "total_gross_amount",
}

# ─── ADMINISTRATION LOOKUP ────────────────────────────────────────────────────

def get_president(year: int, month: int) -> str:
    if year < 2015 or (year == 2015 and month < 5):
        return "Jonathan"
    elif year < 2023 or (year == 2023 and month < 5):
        return "Buhari"
    else:
        return "Tinubu"

MONTH_NAME_MAP = {
    1: "January", 2: "February",  3: "March",    4: "April",
    5: "May",     6: "June",      7: "July",     8: "August",
    9: "September",10: "October", 11: "November",12: "December"
}

# ─── HELPER: EXTRACT MONTH FROM FILENAME ──────────────────────────────────────
# Designed for your exact naming convention: "2020 Apr Disbursement.xlsx"
# Also handles: "2020 April Disbursement.xlsx", "2020 January Disbursement.xlsx"

def extract_month_from_filename(filename: str) -> int:
    """
    Returns the month number (1–12) from the filename.
    Returns 0 if no month can be found — that file will be skipped with a warning.

    Tested against: "2020 Apr Disbursement.xlsx"
                    "2021 December Disbursement.xlsx"
                    "2023 Jan Disbursement.xlsx"
    """
    # Normalise: remove underscores/hyphens, uppercase everything
    name = filename.replace("_", " ").replace("-", " ").upper()

    # Full and abbreviated month names → month number
    month_names = {
        "JANUARY": 1,   "JAN": 1,
        "FEBRUARY": 2,  "FEB": 2,
        "MARCH": 3,     "MAR": 3,
        "APRIL": 4,     "APR": 4,
        "MAY": 5,
        "JUNE": 6,      "JUN": 6,
        "JULY": 7,      "JUL": 7,
        "AUGUST": 8,    "AUG": 8,
        "SEPTEMBER": 9, "SEP": 9,  "SEPT": 9,
        "OCTOBER": 10,  "OCT": 10,
        "NOVEMBER": 11, "NOV": 11,
        "DECEMBER": 12, "DEC": 12,
    }

    # Split on spaces and check each word — catches "Apr", "April", "APRIL" etc.
    for word in name.split():
        # Strip any trailing punctuation that might attach to the word
        word = word.strip(".,;:()")
        if word in month_names:
            return month_names[word]

    return 0  # Could not determine month


# ─── HELPER: READ ONE EXCEL FILE ──────────────────────────────────────────────

def read_faac_excel(filepath: str, year: int, month: int):
    """
    Reads the Income sheet from one FAAC Excel file using pandas,
    cleans it up, and returns a Spark DataFrame.

    Your file structure (confirmed from screenshot):
      - Row 1  = column headers (Beneficiaries, LGs, Statutory Allocation, ...)
      - Row 2+ = one row per state (37 states + FCT)
      - Sheet tab name = "Income"
    """
    import pandas as pd

    try:
        # ── Try opening the sheet — handle both "Income" and "income" casing ──
        xl = pd.ExcelFile(filepath, engine="openpyxl")
        sheet_names_in_file = xl.sheet_names

        # Find the income sheet regardless of capitalisation
        income_sheet = None
        for s in sheet_names_in_file:
            if s.strip().lower() == "income":
                income_sheet = s
                break

        if income_sheet is None:
            print(f"\n   ❌ No 'Income' sheet found in {filepath}")
            print(f"      Sheets available: {sheet_names_in_file}")
            return None

        # ── Read the sheet — row 1 is the header (header=0) ──────────────
        pdf = pd.read_excel(
            filepath,
            sheet_name=income_sheet,
            header=0,        # Row 1 in Excel = index 0 in pandas = column names
            engine="openpyxl"
        )

        # ── 1. Drop completely empty rows and columns ──────────────────────
        pdf = pdf.dropna(how="all")
        pdf = pdf.dropna(axis=1, how="all")

        # ── 2. Strip whitespace from column names ──────────────────────────
        pdf.columns = [str(c).strip() for c in pdf.columns]

        # ── 3. Keep only the columns we care about (from COLUMN_MAP) ───────
        # Handle case where some files may have slight name differences
        cols_present = list(pdf.columns)
        rename_dict = {}
        for original_name, clean_name in COLUMN_MAP.items():
            # Exact match first
            if original_name in cols_present:
                rename_dict[original_name] = clean_name
            else:
                # Fuzzy match: check if any column contains the key words
                for col in cols_present:
                    if original_name.lower() in col.lower() or col.lower() in original_name.lower():
                        rename_dict[col] = clean_name
                        break

        pdf = pdf.rename(columns=rename_dict)

        # ── 4. Keep only mapped columns that actually exist ────────────────
        target_cols = list(COLUMN_MAP.values())
        existing_cols = [c for c in target_cols if c in pdf.columns]
        pdf = pdf[existing_cols]

        # ── 5. Filter to actual state rows ────────────────────────────────
        # Remove subtotal/total rows and blank state names
        valid_states = [
            "ABIA", "ADAMAWA", "AKWA IBOM", "ANAMBRA", "BAUCHI", "BAYELSA",
            "BENUE", "BORNO", "CROSS RIVER", "DELTA", "EBONYI", "EDO",
            "EKITI", "ENUGU", "FCT", "GOMBE", "IMO", "JIGAWA",
            "KADUNA", "KANO", "KATSINA", "KEBBI", "KOGI", "KWARA",
            "LAGOS", "NASARAWA", "NIGER", "OGUN", "ONDO", "OSUN",
            "OYO", "PLATEAU", "RIVERS", "SOKOTO", "TARABA", "YOBE", "ZAMFARA"
        ]

        if "state" in pdf.columns:
            pdf["state"] = pdf["state"].astype(str).str.strip().str.upper()
            pdf = pdf[pdf["state"].isin(valid_states)]

        if pdf.empty:
            print(f"   ⚠️  No valid state rows found in: {filepath}")
            return None

        # ── 6. Clean numeric columns (remove commas, dashes, convert) ─────
        numeric_cols = [
            "lg_count", "statutory_allocation", "oil_derivation",
            "exchange_gain_difference", "total_ecology_fund",
            "gross_vat_allocation", "others_income", "total_gross_amount"
        ]

        for col in numeric_cols:
            if col in pdf.columns:
                pdf[col] = (
                    pdf[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("-", "0", regex=False)
                    .str.strip()
                    .replace("", "0")
                    .replace("nan", "0")
                )
                pdf[col] = pd.to_numeric(pdf[col], errors="coerce").fillna(0)

        # ── 7. Add date and administration columns ─────────────────────────
        pdf["year"]            = year
        pdf["month_number"]    = month
        pdf["month_name"]      = MONTH_NAME_MAP.get(month, "Unknown")
        pdf["disbursement_date"] = f"{year}-{month:02d}-01"
        pdf["president"]       = get_president(year, month)
        pdf["source_file"]     = os.path.basename(filepath)

        # ── 8. Title-case state names for clean display ────────────────────
        title_map = {
            "ABIA": "Abia", "ADAMAWA": "Adamawa", "AKWA IBOM": "Akwa Ibom",
            "ANAMBRA": "Anambra", "BAUCHI": "Bauchi", "BAYELSA": "Bayelsa",
            "BENUE": "Benue", "BORNO": "Borno", "CROSS RIVER": "Cross River",
            "DELTA": "Delta", "EBONYI": "Ebonyi", "EDO": "Edo",
            "EKITI": "Ekiti", "ENUGU": "Enugu", "FCT": "FCT",
            "GOMBE": "Gombe", "IMO": "Imo", "JIGAWA": "Jigawa",
            "KADUNA": "Kaduna", "KANO": "Kano", "KATSINA": "Katsina",
            "KEBBI": "Kebbi", "KOGI": "Kogi", "KWARA": "Kwara",
            "LAGOS": "Lagos", "NASARAWA": "Nasarawa", "NIGER": "Niger",
            "OGUN": "Ogun", "ONDO": "Ondo", "OSUN": "Osun",
            "OYO": "Oyo", "PLATEAU": "Plateau", "RIVERS": "Rivers",
            "SOKOTO": "Sokoto", "TARABA": "Taraba", "YOBE": "Yobe",
            "ZAMFARA": "Zamfara"
        }
        pdf["state"] = pdf["state"].map(title_map).fillna(pdf["state"].str.title())

        # ── 9. Convert to Spark DataFrame ─────────────────────────────────
        spark = SparkSession.builder.getOrCreate()
        sdf = spark.createDataFrame(pdf)

        # Cast types cleanly
        long_cols = [
            "statutory_allocation", "oil_derivation", "exchange_gain_difference",
            "total_ecology_fund", "gross_vat_allocation", "others_income",
            "total_gross_amount"
        ]
        for c in long_cols:
            if c in sdf.columns:
                sdf = sdf.withColumn(c, F.col(c).cast(LongType()))

        if "lg_count" in sdf.columns:
            sdf = sdf.withColumn("lg_count", F.col("lg_count").cast(IntegerType()))

        sdf = sdf.withColumn("year",         F.col("year").cast(IntegerType()))
        sdf = sdf.withColumn("month_number", F.col("month_number").cast(IntegerType()))
        sdf = sdf.withColumn("disbursement_date", F.to_date("disbursement_date", "yyyy-MM-dd"))

        return sdf

    except Exception as e:
        print(f"   ❌ Failed to read {filepath}: {e}")
        return None


# ─── MAIN PIPELINE ────────────────────────────────────────────────────────────

def run_pipeline():
    spark = SparkSession.builder.getOrCreate()
    spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")

    print("=" * 65)
    print("  FAAC Monthly Income Pipeline")
    print(f"  Source:  {BASE_PATH}")
    print(f"  Target:  {WAREHOUSE_NAME}.{TARGET_TABLE}")
    print("=" * 65)

    # ── PATH VERIFICATION — runs before anything else ──────────────────────
    print("\n🔍 Verifying folder structure...\n")
    if not os.path.isdir(BASE_PATH):
        print(f"❌ BASE_PATH does not exist: {BASE_PATH}")
        print(f"   Open your Lakehouse in Fabric, click into Files, and copy")
        print(f"   the exact folder path. Update BASE_PATH at the top of this script.")
        return

    for year in YEARS_TO_LOAD:
        year_path = f"{BASE_PATH}/{year}"
        if os.path.isdir(year_path):
            xlsx_count = sum(
                1 for f in os.listdir(year_path)
                if f.endswith(".xlsx") and not f.startswith("~$")
            )
            print(f"   ✅ {year}  →  found ({xlsx_count} Excel files)")
        else:
            print(f"   ❌ {year}  →  folder missing: {year_path}")
    print()

    all_dataframes = []
    files_processed = 0
    files_failed    = 0

    # ── Loop through each year folder ─────────────────────────────────────
    for year in YEARS_TO_LOAD:
        year_path = f"{BASE_PATH}/{year}"

        print(f"\n📁 Processing year: {year}  →  {year_path}")

        # ── List Excel files using os.walk on the local mount path ───────
        # NOTE: wholeTextFiles / Spark file listing does NOT work on OneLake.
        # The Lakehouse is always mounted locally at /lakehouse/default/
        # so os.walk is the correct and reliable way to list files here.
        try:
            excel_files = []
            if os.path.isdir(year_path):
                for root, dirs, files in os.walk(year_path):
                    for f in files:
                        if f.endswith(".xlsx") and not f.startswith("~$"):
                            excel_files.append(os.path.join(root, f))
            else:
                print(f"   ⚠️  Folder does not exist: {year_path}")
                print(f"       Double-check your folder name in the Lakehouse Files browser.")
                continue

        except Exception as e:
            print(f"   ⚠️  Could not read folder for {year}: {e}")
            continue

        if not excel_files:
            print(f"   ⚠️  No .xlsx files found in {year_path}")
            continue

        print(f"   Found {len(excel_files)} Excel file(s)")

        # ── Process each file ──────────────────────────────────────────────
        for file_path in sorted(excel_files):
            filename = os.path.basename(file_path)
            month = extract_month_from_filename(filename)

            if month == 0:
                print(f"   ⚠️  Could not determine month from filename: {filename}")
                print(f"       Rename the file to include the month name, e.g. 'FAAC_January_{year}.xlsx'")
                files_failed += 1
                continue

            print(f"   📄 {filename}  →  {MONTH_NAME_MAP[month]} {year}", end=" ... ")

            # file_path is already a full local path from os.walk — use it directly
            local_path = file_path

            sdf = read_faac_excel(local_path, year, month)

            if sdf is not None:
                row_count = sdf.count()
                print(f"✅ {row_count} rows")
                all_dataframes.append(sdf)
                files_processed += 1
            else:
                print("❌ failed")
                files_failed += 1

    # ── Merge all DataFrames ───────────────────────────────────────────────
    if not all_dataframes:
        print("\n❌ No data was loaded. Pipeline stopped.")
        print("   Check the folder paths and file names above.")
        return

    print(f"\n{'─'*65}")
    print(f"🔗 Merging {len(all_dataframes)} monthly datasets...")

    merged = all_dataframes[0]
    for df in all_dataframes[1:]:
        merged = merged.unionByName(df, allowMissingColumns=True)

    # Fill any nulls created by allowMissingColumns
    numeric_fill_cols = [
        "statutory_allocation", "oil_derivation", "exchange_gain_difference",
        "total_ecology_fund", "gross_vat_allocation", "others_income",
        "total_gross_amount", "lg_count"
    ]
    for c in numeric_fill_cols:
        if c in merged.columns:
            merged = merged.withColumn(c, F.coalesce(F.col(c), F.lit(0).cast(LongType())))

    # Sort for a clean table
    merged = merged.orderBy("disbursement_date", "state")

    total_rows = merged.count()
    print(f"   Total rows merged: {total_rows:,}")
    print(f"   Date range: {merged.agg(F.min('disbursement_date')).collect()[0][0]} "
          f"to {merged.agg(F.max('disbursement_date')).collect()[0][0]}")
    print(f"   States: {merged.select('state').distinct().count()}")

    # ── Write to Warehouse ─────────────────────────────────────────────────
    print(f"\n💾 Writing to warehouse: {WAREHOUSE_NAME}.{TARGET_TABLE}")
    print(f"   Mode: OVERWRITE (replaces existing table if present)\n")

    try:
        (
            merged.write
            .format("fabric.api.spark.sql")          # Fabric Warehouse writer
            .option("warehouse", WAREHOUSE_NAME)
            .option("schema", "dbo")
            .option("tableName", "faac_monthly_income")
            .mode("overwrite")                        # Change to "append" to add rows instead
            .save()
        )
        print(f"✅ Successfully written to {WAREHOUSE_NAME}.dbo.faac_monthly_income")

    except Exception as e:
        # Fallback: try writing as a Lakehouse Delta table instead
        print(f"   ℹ️  Direct warehouse write failed ({e})")
        print(f"   🔄 Falling back: saving as Delta table in Lakehouse...")

        (
            merged.write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable("faac_monthly_income")      # Saves to default Lakehouse
        )
        print(f"✅ Saved as Delta table: faac_monthly_income")
        print(f"   You can now reference this in your Warehouse via the Lakehouse shortcut.")

    # ── Final Summary ──────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"  ✅ PIPELINE COMPLETE")
    print(f"{'='*65}")
    print(f"  Files processed successfully : {files_processed}")
    print(f"  Files failed / skipped       : {files_failed}")
    print(f"  Total rows in final table    : {total_rows:,}")
    print(f"  Table                        : {WAREHOUSE_NAME}.dbo.faac_monthly_income")
    print()
    print(f"  COLUMNS IN TABLE:")
    for field in merged.schema.fields:
        print(f"    • {field.name:35s} {str(field.dataType)}")
    print(f"{'='*65}")


# ─── RUN ──────────────────────────────────────────────────────────────────────
run_pipeline()

# METADATA ********************
# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
