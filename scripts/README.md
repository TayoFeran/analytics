# scripts

Small tools for working on the repo. They don't load data and aren't scheduled.

| Script | What it does | Run |
|---|---|---|
| `check_motherduck.py` | Checks that the token in `.env` works and lists the databases it can see | `uv run --group pipelines python scripts/check_motherduck.py` |
