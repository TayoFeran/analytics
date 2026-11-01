# Architecture

How data moves from public sources to tables you can query, and what runs it.

## Overview

```text
                         GitHub Actions: daily-pipeline.yml (05:00 UTC, on merge, or by hand)
                         ┌──────────────────────────────────────────────────────────────────┐
                         │                                                                  │
 World Bank API ──▶ pipelines/nigeria/load_world_bank_indicators.py ──▶ bronze ─dbt▶ silver ─dbt▶ gold │
                         │                              (raw)       (views)        (tables) │
                         └──────────────────────────────────────────────────────────────────┘
                                                        MotherDuck: prod_dwh

 FAAC Excel files ──▶ Fabric notebooks ──▶ Lakehouse ──▶ copy jobs ──▶ Fabric Warehouse  (being migrated)
```

## Projects

The repo and warehouse are shared by unrelated projects. Every layer is organized by project first: `pipelines/<project>/`, `bronze/<project>/<source>/`, `silver/<project>/<source>/` and `gold/<project>/`. `bronze` and `silver` are shared schemas, so their tables and views start with the project name. Today's projects: `nigeria` (World Bank indicators; FAAC later) and `sandbox` (ad-hoc and shared tables such as `fo_calendar`).

## Layers

| Layer | Where the code is | MotherDuck schema | Built by | What a row is |
|---|---|---|---|---|
| bronze | `pipelines/<project>/load_<source>_<what>.py` writes it, and `dbt/models/motherduck/bronze/<project>/<source>/` declares it as a dbt source | `bronze` (shared; tables named `<project>_<source>_<what>`) | the load script | the raw API value, plus `extracted_at` |
| silver | `dbt/models/motherduck/silver/<project>/<source>/` | `silver` (shared; models named `stg_<project>_<source>__<entity>`) | dbt (views) | one cleaned, typed observation |
| gold | `dbt/models/motherduck/gold/<schema>/` | one schema per subfolder: `nigeria`, `sandbox` | dbt (tables) | a business-ready fact, e.g. one month of the FX rate |

Gold tables today:

| Table | Grain | Source |
|---|---|---|
| `nigeria.nigeria_gdp` | one row per year | World Bank `NY.GDP.MKTP.CD` |
| `nigeria.nigeria_population` | one row per year | World Bank `SP.POP.TOTL` |
| `nigeria.nigeria_fx_rate` | one row per month | World Bank `DPANUSSPB` |
| `nigeria.nigeria_consumer_price_index` | one row per month | World Bank `CPTOTNSXN` |
| `sandbox.fo_calendar` | one row per day, 1990-01-01 to today | generated |

## Environments

| | dev | prod |
|---|---|---|
| MotherDuck database | `dev_dwh` | `prod_dwh` |
| Written by | you, locally, and the `ci` workflow on PRs | only the `daily-pipeline` workflow |
| Extract setting | `MOTHERDUCK_DATABASE=dev_dwh` (default) | `MOTHERDUCK_DATABASE=prod_dwh` |
| dbt | `--target dev` (default) | `--target prod` |

The two databases have identical schemas, and the dbt source reads `{{ target.database }}`, so prod models only ever read prod bronze. dbt also has a `ci` target, an in-memory DuckDB used by `dbt parse` in pre-commit and CI, with no token or network.

## Automation

| What | Where | Runs |
|---|---|---|
| Local checks | `.pre-commit-config.yaml` | every `git commit`: file checks, ruff, mypy, sqlfmt, dbt parse, commit message format |
| `ci` workflow | `.github/workflows/ci.yml` | every PR (checks + `dbt build --target dev`) and push to `main` (checks) |
| `daily-pipeline` workflow | `.github/workflows/daily-pipeline.yml` | 05:00 UTC daily, on merges that change `dbt/` or `pipelines/`, and by hand |

Secrets: `MOTHERDUCK_TOKEN` lives in `.env` locally (gitignored) and as a GitHub Actions repository secret.

## Fabric (FAAC)

The FAAC pipeline still runs in Microsoft Fabric, synced to `nigeria-faac/` and `shared/` by Fabric Git integration. Don't hand-edit those folders. Moving FAAC to MotherDuck will be tracked in its own GitHub issue. See [decision 0001](decisions/0001-motherduck-over-fabric.md).
