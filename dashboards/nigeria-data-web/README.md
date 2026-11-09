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

## Folder layout

```text
nigeria-data-web/
├── README.md
├── package.json        dependencies and the npm scripts (dev, build, preview)
├── package-lock.json   exact dependency versions; commit it, never edit by hand
├── astro.config.mjs    site settings
├── tsconfig.json       type checking for the site's code
├── .nvmrc              the Node.js major version (CI reads it too)
├── public/             files served as they are: favicon, images
└── src/
    └── pages/          one file per page; src/pages/index.astro is the home page
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
