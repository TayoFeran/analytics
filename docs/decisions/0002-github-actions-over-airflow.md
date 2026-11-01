# 0002: GitHub Actions schedules the pipeline instead of Airflow

- Status: accepted
- Date: 2026-11-01

## Context

The World Bank pipeline was scheduled by Airflow (an Astro project) running in Docker on a laptop. It only ran while the laptop was on and Docker was up, so in practice it rarely ran on schedule. The requirement: the pipeline must run without the laptop being on.

## Decision

A GitHub Actions workflow, `.github/workflows/daily-pipeline.yml`, runs the extract and then `dbt build --target prod`, daily at 05:00 UTC. It also runs on merges that change `dbt/` or `pipelines/` (so prod picks up changes the same day), and on demand. Airflow is kept in `archive/airflow/` for reference.

One hand-written workflow is used instead of the config-driven `schedules.json` + generator pattern from the restructure skill. That generator only schedules dbt-only jobs, and there is a single extract-then-dbt job today. Adopt it once there are several dbt-only jobs with different cadences.

## Consequences

- Free for this usage, nothing to host, and runs in the same environment as CI (`uv sync --locked`).
- Scheduled runs are in UTC and can start a few minutes late. Nothing here needs an exact minute.
- GitHub disables scheduled workflows after 60 days with no commits. See [the runbook](../runbooks/daily-pipeline.md).
- No backfills, cross-job dependencies or retries per task. If those are needed, move to Dagster, Prefect or Airflow on a hosted service.
