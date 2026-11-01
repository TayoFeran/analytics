---
name: add-project
description: Add a new project, or a new data source to an existing project, in this analytics repo. Covers the load script into MotherDuck bronze, the dbt bronze/silver/gold models, the gold schema, the daily-pipeline step and docs. TRIGGER when the user wants to add or start a project, ingest a new API, dataset or source, add a pipeline or load script, or create a new gold schema.
---

# Add a project or a source

The repo and the MotherDuck warehouse are shared by **unrelated projects**. Every project uses the same layout and naming, so projects never mix or clash. The full human guide, with every snippet, is `docs/runbooks/adding-a-project.md`. Read it before starting, and follow it. This skill is the checklist for doing it reliably.

The user is learning data engineering: say what each step does and why before doing it, one step at a time.

## 1. Ask first (one AskUserQuestion round)

Don't guess these:

- **New project or new source for an existing one?** List existing projects from `pipelines/` and `dbt/models/motherduck/gold/`.
- **Project name** (lowercase snake_case: it becomes a folder, a gold schema and a prefix) and **source name**.
- **What is loaded**: endpoint/dataset, which fields, and the grain (what one row is).
- **Credentials**: does the source need an API key?
- **Schedule**: daily with the others (default), or something else, which needs its own workflow.

## 2. Build it, following the runbook

Work on a branch named `<project>/add-project` or `<project>/add-<source>`. Steps:

1. **Load script**: copy `templates/load_source_template.py` (in this skill folder) to `pipelines/<project>/load_<source>_<what>.py`. Fill in the placeholders. **Don't remove its safety checks**: allowed databases, fetch-before-connect, stop on 0 rows, one transaction, `utc_now()`, and the token read from the environment (never in the connection string). For more than a few hundred rows, stage locally and upload with one `INSERT ... SELECT` (see `pipelines/nigeria/load_faac_allocations.py`). Source files that aren't fetched from an API live in `data/<project>/<source>/`. Add or extend `pipelines/<project>/README.md`. Add keys to `.env.example`, and libraries with `uv add --group pipelines`.
2. **Bronze**: `dbt/models/motherduck/bronze/<project>/<source>/_<project>_<source>__sources.yml`, with source name `<project>_<source>`, `database: "{{ target.database }}"`, `schema: bronze`, and `identifier:` set to the full table name.
3. **Silver**: `silver/<project>/<source>/stg_<project>_<source>__<entity>.sql` plus its own `_<model>.yml`.
4. **Gold**: `gold/<project>/<project>_<what>.sql` plus its own `_<model>.yml`, testing the grain. For a **new project only**, add `<project>: {+schema: <project>}` under `gold:` in `dbt/dbt_project.yml`.
5. **Schedule**: one step per load script in `.github/workflows/daily-pipeline.yml`, before `dbt build (prod)`, named `"<project>: load <source> <what> into prod_dwh.bronze"`, with any secrets in `env:`.
6. **Docs**: `README.md` and the **Projects** section and gold table list in `docs/architecture.md`.

## Mistakes to avoid

- A bare or generic file name (`extract.py`, `load.py`), or a table or model without the project prefix. dbt model names must be unique across **all** projects.
- Forgetting the `+schema` entry for a new gold folder. The models would land in `main`.
- Putting the workflow step after `dbt build`. The models would read yesterday's bronze.
- Adding a `dbt/models/fabric/` folder or anything Fabric-specific: Fabric is retired, and dbt-duckdb only builds in MotherDuck.
- Tests outside the house rules: one `_<model>.yml` per model, built-in tests only, no packages or singular tests.
- Running anything against `prod_dwh` locally. Only `daily-pipeline` writes prod.

## 3. Verify before proposing a commit

- [ ] Load script runs against `dev_dwh` and prints sensible row counts
- [ ] `.\dbt\run_dbt.ps1 build --select path:models/motherduck/bronze/<project> path:models/motherduck/silver/<project> path:models/motherduck/gold/<project>` is all green (a new source: select its `<source>` subfolders and the affected gold models)
- [ ] `uv run pre-commit run --all-files` is all green (ruff, mypy on `pipelines/`, sqlfmt, dbt parse)
- [ ] `uvx --from actionlint-py actionlint .github/workflows/*.yml` if the workflow changed
- [ ] `grep` finds no leftover `<placeholder>` or `TODO` from the template in the new files

Then show `git status` and a summary, and **ask before committing**. Commit format: `<project>(+): Add <source> <what> project`. No Claude attribution in commits or PRs. After the merge, offer to watch the `daily-pipeline` run it triggers, and check the new `prod_dwh` objects.
