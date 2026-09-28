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
# FAAC Monthly Deduction Pipeline
# =============================================================================
# Reads all refined FAAC Excel files (2020-2026) from the Lakehouse,
# merges them into one clean table, and writes to the Fabric Warehouse.
#
# File location pattern:
#   Data_lake/Files/FAAC/Refined/{year}/{filename}.xlsx
#
# Target table:  DWH.dbo.faac_monthly_deduction
# Sheet used:    "Deduction"
#
# This pipeline was written fresh from the actual "Deduction" sheet found in
# the source workbooks — the old prototype's faac_deduction_pipeline
# (a Synapse notebook in the retired workspace) could not be inspected
# directly (notebook code isn't exposed via OneLake Files/Tables, and that
# workspace isn't Git-connected), so its logic wasn't available to port.
#
# Header quirks confirmed against real files (2020-2026 Jan spot-checked):
#   - The "Total Gross Amount" column is actually TOTAL DEDUCTIONS (sum of
#     the deduction line items) — an earlier version of this script assumed
#     it was the net amount, which was wrong; confirmed by summing the
#     component columns and finding an exact match wherever the source
#     value is populated (2021-2024 Jan checked).
#   - The TRUE net-after-deductions value lives in an UNNAMED trailing
#     column immediately after "Total Gross Amount" (blank header in the
#     source file itself — pandas reads it as "Unnamed: N"). The earlier
#     version of this script never captured this column at all.
#   - Both "Total Gross Amount" (total deductions) and the unnamed net
#     column are blank in some files (confirmed: 2020, 2025, 2026 Jan) —
#     a cached-formula-not-recalculated issue in the source, same as the
#     Income sheet's "Total Gross Amount". total_deductions is recomputed
#     from components to work around this (see step 6b below); net_amount
#     is recovered by falling back to (income total - total_deductions)
#     using the same file's Income sheet when the source net value itself
#     is missing.
#   - The Deduction sheet spells the state "NASSARAWA" (double-S), while
#     the Income sheet spells it "NASARAWA" (single-S) — both are
#     normalised to canonical "Nasarawa" below.
#   - FCT does not appear in the Deduction sheet's state list in the files
#     checked — treated as legitimately absent, not an error.
# =============================================================================

import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, LongType

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

