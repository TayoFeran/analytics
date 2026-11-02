# Project instructions for Claude Code

## What this repo is

Personal data-engineering portfolio. Python pipelines load public Nigerian economic data into MotherDuck, and dbt models it into bronze, silver and gold layers. The FAAC allocation pipeline moved here from Microsoft Fabric in #17. Fabric was retired on 2026-11-02, and nothing in this repo uses it any more.

The layout comes from the restructure recorded in `docs/restructure/` (all phases 0-9 done, including the FAAC migration and Fabric's retirement). See `docs/architecture.md` for how it fits together, and `docs/decisions/` for why.

## Where things go

- dbt: one project in `dbt/`, models in `dbt/models/motherduck/<bronze|silver|gold>/`. Each subfolder of `gold/` is a schema, e.g. `gold/nigeria`, `gold/sandbox`.
- The warehouse and repo are shared by **unrelated projects**, not only Nigeria. Organize by project first in every layer, and give files self-describing names (never a bare `extract.py`).
- Source files that don't come from an API: `data/<project>/<source>/` (e.g. the FAAC workbooks in `data/nigeria/faac/`).
- Ingestion code: `pipelines/<project>/load_<source>_<what>.py`, e.g. `pipelines/nigeria/load_world_bank_indicators.py`. Repo tooling and one-off scripts: `scripts/`. Docs: `docs/`.
- If a new file doesn't clearly fit, ask before creating a new top-level folder.
- Adding a project or a source: use the `add-project` skill (`.claude/skills/add-project/`), which follows `docs/runbooks/adding-a-project.md`.

## How I want you to work

- I'm learning data engineering: explain what you're doing and why, step by step, before doing it.
- Work on a feature branch, never commit directly to `main`. Changes go through a PR.
- Use `git mv` to move files. Don't delete files without asking; park doubtful ones in `archive/`.
- Before committing, check `git status` for files staged earlier that don't belong.
- Commit only when I agree.
- Never add Claude attribution anywhere: no `Co-Authored-By` lines in commits, no "Generated with Claude Code" in PRs, issues or docs.

## Commit and PR format

`<ticket or area>(<+|~|->): Short description`. `+` is new, `~` is a change or fix, `-` is a removal. The prefix is a GitHub issue (`GH-12`) or an area (`dbt`, `ci`, `docs`, `pipelines`). Example: `dbt(+): Add fo_calendar to gold/sandbox`. PR titles use the same format.

## dbt (MotherDuck)

- Two databases: `dev_dwh` for local work and PR checks (`ci.yml`), `prod_dwh` written only by `.github/workflows/daily-pipeline.yml`. Never build against prod locally unless I ask.
- `pipelines/nigeria/load_world_bank_indicators.py` loads the database in `MOTHERDUCK_DATABASE` (default `dev_dwh`, only `dev_dwh`/`prod_dwh` allowed). dbt picks the database by `--target dev|prod`.
- Load env first (Git Bash): `set -a; source .env; set +a`
- Tests: one `_<model_name>.yml` per model, next to its `.sql`. Built-in generic tests only (`unique`, `not_null`, `accepted_values`, `relationships`), with args nested under `arguments:`. No `dbt_utils`, no custom or singular tests.
- After a model or yml change: `dbt parse --no-partial-parse`, then `dbt build --target dev --select <model>+`.
- Run dbt with `.\dbt\run_dbt.ps1 <command>` (PowerShell, loads `.env`), or from `dbt/` with `uv run --group dbt dbt <command> --profiles-dir .`.
- A model's folder sets its schema and materialization in `dbt_project.yml`. Don't add `config(schema=..., materialized=...)` to model files.
- dbt folders are `<layer>/<project>/<source>/` for bronze and silver, and `gold/<project or schema>/`. Dashboard-shaped facts go in `gold/datamart/` (schema `datamart`), named `<project>_<what>`. Hand-maintained reference lists are seeds in `dbt/seeds/<schema>/` (today `sandbox`), each with its own `_<seed>.yml`.
- bronze and silver are **shared schemas**, so names carry the project: bronze tables `<project>_<source>_<what>`, silver models `stg_<project>_<source>__<entity>`, sources declared as `<project>_<source>` in `bronze/<project>/<source>/_<project>_<source>__sources.yml`.

## FAAC and security

- FAAC runs on MotherDuck since #17 (`pipelines/nigeria/load_faac_allocations.py`, `nigeria.nigeria_faac_*`). Fabric is retired: don't add Fabric items or a `dbt/models/fabric/` folder.
- Never put the MotherDuck token in a connection string (`md:?motherduck_token=...`): DuckDB echoes it in error messages. Connect with `md:` and let the extension read `MOTHERDUCK_TOKEN` from the environment.

## Code quality

- Checks run on every commit through pre-commit (ruff, sqlfmt, dbt parse, file checks, commit message format). Run everything with `uv run pre-commit run --all-files`. Never skip hooks with `--no-verify`.
- Comments explain why, not what.
- Script output is plain text (`Error: ...`, `Wrote 3 tables`), no emojis or decorative lines.
