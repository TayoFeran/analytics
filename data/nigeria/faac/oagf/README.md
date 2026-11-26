# FAAC figures from the OAGF reports

The state table (Table III) and the local government (LGA) table of every monthly FAAC report published by the OAGF (Office of the Accountant-General of the Federation), from January 2020. `pipelines/nigeria/refine_faac_reports.py` writes every file in this folder. Don't edit them by hand: fix the reader and run it again. Why the data comes from the PDFs, and which months are exceptions: [ADR 0004](../../../../docs/decisions/0004-faac-from-oagf-reports.md).

The PDFs themselves aren't in git (about 200 MB). They're published on the OAGF's [FAAC report page](https://oagf.gov.ng/publications/faac-report/), and `reports.csv` records the fingerprint of each one.

## Files

| File | One row per | Columns |
|---|---|---|
| `reports.csv` | month | `shared_month`, `source_type` (`pdf` or `excel`), `file_name`, `sha256` of that file, `page` the state table is on, `reader_version` |
| `columns.csv` | month and column | `shared_month`, `position`, `column_id` (the number printed above the column, or `14a` for an unnumbered column after 14), `column_header` as printed, `header_key` (letters and digits only, for matching) |
| `state_figures/<year>.csv` | month, row and column | `shared_month`, `row_number`, `beneficiary` as printed, `row_type` (`state`, `other` or `total`), `lgc_count`, `column_id`, `amount` in naira |
| `notes.csv` | finding | `shared_month`, `note`: report quirks found by the checks, and why a month came from Excel |
| `lga_columns.csv` | month and LGA column | `shared_month`, `position`, `column_id` (numbered 1, 2, ... from the left), `column_header` as printed, `header_key` |
| `lga_figures/<year>/<yyyy-mm>.csv` | month, council and column | `shared_month`, `state` as the state table prints it (plus `FCT`), `lga_sn` (the council's number within its state), `lga` as printed, `row_type` (`lga` or `total`), `column_id`, `amount` in naira |
| `known_report_errors.csv` | month and state | `shared_month`, `state`, `error`: LGA tables whose councils don't add up to the state's TOTAL row in the report itself, kept as printed |

`shared_month` is the month the money was shared, the "shared in" month of the report's title. The report's figures are for the month before.

`row_type`:

- `state`: the 36 states. Nasarawa is spelled "NASSARAWA" in most reports.
- `other`: other beneficiaries some months list, such as FCT, HYPPADEC, the Governors Forum and derivation held for disputed oil fields (Soku, Gbetiokun, Akri, Mbede).
- `total`: the report's own Total row, kept so dbt can check every column against it.

A dash in the report is stored as `0.00`; a blank cell is left out. Column meanings change over the years, so `column_id` 11 in one month isn't the same line as 11 in another; match columns on `header_key`.

LGA tables:

- 774 councils a month: the 36 states' councils plus the FCT's 6 area councils, each state closed by its `total` row from the report.
- Council names are as printed, and a name that wraps onto two lines can come out cut short. `(state, lga_sn)` is the stable key; dbt maps it to a reference list of names.
- September 2021 has no LGA figures: its Excel report has no LGA sheet, and its PDF LGA table doesn't add up for five states and the FCT.

## Adding a month

1. Download the month's report from the [OAGF FAAC report page](https://oagf.gov.ng/publications/faac-report/) into the PDF folder: `<year>/Disbursement-<Month>-<year>.pdf`.
2. Run the refine script from the repo root. It reads only new or changed files:

   ```bash
   uv run --group refine python pipelines/nigeria/refine_faac_reports.py
   ```

   It takes the folders from `FAAC_OAGF_PDF_DIR` and `FAAC_RAW_EXCEL_DIR` in `.env`, or `--pdf-dir` and `--excel-dir`.
3. If it prints `Error: ...`, nothing was written. The message names the month and the check that failed.
4. Commit the changed CSV files on a branch and open a PR.

## Checks

Every month must pass all of these, or nothing is written:

- Table I on page 1 is for the file's month. A stale or mistyped state-table title only gets a note.
- 36 states are listed.
- No column holds two figures in one row.
- Every column adds up to the report's Total row, within ₦1. A Total cell left blank in the report gets a note.
- No month's Total row is identical to another month's (a copied table).
- The LGA table lists every state, in the state table's order, with the state table's number of councils.
- Each state's councils add up to its TOTAL row, within ₦1, in every LGA column. A mismatch that is the report's own mistake is listed in `KNOWN_REPORT_ERRORS` in the script, with what is wrong, and goes to `known_report_errors.csv` instead of failing the month.
