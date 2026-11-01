# Runbook: adding a project or a source

The repo and the MotherDuck warehouse are shared by unrelated projects. Every project follows the same layout, so its files are easy to find and its tables never clash with another project's.

Claude Code follows this runbook through the `add-project` skill (`.claude/skills/add-project/`). Ask it to "add a project" or "add a source".

## Names first

| Name | Rule | Example |
|---|---|---|
| project | lowercase snake_case. Becomes a folder name, a gold schema and a prefix | `uk_housing` |
| source | lowercase snake_case, the system the data comes from | `ons` |
| what | what the script/table holds | `house_prices` |

Everything else is derived from these:

| Thing | Pattern | Example |
|---|---|---|
| load script | `pipelines/<project>/load_<source>_<what>.py` | `pipelines/uk_housing/load_ons_house_prices.py` |
| bronze table (shared `bronze` schema) | `<project>_<source>_<what>` | `bronze.uk_housing_ons_house_prices` |
| dbt sources file | `dbt/models/motherduck/bronze/<project>/<source>/_<project>_<source>__sources.yml` | `.../bronze/uk_housing/ons/_uk_housing_ons__sources.yml` |
| dbt source name | `<project>_<source>` | `uk_housing_ons` |
| silver model (shared `silver` schema) | `silver/<project>/<source>/stg_<project>_<source>__<entity>.sql` | `stg_uk_housing_ons__house_prices` |
| gold schema | `gold/<project>/` → schema `<project>` | `uk_housing` |
| gold model | `<project>_<what>` (dbt model names are unique across all projects) | `uk_housing_average_price` |
| model tests | `_<model_name>.yml` next to each model | `_uk_housing_average_price.yml` |
| commit prefix | `<project>(+\|~\|-)` | `uk_housing(+): Add ONS house prices project` |

## Steps for a new project

### 0. Branch

```bash
git switch main && git pull
git switch -c <project>/add-project
```

### 1. Load script (into bronze)

1. Copy `.claude/skills/add-project/templates/load_source_template.py` to `pipelines/<project>/load_<source>_<what>.py`.
2. Fill in `PROJECT`, `SOURCE`, the table's columns in `BRONZE_DDL`, and `fetch_rows()`.
3. Keep the safety checks the template already has: only `dev_dwh`/`prod_dwh`, fetch everything before connecting, stop on 0 rows, replace in one transaction, `utc_now()` for timestamps, and the token read from the environment, never put in the connection string. For several tables, add more `BRONZE_DDL` entries and call `replace_table` once per table inside the same transaction.
4. Add `pipelines/<project>/README.md`: one row per script (script, source, tables written), then what it pulls, safety checks, how to run and the schedule. `pipelines/nigeria/README.md` is the model.

If the source needs an API key:
- Add `<SOURCE>_API_KEY=` to `.env.example`, and the real value to your `.env`.
- `gh secret set <SOURCE>_API_KEY` for GitHub Actions.

If the data comes as files rather than from an API (e.g. Excel workbooks), commit them under `data/<project>/<source>/` and read them from there. Adding a file is then a commit, which triggers the prod load. `pipelines/nigeria/load_faac_allocations.py` is the example; it also shows staging rows locally and uploading them in one `INSERT ... SELECT`, which is much faster than row-by-row inserts for thousands of rows.

If it needs a new Python library: `uv add --group pipelines <library>`. That updates `pyproject.toml` and `uv.lock`.

Try it against dev:

```bash
uv run --group pipelines python pipelines/<project>/load_<source>_<what>.py
```

### 2. Bronze: declare the source in dbt

`dbt/models/motherduck/bronze/<project>/<source>/_<project>_<source>__sources.yml`:

```yaml
version: 2

sources:
  - name: <project>_<source>
    description: Raw <what> for the <project> project, loaded by pipelines/<project>/load_<source>_<what>.py.
    database: "{{ target.database }}"   # dev builds read dev_dwh, prod builds read prod_dwh
    schema: bronze
    tables:
      - name: <what>
        identifier: <project>_<source>_<what>
```

