# Repo audit

Date: 2026-11-01. Phase 0 of the restructure, which only reads the repo and changes nothing. The plan is in [PLAN.md](PLAN.md).

## What the repo does today

Two pipelines that don't share anything:

| Pipeline | Source | Runs on | Writes to | Scheduled by |
|---|---|---|---|---|
| World Bank indicators | World Bank API (GDP, population, FX rate, CPI) | your laptop | MotherDuck `dev_dwh` (bronze → silver → analytics) | Airflow (Astro, Docker on your laptop), `@daily` |
| FAAC income and deductions | Excel files in the Fabric Lakehouse (`Data_lake/Files/FAAC/Refined/{year}/*.xlsx`) | Microsoft Fabric | Fabric Warehouse `DWH.nigeria.faac_income` / `faac_deduction` | Fabric pipeline schedule (currently **disabled**) |

There is also the new `sandbox/` dbt project (`fo_calendar`). It is uncommitted, on the `add-fo-calendar-model` branch.

## How data flows

```text
World Bank API ─ extract.py ─▶ dev_dwh.bronze.* ─ dbt silver (views) ─▶ dev_dwh.silver.* ─ dbt gold ─▶ dev_dwh.analytics.nigeria_*
FAAC .xlsx (Lakehouse Files) ─ PySpark notebooks ─▶ Lakehouse dbo.faac_monthly_* ─ copy jobs ─▶ DWH.nigeria.faac_*
(generated) ─ dbt sandbox project ─▶ dev_dwh.sandbox.fo_calendar
```

## Inventory

| Current path | What it is | Used? | Proposed new path | Notes |
|---|---|---|---|---|
| `README.md` | Repo overview, written for "Fabric sync target" | yes | `README.md` (rewritten) | Describes the repo as Fabric-first. Out of date once FAAC leaves Fabric. |
| `nigeria-economic-indicators/extract.py` | World Bank API → `bronze` tables | yes | `pipelines/world-bank/` | Database name is hard-coded, so it only writes to the dev database. No type hints. |
| `nigeria-economic-indicators/setup_motherduck.py` | One-off: drops the old `analytics.nigeria` schema, creates `dev_dwh` schemas | done, one-off | `scripts/` or `archive/` | **Destructive** (`DROP SCHEMA ... CASCADE`). Must not be run by accident. |
| `nigeria-economic-indicators/test_connection.py` | Checks the MotherDuck connection | occasionally | `scripts/check_motherduck.py` | |
| `nigeria-economic-indicators/.env.example`, `.gitignore` | Env template, ignores | yes | root `.env.example`, `.gitignore` | Merge into the root files. |
| `nigeria-economic-indicators/dbt/` | dbt project `nigeria_econ`: 2 silver views, 4 gold tables, `sources.yml` | yes | `dbt/` (root) | Gold models set `schema='analytics'` in each file. Config should come from the folder instead. |
| `nigeria-economic-indicators/dbt/.user.yml` | dbt's anonymous user id | no | untrack | Machine-specific, shouldn't be in git. |
| `nigeria-economic-indicators/dbt/run_dbt.ps1` | Loads `.env`, runs dbt | yes | replaced by `Makefile` / uv | |
| `nigeria-economic-indicators/airflow/` | Astro project: Dockerfile, DAG, requirements | yes, laptop only | `archive/airflow/` | Replaced by GitHub Actions. `exampledag.py`, `tests/dags/test_dag_example.py` and the default README are Astro boilerplate. |
| `sandbox/dbt/` (uncommitted) | dbt project `sandbox`: `fo_calendar` | yes | `dbt/models/motherduck/gold/sandbox/` | Merges into the single dbt project. |
| `calendar/` (untracked, empty) | Leftover from the rename | no | delete | Locked by VS Code earlier. |
| `nigeria-faac/*.Notebook` | PySpark: reads FAAC Excel, writes Lakehouse tables | yes | port to `pipelines/faac/`, then `archive/` | About 500 lines each. Header quirks are documented in the comments; keep that knowledge when porting. |
| `nigeria-faac/*.CopyJob`, `FAAC_Full_Job.DataPipeline` | Copy Lakehouse → Warehouse, orchestration | yes | `archive/` after FAAC migration | Schedule is disabled. |
| `shared/DWH.Warehouse`, `shared/Data_lake.Lakehouse` | Fabric storage definitions | yes, by FAAC | `archive/` after FAAC migration | `faac_income.sql` / `faac_deduction.sql` hold the table DDL. Useful reference for the dbt models. |

## Findings

- **No committed secrets.** I searched tracked files for tokens, passwords and keys and checked `.env` history; nothing found. The Fabric files contain workspace, item and connection IDs and a Warehouse endpoint hostname. Those are identifiers, not credentials.
- **No data files in git** (`.csv`, `.parquet`, `.duckdb`, `.pbix`).
- **No dev/prod separation.** Everything goes to `dev_dwh`.
- **No reproducible Python setup.** There's a local `venv/` with no lockfile or dependency list outside Airflow's `requirements.txt`.
- **No CI, no pre-commit, no linting.**
- **Scheduling depends on your laptop** (Airflow in local Docker), and the Fabric schedule is off. So nothing runs on its own today.
- **FAAC's input files live only in the Fabric Lakehouse.** They need a new home before Fabric can be retired.
