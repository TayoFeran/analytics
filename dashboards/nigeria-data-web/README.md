# Nigeria Data website

The public website for the Nigeria Data Dashboard: interactive pages and plain-language explainers on public Nigerian data, readable on any phone. Built with [Astro](https://astro.build). Phase 1 is tracked in #35, and the reasons for choosing a website over Power BI are in [`docs/decisions/0003`](../../docs/decisions/0003-public-website-over-power-bi.md).

The Power BI report in [`../nigeria-data-dashboard/`](../nigeria-data-dashboard/) stays live until this site covers everything it shows.

## How it gets its data

The site never connects to MotherDuck from the browser. Instead:

1. `daily-pipeline.yml` builds `prod_dwh` with dbt.
2. An export step runs the `.sql` files in `queries/` and writes small JSON files.
3. Astro builds static pages from those files.
4. The pages are deployed to Cloudflare Pages.

The MotherDuck token stays in GitHub Secrets, so visitors only ever download finished public numbers.

### Exporting the data locally

`export_site_data.py` runs every `queries/<name>.sql` and writes `src/data/<name>.json`, plus `src/data/export_info.json` (when it ran, from which database, row counts). **To add data to the site, add a `.sql` file:** the script picks it up without changes. Queries name tables without the database (`datamart.nigeria_faac_state_month`), so the same SQL runs against `dev_dwh` and `prod_dwh`.

From the repo root, with `MOTHERDUCK_TOKEN` in `.env`:

```bash
uv run --group pipelines python dashboards/nigeria-data-web/export_site_data.py
```

It reads `dev_dwh` unless `MOTHERDUCK_DATABASE=prod_dwh`, which only `daily-pipeline` sets. It stops without writing anything if a query fails or returns no rows. `src/data/` is rebuilt on every run and kept out of git, so run the export once before `npm run dev` on a fresh clone.

| Query | One row per | Used by |
|---|---|---|
| `faac_national_month.sql` | FAAC month, all states together: gross, deductions, net, the 6 revenue lines, the 6 deduction lines, naira per dollar | FAAC Overview |
| `faac_state_month.sql` | state per FAAC month: gross, deductions, net | FAAC Overview top 5, later the state pages |
| `faac_states.sql` | state: zone and region | colouring and grouping states by zone |

Amounts are whole naira. Dollars are worked out on the site as naira ÷ that month's `naira_per_usd`, the same way the datamart does it.

## Folder layout

```text
nigeria-data-web/
├── README.md
├── export_site_data.py runs queries/*.sql and writes src/data/*.json
├── queries/            the SQL behind each data file (one .sql per JSON file)
├── package.json        dependencies and the npm scripts (dev, build, preview)
├── package-lock.json   exact dependency versions; commit it, never edit by hand
├── astro.config.mjs    site settings
├── tsconfig.json       type checking for the site's code
├── .nvmrc              the Node.js major version (CI reads it too)
├── public/             files served as they are: favicon, images
└── src/
    ├── data/           exported JSON (generated, not in git)
    ├── layouts/        the frame around every page (header, menu, footer)
    ├── pages/          one file per page; src/pages/index.astro is the home page
    └── styles/         the palette and shared styles
```

`node_modules/` (installed packages), `dist/` (the built site) and `.astro/` (generated types) are rebuilt on demand and kept out of git.

## Preview locally

You need Node.js (the version in `.nvmrc`). From this folder:

```bash
npm install        # once, and after package.json changes
npm run dev        # opens a live preview at http://localhost:4321 that reloads as you edit
npm run build      # builds the finished site into dist/, as the pipeline does
npm run preview    # serves dist/ to check the built site
```
