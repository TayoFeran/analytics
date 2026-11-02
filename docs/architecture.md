# Architecture

How data moves from public sources to tables you can query, and what runs it.

## Overview

```text
                         GitHub Actions: daily-pipeline.yml (05:00 UTC, on merge, or by hand)
                         ┌──────────────────────────────────────────────────────────────────┐
                         │                                                                  │
 World Bank API ─────────▶ pipelines/nigeria/load_world_bank_indicators.py ─┐                       │
 data/nigeria/faac/*.xlsx ▶ pipelines/nigeria/load_faac_allocations.py ─────┴▶ bronze ─dbt▶ silver ─dbt▶ gold
                         │                                          (raw)    (views)     (tables)│
                         └──────────────────────────────────────────────────────────────────┘
                                                        MotherDuck: prod_dwh

```

## Projects

The repo and warehouse are shared by unrelated projects. Every layer is organized by project first: `pipelines/<project>/`, `bronze/<project>/<source>/`, `silver/<project>/<source>/` and `gold/<project>/`. `bronze` and `silver` are shared schemas, so their tables and views start with the project name. Today's projects: `nigeria` (World Bank indicators and FAAC allocations) and `sandbox` (ad-hoc and shared tables such as `fo_calendar`).

## Layers

| Layer | Where the code is | MotherDuck schema | Built by | What a row is |
|---|---|---|---|---|
| bronze | `pipelines/<project>/load_<source>_<what>.py` writes it, and `dbt/models/motherduck/bronze/<project>/<source>/` declares it as a dbt source | `bronze` (shared; tables named `<project>_<source>_<what>`) | the load script | the raw API value, plus `extracted_at` |
| silver | `dbt/models/motherduck/silver/<project>/<source>/` | `silver` (shared; models named `stg_<project>_<source>__<entity>`) | dbt (views) | one cleaned, typed observation |
| gold | `dbt/models/motherduck/gold/<schema>/` | one schema per subfolder: `nigeria`, `sandbox`, `datamart` | dbt (tables) | a business-ready fact, e.g. one month of the FX rate |
| seeds | `dbt/seeds/<schema>/` | one schema per subfolder: `sandbox` | dbt (`dbt seed`, part of `dbt build`) | a row of a small hand-maintained reference list, e.g. a state and its zone |

Gold tables today:

| Table | Grain | Source |
|---|---|---|
| `nigeria.nigeria_gdp` | one row per year | World Bank `NY.GDP.MKTP.CD` |
| `nigeria.nigeria_population` | one row per year | World Bank `SP.POP.TOTL` |
| `nigeria.nigeria_fx_rate` | one row per month | World Bank `DPANUSSPB` |
| `nigeria.nigeria_consumer_price_index` | one row per month | World Bank `CPTOTNSXN` |
| `nigeria.nigeria_faac_income` | one row per state per month (`state_month`) | FAAC workbooks, Income sheet |
| `nigeria.nigeria_faac_deduction` | one row per state per month (`state_month`) | FAAC workbooks, Deduction sheet (+ Income for the net-amount fallback) |
| `sandbox.fo_calendar` | one row per day, 1990-01-01 to today | generated |
| `datamart.nigeria_faac_state_month` | one row per state per month (`state_month`) | FAAC income + deduction, with every amount also in US dollars at the month's official exchange rate. Fact table of the Nigeria Data Dashboard's FAAC section |

Reference lists (dbt seeds, in `sandbox`):

| Table | Grain | What it's for |
|---|---|---|
| `sandbox.nigeria_state` | one row per state (36 + FCT) | geopolitical zone and region (North/South) of each state |
| `sandbox.nigeria_administration` | one row per administration | president, party, term dates and the first FAAC month attributed to each |

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
| `daily-pipeline` workflow | `.github/workflows/daily-pipeline.yml` | 05:00 UTC daily, on merges that change `dbt/`, `pipelines/` or `data/`, and by hand |

Secrets: `MOTHERDUCK_TOKEN` lives in `.env` locally (gitignored) and as a GitHub Actions repository secret.

## FAAC: moved from Fabric

FAAC now runs on MotherDuck (#17): the workbooks live in `data/nigeria/faac/`, and `nigeria.nigeria_faac_income` and `nigeria.nigeria_faac_deduction` replace Fabric's `DWH.nigeria.faac_income` and `faac_deduction`. The migration was reconciled row by row against Fabric. Every difference traced back to a bug in the Fabric notebooks, the largest being a net-amount fallback that understated net allocations by about ₦4.48 trillion. The details are in #17.

Fabric was retired on 2026-11-02: the Git integration was disconnected, the `Analytics_Engineering` workspace deleted, and the Fabric item folders removed from the repo (they remain in git history before that date). See [decision 0001](decisions/0001-motherduck-over-fabric.md).
