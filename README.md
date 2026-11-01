# analytics

[![daily-pipeline](https://github.com/TayoFeran/analytics/actions/workflows/daily-pipeline.yml/badge.svg)](https://github.com/TayoFeran/analytics/actions/workflows/daily-pipeline.yml)
[![ci](https://github.com/TayoFeran/analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/TayoFeran/analytics/actions/workflows/ci.yml)

Data pipelines that load public Nigerian economic data into **MotherDuck** and model it with **dbt** in bronze, silver and gold layers. **GitHub Actions** runs everything in the cloud: a daily production load, and checks on every pull request.

```text
World Bank API ─▶ pipelines/nigeria ─▶ bronze ─dbt─▶ silver ─dbt─▶ gold (nigeria, sandbox)
                                          MotherDuck: dev_dwh (development) · prod_dwh (production)
```

The FAAC pipeline still runs in **Microsoft Fabric** until it's migrated to MotherDuck. See [architecture](docs/architecture.md) for the full picture.

## Layout

| Folder | What it is |
| --- | --- |
| [`pipelines/`](pipelines) | Ingestion: one folder per project, one `load_<source>_<what>.py` per source, loading raw data into MotherDuck `bronze`. Today: [`nigeria/`](pipelines/nigeria). |
| [`dbt/`](dbt) | The dbt project: `models/motherduck/bronze/<project>/<source>` (sources), `silver/<project>/<source>` (cleaned views) and `gold/<schema>` (tables; each subfolder is a schema: `nigeria`, `sandbox`). |
| [`.github/`](.github) | GitHub Actions workflows (`daily-pipeline`, `ci`) and the PR template. |
| [`scripts/`](scripts) | Repo tooling, e.g. `check_motherduck.py` to test your token. |
| [`docs/`](docs) | [Architecture](docs/architecture.md), [decisions](docs/decisions), [runbooks](docs/runbooks) and the [restructure record](docs/restructure). |
| [`archive/`](archive) | Retired code kept for reference (the old Airflow project, one-off setup). Nothing here runs. |
| [`nigeria-faac/`](nigeria-faac), [`shared/`](shared) | FAAC pipeline and its storage, written by Fabric Git integration. Don't hand-edit: Fabric overwrites unrelated files inside an item's folder on commit. |
| [`.claude/`](.claude) | Instructions for Claude Code in this repo. |

## How it runs

| Workflow | When | What |
| --- | --- | --- |
| `daily-pipeline` | daily 05:00 UTC, on merges that change `dbt/` or `pipelines/`, or by hand ("Run workflow") | World Bank extract into `prod_dwh.bronze`, then `dbt build --target prod`. The only writer to `prod_dwh`. |
| `ci` | every PR and push to `main` | pre-commit checks, then `dbt build --target dev` on PRs. |

Both use the `MOTHERDUCK_TOKEN` repository secret. If a run fails, see the [runbook](docs/runbooks/daily-pipeline.md).

## Setup

Python dependencies are managed with [uv](https://docs.astral.sh/uv/) in `pyproject.toml`, in groups per area (`dbt`, `pipelines`, `dev`).

```bash
uv sync                       # create .venv with every group
uv run pre-commit install     # run the quality checks on every commit
cp .env.example .env          # then fill in MOTHERDUCK_TOKEN
uv run --group pipelines python scripts/check_motherduck.py   # check the token works
```

## Everyday commands

```powershell
# Load fresh World Bank data into dev_dwh
uv run --group pipelines python pipelines/nigeria/load_world_bank_indicators.py

# Build and test dbt models in dev_dwh (PowerShell; loads .env for you)
.\dbt\run_dbt.ps1 build
.\dbt\run_dbt.ps1 build --select nigeria_gdp+

# Run every quality check
uv run pre-commit run --all-files
```

## Contributing

1. Branch from `main`.
2. Make the change, and build it in dev.
3. Commit with the format `<area or ticket>(<+|~|->): Short description`, e.g. `dbt(+): Add fo_calendar`. The commit hook checks it.
4. Open a PR. CI runs the checks and a dev build.
5. Merge. Changes to `dbt/` or `pipelines/` deploy to prod straight away.

## Related

[`nigeria`](https://github.com/TayoFeran/nigeria): documentation and portfolio repo for the FAAC project. This repo holds the pipeline code; `nigeria` holds the narrative.
