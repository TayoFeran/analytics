# sandbox

Standalone dbt project for sandbox tables in MotherDuck. Every model here builds into `dev_dwh.sandbox`. It does not depend on any other project in this repo.

## Models

- `fo_calendar`: date dimension with one row per day from 1990-01-01 to the current date, ported from the Redshift `sandbox.fo_calendar` script. Because it stops at `current_date`, rebuild it regularly to add new days.

## Run

1. Copy `.env.example` to `.env` and set `MOTHERDUCK_TOKEN`.
2. Install `dbt-duckdb`.
3. From `dbt/`, run:

```powershell
.\run_dbt.ps1 build   # builds the table and runs its tests
```