LAKEHOUSE_NAME  = "Data_lake"
WAREHOUSE_NAME  = "DWH"
TARGET_TABLE    = "dbo.faac_monthly_deduction"
SHEET_NAME      = "Deduction"
YEARS_TO_LOAD   = [2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Base path to the FAAC folder inside your Lakehouse Files
# This is the local mount path — always available inside a Fabric notebook
BASE_PATH = "/lakehouse/default/Files/FAAC/Refined"

# ─── COLUMN MAPPING ───────────────────────────────────────────────────────────
# Keys are the exact header strings found in the source files (confirmed via
# openpyxl inspection of 2020 Jan and 2024 Jan Disbursement.xlsx), including
# the source's own irregular internal spacing — this keeps the pipeline on
# the fast, exact-match path rather than relying on fuzzy substring matching.

COLUMN_MAP = {
    "Beneficiaries":                       "state",
    "LGs":                                 "lg_count",
    "External Debt":                       "external_debt",
    "Contractual Obligation (ISPO)":       "contractual_obligation_ispo",
    "Other Deductions   (see Note)":       "other_deductions_note",
    "Transfer of 50% to NDDC/HYPPADEC":    "transfer_nddc_hyppadec",
    "Deduction":                           "deduction_misc",       # unlabelled generic deduction line in source
    "Others Deduction":                    "other_deduction",
    "Total Gross Amount":                  "total_deductions",     # this is TOTAL DEDUCTIONS, not net — see header note above
}

# The real net-after-deductions value has no header in the source file at
# all (blank cell) — it's positioned immediately after "Total Gross Amount".
# Captured by position, not name, since pandas assigns a generated
# "Unnamed: N" name that depends on column count.
NET_AMOUNT_COLUMN_NAME = "net_amount_after_deductions"

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
# Same convention as the income pipeline: "2020 Apr Disbursement.xlsx"

def extract_month_from_filename(filename: str) -> int:
    name = filename.replace("_", " ").replace("-", " ").upper()

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

    for word in name.split():
        word = word.strip(".,;:()")
        if word in month_names:
            return month_names[word]

    return 0


# ─── HELPER: READ ONE EXCEL FILE ──────────────────────────────────────────────

def read_faac_deduction_excel(filepath: str, year: int, month: int):
    """
    Reads the Deduction sheet from one FAAC Excel file using pandas,
    cleans it up, and returns a Spark DataFrame.
    """
    import pandas as pd

    try:
        xl = pd.ExcelFile(filepath, engine="openpyxl")
        sheet_names_in_file = xl.sheet_names

        deduction_sheet = None
        for s in sheet_names_in_file:
            if s.strip().lower() == "deduction":
                deduction_sheet = s
                break

        if deduction_sheet is None:
            print(f"\n   ❌ No 'Deduction' sheet found in {filepath}")
            print(f"      Sheets available: {sheet_names_in_file}")
            return None

        pdf = pd.read_excel(
            filepath,
            sheet_name=deduction_sheet,
            header=0,
            engine="openpyxl"
        )

        # ── 1. Drop completely empty rows and columns ──────────────────────
        pdf = pdf.dropna(how="all")
        pdf = pdf.dropna(axis=1, how="all")

        # ── 2. Strip whitespace from column names (leading/trailing only —
        #        exact match keys above already account for internal spacing) ──
        pdf.columns = [str(c).strip() for c in pdf.columns]

        # ── 3. Keep only the columns we care about (from COLUMN_MAP) ───────
        cols_present = list(pdf.columns)
        rename_dict = {}
        for original_name, clean_name in COLUMN_MAP.items():
            if original_name in cols_present:
                rename_dict[original_name] = clean_name
            else:
                for col in cols_present:
                    if original_name.lower() in col.lower() or col.lower() in original_name.lower():
                        rename_dict[col] = clean_name
                        break

        # ── 3b. Capture the unnamed net-amount column by position ──────────
        # It has no header in the source (pandas names it "Unnamed: N"), so
        # it can't be matched by name — grab whatever immediately follows
        # "Total Gross Amount" if it looks unnamed.
        if "Total Gross Amount" in cols_present:
            tga_idx = cols_present.index("Total Gross Amount")
            if tga_idx + 1 < len(cols_present):
                next_col = cols_present[tga_idx + 1]
                if str(next_col).startswith("Unnamed"):
                    rename_dict[next_col] = NET_AMOUNT_COLUMN_NAME

        pdf = pdf.rename(columns=rename_dict)

        target_cols = list(COLUMN_MAP.values()) + [NET_AMOUNT_COLUMN_NAME]
        existing_cols = [c for c in target_cols if c in pdf.columns]
        pdf = pdf[existing_cols]

        # ── 4. Filter to actual state rows ────────────────────────────────
        # NOTE: includes both spellings seen in source files — "NASSARAWA"
        # (Deduction sheet) and "NASARAWA" (Income sheet) — both normalised
        # to "Nasarawa" below. FCT is intentionally not required here; it's
        # legitimately absent from the Deduction sheet in files checked.
        valid_states = [
            "ABIA", "ADAMAWA", "AKWA IBOM", "ANAMBRA", "BAUCHI", "BAYELSA",
            "BENUE", "BORNO", "CROSS RIVER", "DELTA", "EBONYI", "EDO",
            "EKITI", "ENUGU", "FCT", "GOMBE", "IMO", "JIGAWA",
            "KADUNA", "KANO", "KATSINA", "KEBBI", "KOGI", "KWARA",
            "LAGOS", "NASARAWA", "NASSARAWA", "NIGER", "OGUN", "ONDO", "OSUN",
            "OYO", "PLATEAU", "RIVERS", "SOKOTO", "TARABA", "YOBE", "ZAMFARA"
        ]

        if "state" in pdf.columns:
            pdf["state"] = pdf["state"].astype(str).str.strip().str.upper()
            pdf = pdf[pdf["state"].isin(valid_states)]
            pdf["state"] = pdf["state"].replace({"NASSARAWA": "NASARAWA"})

        if pdf.empty:
            print(f"   ⚠️  No valid state rows found in: {filepath}")
            return None

        # ── 5. Clean numeric columns (remove commas, dashes, convert) ─────
        numeric_cols = [
            "lg_count", "external_debt", "contractual_obligation_ispo",
            "other_deductions_note", "transfer_nddc_hyppadec",
            "deduction_misc", "other_deduction", "total_deductions",
            "net_amount_after_deductions"
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

        # ── 5b. Recompute total_deductions from its components ─────────────
        # Same reasoning as the income pipeline's total_gross_amount fix:
        # the source cell is a cached formula that's sometimes blank
        # (confirmed: 2020, 2025, 2026 Jan), and sum(components) matches the
        # source value exactly wherever it IS present, so compute it
        # directly rather than trust the source cell.
        deduction_component_cols = [
            "external_debt", "contractual_obligation_ispo", "other_deductions_note",
            "transfer_nddc_hyppadec", "deduction_misc", "other_deduction"
        ]
        present_components = [c for c in deduction_component_cols if c in pdf.columns]
        pdf["total_deductions"] = sum(pdf[c] for c in present_components)

        # ── 5c. Fall back to (income total - total_deductions) for any row
        #        where net_amount_after_deductions is still missing/zero ───
        # The source's own net-amount column is blank in the same files
        # where totals are blank. Since Income and Deduction are two sheets
        # in the SAME workbook, recover it here rather than leave it wrong.
        if "net_amount_after_deductions" not in pdf.columns:
            pdf["net_amount_after_deductions"] = 0.0

        missing_net = pdf["net_amount_after_deductions"] == 0
        if missing_net.any():
            try:
                income_pdf = pd.read_excel(filepath, sheet_name="Income", header=0, engine="openpyxl")
                income_pdf.columns = [str(c).strip() for c in income_pdf.columns]
                income_pdf = income_pdf.rename(columns={"Beneficiaries": "state"})
                income_component_cols = [
                    " Statutory Allocation", "Oil Derivation", "Exchange Gain Difference",
                    "Total Ecology Fund", "Gross VAT Allocation", "Others Income"
                ]
                present_income_cols = [c for c in income_component_cols if c in income_pdf.columns]
                for c in present_income_cols:
                    income_pdf[c] = pd.to_numeric(
                        income_pdf[c].astype(str).str.replace(",", "", regex=False).str.replace("-", "0", regex=False),
                        errors="coerce"
                    ).fillna(0)
                income_pdf["income_total"] = sum(income_pdf[c] for c in present_income_cols)
                income_pdf["state"] = income_pdf["state"].astype(str).str.strip().str.upper()
                income_totals = income_pdf.set_index("state")["income_total"]

                pdf.loc[missing_net, "net_amount_after_deductions"] = pdf.loc[missing_net].apply(
                    lambda row: income_totals.get(row["state"], 0) - row["total_deductions"], axis=1
                )
            except Exception as e:
                print(f"   ⚠️  Could not recover net_amount_after_deductions from Income sheet: {e}")

        # ── 6. Add date and administration columns ─────────────────────────
        pdf["year"]            = year
        pdf["month_number"]    = month
        pdf["month_name"]      = MONTH_NAME_MAP.get(month, "Unknown")
        pdf["disbursement_date"] = f"{year}-{month:02d}-01"
        pdf["president"]       = get_president(year, month)
        pdf["source_file"]     = os.path.basename(filepath)

        # ── 7. Title-case state names for clean display ────────────────────
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

        # ── 8. Convert to Spark DataFrame ─────────────────────────────────
        spark = SparkSession.builder.getOrCreate()
        sdf = spark.createDataFrame(pdf)

        long_cols = [
            "external_debt", "contractual_obligation_ispo",
            "other_deductions_note", "transfer_nddc_hyppadec",
            "deduction_misc", "other_deduction", "total_deductions",
            "net_amount_after_deductions"
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
    print("  FAAC Monthly Deduction Pipeline")
    print(f"  Source:  {BASE_PATH}")
    print(f"  Target:  {WAREHOUSE_NAME}.{TARGET_TABLE}")
    print("=" * 65)

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

    for year in YEARS_TO_LOAD:
        year_path = f"{BASE_PATH}/{year}"

        print(f"\n📁 Processing year: {year}  →  {year_path}")

        try:
            excel_files = []
            if os.path.isdir(year_path):
                for root, dirs, files in os.walk(year_path):
                    for f in files:
                        if f.endswith(".xlsx") and not f.startswith("~$"):
                            excel_files.append(os.path.join(root, f))
            else:
                print(f"   ⚠️  Folder does not exist: {year_path}")
                continue

        except Exception as e:
            print(f"   ⚠️  Could not read folder for {year}: {e}")
            continue

        if not excel_files:
            print(f"   ⚠️  No .xlsx files found in {year_path}")
            continue

        print(f"   Found {len(excel_files)} Excel file(s)")

        for file_path in sorted(excel_files):
            filename = os.path.basename(file_path)
            month = extract_month_from_filename(filename)

            if month == 0:
                print(f"   ⚠️  Could not determine month from filename: {filename}")
                files_failed += 1
                continue

            print(f"   📄 {filename}  →  {MONTH_NAME_MAP[month]} {year}", end=" ... ")

            sdf = read_faac_deduction_excel(file_path, year, month)

            if sdf is not None:
                row_count = sdf.count()
                print(f"✅ {row_count} rows")
                all_dataframes.append(sdf)
                files_processed += 1
            else:
                print("❌ failed")
                files_failed += 1

    if not all_dataframes:
        print("\n❌ No data was loaded. Pipeline stopped.")
        return

    print(f"\n{'─'*65}")
    print(f"🔗 Merging {len(all_dataframes)} monthly datasets...")

    merged = all_dataframes[0]
    for df in all_dataframes[1:]:
        merged = merged.unionByName(df, allowMissingColumns=True)

    numeric_fill_cols = [
        "external_debt", "contractual_obligation_ispo", "other_deductions_note",
        "transfer_nddc_hyppadec", "deduction_misc", "other_deduction",
        "total_deductions", "net_amount_after_deductions", "lg_count"
    ]
    for c in numeric_fill_cols:
        if c in merged.columns:
            merged = merged.withColumn(c, F.coalesce(F.col(c), F.lit(0).cast(LongType())))

    merged = merged.orderBy("disbursement_date", "state")

    total_rows = merged.count()
    print(f"   Total rows merged: {total_rows:,}")
    print(f"   Date range: {merged.agg(F.min('disbursement_date')).collect()[0][0]} "
          f"to {merged.agg(F.max('disbursement_date')).collect()[0][0]}")
    print(f"   States: {merged.select('state').distinct().count()}")

    print(f"\n💾 Writing to warehouse: {WAREHOUSE_NAME}.{TARGET_TABLE}")
    print(f"   Mode: OVERWRITE (replaces existing table if present)\n")

    try:
        (
            merged.write
            .format("fabric.api.spark.sql")
            .option("warehouse", WAREHOUSE_NAME)
            .option("schema", "dbo")
            .option("tableName", "faac_monthly_deduction")
            .mode("overwrite")
            .save()
        )
        print(f"✅ Successfully written to {WAREHOUSE_NAME}.dbo.faac_monthly_deduction")

    except Exception as e:
        print(f"   ℹ️  Direct warehouse write failed ({e})")
        print(f"   🔄 Falling back: saving as Delta table in Lakehouse...")

        (
            merged.write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable("faac_monthly_deduction")
        )
        print(f"✅ Saved as Delta table: faac_monthly_deduction")
        print(f"   You can now reference this in your Warehouse via the Lakehouse shortcut.")

    print(f"\n{'='*65}")
    print(f"  ✅ PIPELINE COMPLETE")
    print(f"{'='*65}")
    print(f"  Files processed successfully : {files_processed}")
    print(f"  Files failed / skipped       : {files_failed}")
    print(f"  Total rows in final table    : {total_rows:,}")
    print(f"  Table                        : {WAREHOUSE_NAME}.dbo.faac_monthly_deduction")
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
