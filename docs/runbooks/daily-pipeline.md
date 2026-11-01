# Runbook: daily pipeline

What to do when `daily-pipeline` fails or stops running. GitHub emails you when a scheduled run fails.

## Look at the failed run

```bash
gh run list --workflow daily-pipeline.yml --limit 5
gh run view <run-id> --log-failed
```

Or on GitHub: **Actions**, then **daily-pipeline**, then the red run, then the failed step.

## By failed step

### "Install dependencies"

- `uv.lock` is out of date: someone changed `pyproject.toml` without running `uv lock`. Run `uv lock` locally, commit, and merge.

### "nigeria: load World Bank indicators into prod_dwh.bronze"

| Error | Cause | Fix |
|---|---|---|
| `MOTHERDUCK_TOKEN is not set` | The repository secret is missing | Set it again: Settings, Secrets and variables, Actions, `MOTHERDUCK_TOKEN` |
| Authentication or token error from MotherDuck | Token expired or revoked | Create a new token in MotherDuck (Settings, Access tokens), then update the secret and your local `.env` |
| `0 rows fetched for <code>` | The World Bank API returned nothing for that indicator. This is a guard: **bronze was left unchanged** | Usually a temporary API problem: re-run later. If it persists, check the indicator code at api.worldbank.org |
| HTTP 5xx or timeout | World Bank API down | Re-run later. The script already retries 3 times |

Nothing is half-written in any of these cases: the extract fetches everything before connecting, and loads in one transaction.

### "dbt build (prod)"

- A **test failed**: open the log, find `FAIL`, and look at the test's model and column. Common cause: World Bank renamed an indicator, so an `accepted_values` test on `indicator_name` fails. Update the extract's indicator names and the silver yml, and test in dev first.
- A **model failed**: reproduce it locally in dev with `.\dbt\run_dbt.ps1 build --select <model>+` and fix it through a PR.

### A step hangs at "Opening a new connection"

Seen once locally: a MotherDuck connection stalled while dbt opened several connections at once. The job's 30 minute timeout ends it. Re-run. If it repeats, set `threads: 1` for the `prod` target in `dbt/profiles.yml`.

## Re-run

**Actions**, then **daily-pipeline**, then **Run workflow** on `main`, or:

```bash
gh workflow run daily-pipeline.yml
gh run watch
```

Re-running is always safe: each run replaces bronze in full and rebuilds every model.

## The schedule stopped running

GitHub **disables scheduled workflows after 60 days with no commits** to the repo. Re-enable it under **Actions**, then **daily-pipeline**, then **Enable workflow**, or with `gh workflow enable daily-pipeline.yml`. Then trigger one run by hand.

## Check that prod is fresh

```bash
uv run --group pipelines python -c "import duckdb, dotenv; dotenv.load_dotenv(); print(duckdb.connect('md:').sql('select max(extracted_at) from prod_dwh.bronze.nigeria_world_bank_indicators_annual').fetchone())"
```

The value should be from today's run, around 05:00 UTC.
