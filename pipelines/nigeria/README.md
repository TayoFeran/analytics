# nigeria

Ingestion for the Nigeria project. One `load_<source>_<what>.py` script per source.

| Script | Source | Writes |
|---|---|---|
| `load_world_bank_indicators.py` | World Bank API | `bronze.nigeria_world_bank_indicators_annual`, `bronze.nigeria_world_bank_indicators_monthly` |

## load_world_bank_indicators.py

Pulls Nigerian economic indicators from the [World Bank API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392) and loads them into MotherDuck bronze tables. The dbt models in `dbt/models/motherduck/` build silver and gold from there.

### What it pulls

| Indicator | Code | Frequency | From |
|---|---|---|---|
| GDP (current US$) | `NY.GDP.MKTP.CD` | annual | 1990 |
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
