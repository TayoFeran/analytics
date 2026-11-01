# FAAC workbooks

Monthly FAAC (Federation Account Allocation Committee) disbursement workbooks for the Nigeria project, one file per month: `<year>/<year> <Mon> Disbursement.xlsx`. They were moved here from the Fabric Lakehouse (`Data_lake/Files/FAAC/Refined/`) in #17.

`pipelines/nigeria/load_faac_allocations.py` loads every file in this folder into `bronze.nigeria_faac_income_sheet` and `bronze.nigeria_faac_deduction_sheet`, and dbt builds `nigeria.nigeria_faac_income` and `nigeria.nigeria_faac_deduction`.

## Adding a month

1. Save the workbook as `data/nigeria/faac/<year>/<year> <Mon> Disbursement.xlsx`, e.g. `2026/2026 May Disbursement.xlsx` (3-letter month).
2. Load it into dev and build: `uv run --group pipelines python pipelines/nigeria/load_faac_allocations.py`, then `.\dbt\run_dbt.ps1 build --select path:models/motherduck/silver/nigeria/faac nigeria_faac_income nigeria_faac_deduction`.
3. Commit on a branch (`GH-<issue>(+): Add FAAC <Mon> <year> workbook`), open a PR and merge. The merge triggers `daily-pipeline`, which loads it into `prod_dwh`.

## What the loader expects

Each workbook has an `Income` and a `Deduction` sheet, with these headers in row 1 (extra spaces are ignored):

| Sheet | Columns, in order |
|---|---|
| Income | Beneficiaries, LGs, Statutory Allocation, Oil Derivation, Exchange Gain Difference, Total Ecology Fund, Gross VAT Allocation, Others Income, Total Gross Amount |
| Deduction | Beneficiaries, LGs, External Debt, Contractual Obligation (ISPO), Other Deductions (see Note), Transfer of 50% to NDDC/HYPPADEC, Deduction, Others Deduction (or "Others Income"), Total Gross Amount, then an unlabelled net-amount column |

A file with any other layout stops the load with an error naming the file, and nothing is changed. Update the layouts in the loader if NBS changes the format.

## Known quirks (all handled)

- Nasarawa is spelled "NASSARAWA" in every sheet. FCT isn't in the sheets.
- In the Deduction sheet, "Total Gross Amount" is the **total of deductions**. The net amount is in the unlabelled column after it.
- Totals and the net amount are blank in files saved without recalculating formulas (2020 Jan, 2024 Jun-Dec, 2025, 2026). dbt recomputes totals from their components, and derives the net amount as income total minus total deductions. That formula matches every file where the net amount is filled in.
- Every November and December file from 2020 to 2023 labels Deduction column 8 "Others Income".
- There is no October 2024 file.
