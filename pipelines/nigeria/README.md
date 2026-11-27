# nigeria

Ingestion for the Nigeria project. One `load_<source>_<what>.py` script per source.

| Script | Source | Writes |
|---|---|---|
| `load_world_bank_indicators.py` | World Bank API | `bronze.nigeria_world_bank_indicators_annual`, `bronze.nigeria_world_bank_indicators_monthly` |
| `load_faac_allocations.py` | FAAC workbooks in [`data/nigeria/faac/`](../../data/nigeria/faac) | `bronze.nigeria_faac_income_sheet`, `bronze.nigeria_faac_deduction_sheet` |
| `refine_faac_reports.py` | OAGF FAAC report PDFs (outside git) | CSV files in [`data/nigeria/faac/oagf/`](../../data/nigeria/faac/oagf), not MotherDuck |
| `load_faac_oagf_reports.py` | CSV files in [`data/nigeria/faac/oagf/`](../../data/nigeria/faac/oagf) | `bronze.nigeria_faac_oagf_*` (7 tables) |

## refine_faac_reports.py

Reads the state table (Table III) of each monthly OAGF FAAC report and writes tidy CSV files to [`data/nigeria/faac/oagf/`](../../data/nigeria/faac/oagf). It runs on a laptop, not in GitHub Actions: the PDFs stay outside git, and only the CSV files are committed. Why, and which months come from Excel instead: [ADR 0004](../../docs/decisions/0004-faac-from-oagf-reports.md).

```bash
uv run --group refine python pipelines/nigeria/refine_faac_reports.py
```

Every report is checked against itself before anything is written (right month, 36 states, columns add up to the Total row, no copied tables). Unchanged files are reused from the last run by their SHA-256 fingerprint, so adding a month takes seconds. The checks and how to add a month: [`data/nigeria/faac/oagf/README.md`](../../data/nigeria/faac/oagf/README.md).

## load_faac_oagf_reports.py

Loads the CSV files that `refine_faac_reports.py` writes into bronze, **as written**: every printed figure of the state and LGA tables in long form, the columns' printed headers, the report each month came from, the known report errors and the reader's notes. Which line each column belongs to, the totals and the checks against the printed totals are in dbt (`silver/nigeria/faac_oagf/`, `gold/nigeria/nigeria_faac_state_allocation`, `nigeria_faac_lga_allocation`, `nigeria_faac_report_figure`), with the column-to-line maps as seeds in `dbt/seeds/sandbox/`.

| Table | Grain |
|---|---|
| `<database>.bronze.nigeria_faac_oagf_reports` | one row per month |
| `<database>.bronze.nigeria_faac_oagf_state_columns`, `..._lga_columns` | one row per month and column |
| `<database>.bronze.nigeria_faac_oagf_state_figures` | one row per month, state-table row and column |
| `<database>.bronze.nigeria_faac_oagf_lga_figures` | one row per month, council (or state TOTAL row) and column |
| `<database>.bronze.nigeria_faac_oagf_known_report_errors` | one row per month and state with a mistake in the report |
| `<database>.bronze.nigeria_faac_oagf_notes` | one row per note |

The same safety checks as the other loaders: only `dev_dwh` and `prod_dwh`, every file is read (and must have rows) before MotherDuck is touched, and all seven tables are replaced in one transaction. About half a million rows load in under a minute, because each table is staged locally and uploaded with one `INSERT ... SELECT`.

```bash
uv run --group pipelines python pipelines/nigeria/load_faac_oagf_reports.py   # dev_dwh
```

## load_world_bank_indicators.py

Pulls Nigerian economic indicators from the [World Bank API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) and loads them into MotherDuck bronze tables. The dbt models in `dbt/models/motherduck/` build silver and gold from there.

### What it pulls

| Indicator | Code | Frequency | From |
|---|---|---|---|
| GDP (current US$) | `NY.GDP.MKTP.CD` | annual | 1990 |
| GDP (current LCU) | `NY.GDP.MKTP.CN` | annual | 1990 |
| GDP growth (annual %) | `NY.GDP.MKTP.KD.ZG` | annual | 1990 |
| Population, total | `SP.POP.TOTL` | annual | 1990 |
| Official exchange rate (LCU per US$) | `DPANUSSPB` | monthly | 2010 |
| CPI price index, not seasonally adjusted | `CPTOTNSXN` | monthly | 2010 |

### What it writes

| Table | Grain |
|---|---|
| `<database>.bronze.nigeria_world_bank_indicators_annual` | one row per indicator per year |
| `<database>.bronze.nigeria_world_bank_indicators_monthly` | one row per indicator per month |

`<database>` comes from `MOTHERDUCK_DATABASE`: `dev_dwh` (default) or `prod_dwh`. Each run replaces both tables in full, in one transaction. The script creates the schema and tables if they don't exist.

### Safety checks

- Only `dev_dwh` and `prod_dwh` are accepted, so a typo can't create a stray database.
- Everything is fetched before MotherDuck is touched. If any indicator comes back with 0 rows, the run stops and bronze is left unchanged.
- If a load fails partway, the transaction rolls back and the previous rows stay.

### Run it

From the repo root, with `.env` filled in (see `.env.example`):

```bash
uv run --group pipelines python pipelines/nigeria/load_world_bank_indicators.py                              # dev_dwh
MOTHERDUCK_DATABASE=prod_dwh uv run --group pipelines python pipelines/nigeria/load_world_bank_indicators.py # prod: only the scheduled job
```

Then build the models: `.\dbt\run_dbt.ps1 build` (PowerShell).

### Schedule

Daily at 05:00 UTC by `.github/workflows/daily-pipeline.yml`, which loads `prod_dwh` and then runs `dbt build --target prod`.

## load_faac_allocations.py

Loads the monthly FAAC (Federation Account Allocation Committee) disbursement workbooks from [`data/nigeria/faac/`](../../data/nigeria/faac) into bronze, **as written in the files**: one row per state row of the Income and Deduction sheets, plus the source file, year and month. All business rules live in dbt (`silver/nigeria/faac/`, `gold/nigeria/nigeria_faac_*`): state spelling, recomputed totals, the net-amount fallback and the president lookup.

Moved from Microsoft Fabric in #17. How to add a month, the expected layout and the known quirks are in [`data/nigeria/faac/README.md`](../../data/nigeria/faac/README.md).

### What it writes

| Table | Grain |
|---|---|
| `<database>.bronze.nigeria_faac_income_sheet` | one row per state per workbook (Income sheet) |
| `<database>.bronze.nigeria_faac_deduction_sheet` | one row per state per workbook (Deduction sheet) |

### Safety checks

- Same database guard, one transaction, and token handling as the World Bank script.
- Columns are read **by position**, and every header row is checked against the known layouts. An unknown layout, a misnamed file, a file in the wrong year folder or a non-numeric amount stops the run before MotherDuck is touched.
- Rows are staged in a local in-memory DuckDB and uploaded with one `INSERT ... SELECT` per table, instead of 5,400 single-row inserts.

### Run it

```bash
uv run --group pipelines python pipelines/nigeria/load_faac_allocations.py   # dev_dwh
```

### Schedule

Daily with the World Bank load, and on any merge that changes `data/` (a new workbook), `pipelines/` or `dbt/`.
