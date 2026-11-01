# Restructure plan

## Progress

| Phase | Status | PR |
|---|---|---|
| 0. Clean start | done | #6 |
| 1. Foundations | done | #7 |
| 2. Quality gates | done | #8 |
| 3. One dbt project | done | #9 |
| 4. Prod database | done | #10 |
| 5. Pipelines | done | #11 |
| 6. Scheduling + CI | done; first cloud prod run green on 2026-11-01 | #12 |
| 7. Docs | done | this PR |
| 8. FAAC on MotherDuck | done (#17) | #18 |
| 9. Retire Fabric | done: Git disconnected, workspace deleted, folders removed | this PR |

Branch protection on `main` was skipped while Fabric Git integration committed straight to `main` (2026-11-01), and turned on once Fabric was retired (2026-11-02): PRs only, `validate` and `dbt-dev` must pass, no admin bypass.

This plan is based on the `repo-restructure` skill, adjusted to your decisions from 2026-11-01. Findings are in [AUDIT.md](AUDIT.md). Each phase is one branch and PR, verified before it merges.

## Target layout

```text
analytics/                                  # the repo
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                          # every PR: lint, dbt parse, dev build of changed models
│   │   └── daily-pipeline.yml              # cron: extract World Bank → dbt build (prod)
│   └── pull_request_template.md
├── .claude/CLAUDE.md                       # how Claude should work in this repo
│
├── dbt/                                    # ONE dbt project for MotherDuck
│   ├── dbt_project.yml                     # folder decides schema + materialization
│   ├── profiles.yml                        # dev / prod / ci targets, token from env
│   ├── macros/generate_schema_name.sql
│   └── models/
│       └── motherduck/
│           ├── bronze/
│           │   └── world_bank/_world_bank__sources.yml   # raw tables written by pipelines/
│           ├── silver/
│           │   └── world_bank/
│           │       ├── stg_world_bank__indicators_annual.sql
│           │       └── _stg_world_bank__indicators_annual.yml   # one yml per model
│           └── gold/                       # one subfolder = one schema
│               ├── nigeria/                # nigeria_gdp, nigeria_fx_rate, ... (+ FAAC later)
│               └── sandbox/                # fo_calendar
│
├── pipelines/                              # get data INTO MotherDuck bronze
│   ├── world-bank/                         # extract.py as a package + README
│   └── faac/                               # phase 8
│
├── scripts/                                # one-off and repo tooling
├── docs/
│   ├── architecture.md
│   ├── decisions/                          # 0001-motherduck-over-fabric.md, 0002-github-actions-over-airflow.md
│   ├── runbooks/                           # "the daily pipeline failed"
│   └── restructure/                        # this plan + audit
├── archive/                                # airflow/, later the Fabric items
│
├── .env.example  .gitignore  .pre-commit-config.yaml
├── pyproject.toml  uv.lock  Makefile
└── README.md
```

### Schema mapping

| Folder | MotherDuck schema | Materialization |
|---|---|---|
| `bronze/<source>/` | `bronze` (written by `pipelines/`) | n/a, sources only |
| `silver/<source>/` | `silver` | view |
| `gold/<name>/` | `<name>` (e.g. `nigeria`, `sandbox`) | table |

Gold tables move from the `analytics` schema to `nigeria`. For example, `dev_dwh.analytics.nigeria_gdp` becomes `dev_dwh.nigeria.nigeria_gdp`. Model names keep their `nigeria_` prefix, because dbt needs every model name to be unique across the project.

### Dev and prod

Two MotherDuck databases, as the skill recommends:

| Target | Database | Used by |
|---|---|---|
| `dev` | `dev_dwh` (exists) | you, locally, and PR checks |
| `prod` | `prod_dwh` (new) | the scheduled GitHub Actions run only |
| `ci` | in-memory DuckDB | `dbt parse` in CI (no token) |

## Where this differs from the skill

| Skill says | We do | Why |
|---|---|---|
| dbt project in `analytics/` | `dbt/` | Your layout. |
| `staging/intermediate/marts` | `bronze/silver/gold`, gold split by schema | Your layout. The skill allows keeping medallion names. |
| `_<folder>__models.yml` per folder, `dbt_utils`, singular tests | `_<model>.yml` per model, built-in tests only | Your rule. |
| `schedules.json` + generator script | one hand-written `daily-pipeline.yml` | The generator only runs dbt jobs. Our job is extract + dbt in sequence, and there is only one. Adopt the generator once there are several dbt-only jobs. |
| `fabric/` folder, `fabric/sql/`, Fabric conventions | none | Fabric is being retired. See phase 9. |
| `dbt/models/fabric/` (your list) | not created | See open question 2. |

## Phases

Each phase ends with these checks: `dbt parse --no-partial-parse` passes, `dbt build --target dev` passes for any changed models, pre-commit is green, and `grep` finds no old paths.

| # | Phase | What changes | Verify |
|---|---|---|---|
| 0 | Clean start | Merge or stash the `sandbox/` work and delete the empty `calendar/`, so the tree is clean. | `git status` clean |
| 1 | Foundations | Root `.gitignore` and `.env.example`, `pyproject.toml` with uv (groups: `dbt`, `pipelines`, `dev`), `uv.lock`, `README.md` skeleton, `.claude/CLAUDE.md`. Untrack `dbt/.user.yml`. | `uv sync` works; old venv no longer needed |
| 2 | Quality gates | `.pre-commit-config.yaml`: ruff, sqlfmt, `dbt parse`, basic file checks, and commitizen for the commit format. mypy waits for phase 5, when `pipelines/` gets type hints. One commit for config, a **separate** formatting-only commit. | `pre-commit run --all-files` green |
| 3 | One dbt project | `git mv` the dbt project to `dbt/`. Models go into `motherduck/bronze|silver|gold/<schema>`. `fo_calendar` goes into `gold/sandbox`. Split `sources.yml` into `bronze/world_bank/_world_bank__sources.yml`. Rename silver models to `stg_world_bank__*`. Move schema config from model files to `dbt_project.yml`. `profiles.yml` gets dev/prod/ci targets. | `dbt build --target dev` all green; then drop the old `dev_dwh.analytics.*` tables |
| 4 | Prod database | Create `prod_dwh` with `bronze`. `extract.py` and dbt read the database name from env (dev by default). First prod build. | Row counts in `prod_dwh` match `dev_dwh` |
| 5 | Pipelines | `extract.py` → `pipelines/world-bank/` with a README and type hints. `setup_motherduck.py` → `archive/` (destructive one-off). `test_connection.py` → `scripts/check_motherduck.py`. | Extract runs against dev |
| 6 | Scheduling + CI | `daily-pipeline.yml` (cron, extract → `dbt build --target prod`), `ci.yml`, PR template, `MOTHERDUCK_TOKEN` secret, branch protection on `main`. Airflow → `archive/airflow/`. | Trigger the workflow manually (`workflow_dispatch`) once and check that it's green; CI is green on the PR |
| 7 | Docs | `docs/architecture.md`, ADRs 0001–0002, runbook, per-folder READMEs, root README layout. | Links resolve |
| 8 | FAAC on MotherDuck | Port both notebooks from PySpark to Python + DuckDB in `pipelines/faac/`. Keep every documented header quirk. Write `bronze.faac_*`, add `silver/faac/stg_faac__income|deduction`, `gold/nigeria/faac_income|deduction`, and a step in the daily workflow. | Totals per month match the Fabric `DWH.nigeria.faac_*` tables |
| 9 | Retire Fabric | Disconnect the workspace's Git integration. `git mv nigeria-faac/ shared/` → `archive/fabric/` (or delete, your call). Update the README. | Fabric workspace no longer syncing; README accurate |

**Phases 8 and 9 are deferred** (decided 2026-11-01). The user will open a GitHub issue for the FAAC migration when it's time. Until then, `nigeria-faac/` and `shared/` stay exactly where they are, and phases 1–7 don't touch them. One open point for that issue: the FAAC Excel files only exist in the Fabric Lakehouse, so they will need a home that GitHub Actions can reach.

**`dbt/models/fabric/` is left out** (decided 2026-11-01). The project uses the `dbt-duckdb` adapter, which can't build models in Fabric. The `motherduck/` level stays in case another platform is added later.

## Decisions

- Prod database: `prod_dwh`.
- Commit and PR titles use `<ticket or area>(<+|~|->): Short description`, e.g. `dbt(+): Add fo_calendar to gold/sandbox`, enforced by commitizen from phase 2.
