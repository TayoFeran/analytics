# Project instructions for Claude Code

## What this repo is

Personal data-engineering portfolio. Python pipelines load public Nigerian economic data into MotherDuck, and dbt models it into bronze, silver and gold layers. The FAAC pipeline still runs in Microsoft Fabric (`nigeria-faac/`, `shared/`) until it's migrated to MotherDuck.

The layout comes from the restructure recorded in `docs/restructure/` (phases 0-7 done; FAAC phases 8-9 wait for a GitHub issue). See `docs/architecture.md` for how it fits together, and `docs/decisions/` for why.

## Where things go

- dbt: one project in `dbt/`, models in `dbt/models/motherduck/<bronze|silver|gold>/`. Each subfolder of `gold/` is a schema, e.g. `gold/nigeria`, `gold/sandbox`.
- The warehouse and repo are shared by **unrelated projects**, not only Nigeria. Organize by project first in every layer, and give files self-describing names (never a bare `extract.py`).
- Ingestion code: `pipelines/<project>/load_<source>_<what>.py`, e.g. `pipelines/nigeria/load_world_bank_indicators.py`. Repo tooling and one-off scripts: `scripts/`. Docs: `docs/`.
- If a new file doesn't clearly fit, ask before creating a new top-level folder.
- Adding a project or a source: use the `add-project` skill (`.claude/skills/add-project/`), which follows `docs/runbooks/adding-a-project.md`.
- Don't create `dbt/models/fabric/`. The dbt-duckdb adapter can't build in Fabric.

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
- dbt folders are `<layer>/<project>/<source>/` for bronze and silver, and `gold/<project or schema>/`.
- bronze and silver are **shared schemas**, so names carry the project: bronze tables `<project>_<source>_<what>`, silver models `stg_<project>_<source>__<entity>`, sources declared as `<project>_<source>` in `bronze/<project>/<source>/_<project>_<source>__sources.yml`.

## Fabric

- Items in `nigeria-faac/` and `shared/` are written by Fabric Git integration: don't hand-edit them.
- FAAC migration to MotherDuck is deferred until there's a GitHub issue for it.

## Code quality

- Checks run on every commit through pre-commit (ruff, sqlfmt, dbt parse, file checks, commit message format). Run everything with `uv run pre-commit run --all-files`. Never skip hooks with `--no-verify`.
- Comments explain why, not what.
- Script output is plain text (`Error: ...`, `Wrote 3 tables`), no emojis or decorative lines.
