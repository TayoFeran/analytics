# nigeria

Ingestion for the Nigeria project. One `load_<source>_<what>.py` script per source.

| Script | Source | Writes |
|---|---|---|
| `load_world_bank_indicators.py` | World Bank API | `bronze.nigeria_world_bank_indicators_annual`, `bronze.nigeria_world_bank_indicators_monthly` |
| `load_faac_allocations.py` | FAAC workbooks in [`data/nigeria/faac/`](../../data/nigeria/faac) | `bronze.nigeria_faac_income_sheet`, `bronze.nigeria_faac_deduction_sheet` |

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
