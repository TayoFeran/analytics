# analytics

Data pipelines that load public Nigerian economic data into **MotherDuck** and model it with **dbt** in bronze, silver and gold layers. The FAAC pipeline still runs in **Microsoft Fabric**, synced to this repo through Fabric Git integration, until it's migrated to MotherDuck.

> This repo is being restructured in phases. See [`docs/restructure/PLAN.md`](docs/restructure/PLAN.md) for the target layout and progress.

## Layout

| Folder | What it is |
| --- | --- |
| [`dbt/`](dbt) | The dbt project for MotherDuck. Models live in `models/motherduck/bronze` (sources), `silver` (cleaned views) and `gold/<schema>` (tables, one subfolder per schema: `nigeria`, `sandbox`). |
| [`pipelines/`](pipelines) | Ingestion: one folder per source that loads data into MotherDuck bronze. Today: [`world-bank/`](pipelines/world-bank). |
| [`scripts/`](scripts) | Repo tooling, e.g. `check_motherduck.py` to test your token. |
| [`archive/`](archive) | Parked code kept for reference. Nothing here runs. |
| [`nigeria-economic-indicators/`](nigeria-economic-indicators) | Airflow (Astro) orchestration, until phase 6 moves scheduling to GitHub Actions. |
| [`nigeria-faac/`](nigeria-faac) | FAAC (Federation Account Allocation Committee) pipeline, synced from Fabric: notebooks, copy jobs and the orchestrating data pipeline. |
| [`shared/`](shared) | Fabric storage used by FAAC: `Data_lake.Lakehouse` and `DWH.Warehouse`. |
| [`docs/`](docs) | Documentation, including the restructure audit and plan. |
| [`.claude/`](.claude) | Instructions for Claude Code in this repo. |

Fabric items (`nigeria-faac/`, `shared/`) are written by Fabric. Don't hand-edit them, because Fabric overwrites unrelated files inside an item's folder on commit.

## Setup

Python dependencies are managed with [uv](https://docs.astral.sh/uv/) in `pyproject.toml`, in groups per area (`dbt`, `pipelines`).

```bash
uv sync --all-groups          # create .venv with every group
uv run pre-commit install     # run the quality checks on every commit
cp .env.example .env          # then fill in MOTHERDUCK_TOKEN
set -a; source .env; set +a   # load env vars (Git Bash)
```

Run dbt (PowerShell, from anywhere in the repo; loads `.env` for you):

```powershell
.\dbt\run_dbt.ps1 build                        # build and test everything in dev_dwh
.\dbt\run_dbt.ps1 build --select fo_calendar   # one model
```

## Related

[`nigeria`](https://github.com/TayoFeran/nigeria): documentation and portfolio repo for the FAAC project. This repo holds the pipeline code; `nigeria` holds the narrative.
