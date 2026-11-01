# archive

Code that is no longer used but kept for reference until a delete decision is made. Nothing here runs, and nothing should import from it.

| File | What it was | Why it's here |
|---|---|---|
| `airflow/` | Astro (Airflow) project that ran the World Bank extract and dbt daily in Docker on a laptop. | Replaced by `.github/workflows/daily-pipeline.yml`, which runs in the cloud. Its compose file still points at the repo-root `dbt/`, `pipelines/` and `.env`. |
| `setup_motherduck.py` | One-off setup from the original layout: dropped the old `analytics.nigeria` schema and created `dev_dwh` schemas and bronze tables. | `pipelines/world-bank/extract.py` now creates its own bronze tables. **Destructive** (`DROP SCHEMA ... CASCADE`): don't run it. |