### 3. Silver: one cleaned view per bronze table

`dbt/models/motherduck/silver/<project>/<source>/stg_<project>_<source>__<entity>.sql`:

```sql
select <column_1>, <column_2>, extracted_at
from {{ source("<project>_<source>", "<what>") }}
```

Next to it, `_stg_<project>_<source>__<entity>.yml` with a description and built-in tests (`not_null`, `unique`, `accepted_values`, `relationships`, args under `arguments:`). No config needed: everything under `silver/` is a view in the `silver` schema. Only silver models call `source()`.

### 4. Gold: the finished tables

1. Create `dbt/models/motherduck/gold/<project>/` with models named `<project>_<what>.sql`, each reading silver with `ref()`, and a `_<model>.yml` that tests the grain (`unique` + `not_null` on the key).
2. Register the schema in `dbt/dbt_project.yml`. This is the only config change:

   ```yaml
         gold:
           +materialized: table
           nigeria:
             +schema: nigeria
           sandbox:
             +schema: sandbox
           <project>:
             +schema: <project>
   ```

3. Build only the new project in dev:

   ```powershell
   .\dbt\run_dbt.ps1 build --select path:models/motherduck/bronze/<project> path:models/motherduck/silver/<project> path:models/motherduck/gold/<project>
   ```

### 5. Schedule

In `.github/workflows/daily-pipeline.yml`, add one step per load script, after the existing load steps and **before** `dbt build (prod)`:

```yaml
      - name: "<project>: load <source> <what> into prod_dwh.bronze"
        run: uv run python pipelines/<project>/load_<source>_<what>.py
        # env:
        #   <SOURCE>_API_KEY: ${{ secrets.<SOURCE>_API_KEY }}
```

The existing `dbt build (prod)` step builds every project's models.

### 6. Docs

- `README.md`: mention the project in the layout or intro.
- `docs/architecture.md`: add it under **Projects**, and its gold tables to the gold table list.

### 7. Check, commit, PR

```bash
uv run pre-commit run --all-files
git add -A
git commit -m "<project>(+): Add <source> <what> project"
git push -u origin <project>/add-project
gh pr create --fill
```

CI checks everything and builds it in `dev_dwh`. When you merge, `daily-pipeline` runs straight away and creates the project's tables in `prod_dwh`. Watch that run under **Actions**.

## Adding a source to an existing project

The same steps with the project's existing folders:
- **Step 1:** add a new `load_<source>_<what>.py` next to the existing scripts, and a row in the project's pipeline README.
- **Steps 2–3:** add new `<source>/` folders under `bronze/<project>/` and `silver/<project>/`.
- **Step 4:** add models to the existing `gold/<project>/`. **No** `dbt_project.yml` change.
- **Steps 5–7:** unchanged.

Example: FAAC for Nigeria would be `pipelines/nigeria/load_faac_<what>.py`, `bronze/nigeria/faac/`, `silver/nigeria/faac/stg_nigeria_faac__<entity>.sql` and gold models in `gold/nigeria/`.

## Checklist

- [ ] Names follow the patterns above; no bare `extract.py`, every bronze table and silver/gold model starts with the project
- [ ] Load script keeps the template's safety checks and runs against `dev_dwh`
- [ ] Every model has its own `_<model>.yml`; gold tests its grain; built-in tests only
- [ ] New gold schema registered in `dbt_project.yml` (new projects only)
- [ ] `dbt build` of the new paths is green in dev
- [ ] `daily-pipeline.yml` step added before `dbt build`, with any secrets
- [ ] API keys in `.env.example` and GitHub secrets; libraries added with `uv add`
- [ ] README and `docs/architecture.md` mention the project
- [ ] `pre-commit run --all-files` green, PR CI green, first prod run after merge green

## Good to know

- All projects share one daily run. If one load step fails, later steps, including `dbt build`, are skipped for every project that day. If that becomes a problem, split projects into separate jobs or workflows.
- A project that needs a different schedule (weekly, monthly) needs its own workflow file with its own cron.
