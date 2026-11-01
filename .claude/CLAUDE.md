# Project instructions for Claude Code

## What this repo is

Personal data-engineering portfolio. Python pipelines load public Nigerian economic data into MotherDuck, and dbt models it into bronze, silver and gold layers. The FAAC pipeline still runs in Microsoft Fabric (`nigeria-faac/`, `shared/`) until it's migrated to MotherDuck.

The repo is being restructured. Follow `docs/restructure/PLAN.md` for the target layout and phase order.

## Where things go

- dbt: one project in `dbt/`, models in `dbt/models/motherduck/<bronze|silver|gold>/`. Each subfolder of `gold/` is a schema, e.g. `gold/nigeria`, `gold/sandbox`.
- Ingestion code: `pipelines/<source>/`. Repo tooling and one-off scripts: `scripts/`. Docs: `docs/`.
- If a new file doesn't clearly fit, ask before creating a new top-level folder.
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

- Two databases: `dev_dwh` for local work and PR checks, `prod_dwh` written only by the scheduled GitHub Actions job. Never build against prod locally unless I ask.
- Load env first (Git Bash): `set -a; source .env; set +a`
- Tests: one `_<model_name>.yml` per model, next to its `.sql`. Built-in generic tests only (`unique`, `not_null`, `accepted_values`, `relationships`), with args nested under `arguments:`. No `dbt_utils`, no custom or singular tests.
- After a model or yml change: `dbt parse --no-partial-parse`, then `dbt build --target dev --select <model>+`.

## Fabric

- Items in `nigeria-faac/` and `shared/` are written by Fabric Git integration: don't hand-edit them.
- FAAC migration to MotherDuck is deferred until there's a GitHub issue for it.

## Code quality

- Checks run on every commit through pre-commit (ruff, sqlfmt, dbt parse, file checks, commit message format). Run everything with `uv run pre-commit run --all-files`. Never skip hooks with `--no-verify`.
- Comments explain why, not what.
- Script output is plain text (`Error: ...`, `Wrote 3 tables`), no emojis or decorative lines.
