# 0003: A public website instead of Power BI Publish to web

- Status: accepted
- Date: 2026-11-09

## Context

The Nigeria Data Dashboard (#2) exists so that Nigerians and anyone interested can see what public data says about the economy. It was built in Power BI, and the plan was to share it with Publish to web. That has three problems:

- It depends on a Power BI tenant and licence. The Power BI and Fabric trials in use end around 2026-11-19, and a Free licence can't use shared workspaces.
- It renders a fixed 1280x720 canvas, which is hard to read on a phone, and most of the audience browses on phones over mobile data.
- Search engines can't index it, so people can only find it through a shared link.

The longer-term aim is a trusted public platform for insights on the Nigerian economy, with interactive data pages and plain-language explainers. A dashboard alone doesn't serve that.

## Decision

Build a public website in `dashboards/nigeria-data-web/` with [Astro](https://astro.build), host it on Cloudflare Pages, and update it from `daily-pipeline.yml`:

1. dbt builds `prod_dwh` as before.
2. An export step runs readable `.sql` files against MotherDuck and writes small JSON files.
3. Astro builds static pages from those files.
4. The pages are deployed to Cloudflare Pages.

The MotherDuck token stays in GitHub Secrets. Visitors download only finished public numbers and never connect to the warehouse. The Power BI report stays live until the website covers everything it shows.

### Options considered

| Option | Why not chosen |
|---|---|
| Power BI Publish to web only | Licence-dependent, not mobile-friendly, not searchable (see Context) |
| Power BI Embedded | Needs a paid Azure capacity, costing hundreds of dollars a month |
| [Evidence.dev](https://evidence.dev) | Pages are Markdown plus SQL, which an analyst can own end to end, and filters, charts and per-state pages come built in. But it's built for dashboards, not a publication: articles, branding, page weight on mobile and page-level search settings are harder to control, and custom pieces such as flip cards need Svelte code anyway |
| Streamlit | Generic look, and the free hosting sleeps when idle |
| Custom site with Astro (chosen) | Made for content sites: articles in Markdown, no JavaScript shipped unless a page needs it, full control of design and search metadata |

### Who owns what

- The data (dbt models and the export `.sql` files) and the words (Markdown pages and articles) are maintained by the repo owner.
- The presentation code (layout, charts, filters) is written and maintained with an AI coding assistant.

The export SQL stays in plain files, so the numbers on the site can always be traced back to a query.

### Hosting

Cloudflare Pages is free, serves from data centres close to Nigerian users, and its terms don't restrict the kind of site. GitHub Pages' terms rule out sites run mainly as a business, and Vercel's free plan is for non-commercial use only, so either would mean moving host as the platform grows.

## Consequences

- No licence to expire, and the site works on any phone.
- Adding a new FAAC workbook stays the only manual step. The site updates with the rest of the daily pipeline.
- The DAX logic in the Power BI model (period comparisons, real terms, per-president figures) has to be rewritten in SQL for each page that uses it.
- Building the site needs Node.js, both locally to preview and in GitHub Actions.
- A new failure point in the daily pipeline. A failed site build must not block the dbt build, so the site steps run after it.
- Maintaining the presentation code relies on an AI assistant or a web developer.
