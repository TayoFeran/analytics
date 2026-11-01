# dbt

The single dbt project for MotherDuck (adapter: `dbt-duckdb`).

## Layout

```text
models/motherduck/
├── bronze/<source>/_<source>__sources.yml        raw tables loaded by pipelines/ (declared, not built)
├── silver/<source>/stg_<source>__<entity>.sql    views: one cleaned model per raw table
└── gold/<schema>/<model>.sql                      tables: each subfolder is its own schema
    ├── nigeria/                                  World Bank indicators for Nigeria
    └── sandbox/                                  ad-hoc and shared tables (fo_calendar)
```

A model's **folder** decides its schema and materialization (`dbt_project.yml`), so model files don't set `config(schema=..., materialized=...)`. `macros/generate_schema_name.sql` uses those schema names exactly, with no `main_` prefix.

## Conventions

- Every model has its own `_<model_name>.yml` next to it, with a description and tests.
- Tests are dbt's built-in generic tests only (`unique`, `not_null`, `accepted_values`, `relationships`), with arguments under `arguments:`. Every gold table tests its grain with `unique` + `not_null`.
- Only silver models call `source()`. Everything else uses `ref()`.

## Targets (`profiles.yml`)

| Target | Database | Used by |
|---|---|---|
| `dev` (default) | `md:dev_dwh` | you locally, and the `ci` workflow on PRs |
| `prod` | `md:prod_dwh` | the `daily-pipeline` workflow only |
| `ci` | in-memory DuckDB | `dbt parse` in pre-commit and CI (no token needed) |

The token comes from the `MOTHERDUCK_TOKEN` environment variable, never from this folder.

## Run

PowerShell, from anywhere in the repo (loads the root `.env`):

```powershell
.\dbt\run_dbt.ps1 build                         # build + test everything in dev_dwh
.\dbt\run_dbt.ps1 build --select nigeria_gdp+   # one model and everything downstream
```

Git Bash, from `dbt/`:

```bash
set -a; source ../.env; set +a
uv run --group dbt dbt build --profiles-dir .
```

## Add a model

1. Put the `.sql` file in the folder for its layer and schema. A new `gold/<schema>/` folder needs a `+schema` entry in `dbt_project.yml`.
2. Add `_<model_name>.yml` with a description and tests.
3. `.\dbt\run_dbt.ps1 build --select <model_name>+` until it's green, then open a PR. CI builds it in dev, and the merge deploys it to prod.
