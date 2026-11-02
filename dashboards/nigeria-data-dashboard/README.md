# Nigeria Data Dashboard

A Power BI dashboard for public Nigerian data, organised in sections. Tracked in #2.

| Section | Status | Source tables (`prod_dwh`) |
|---|---|---|
| FAAC | Model built, pages in progress | `datamart.nigeria_faac_state_month`, `sandbox.nigeria_state`, `sandbox.nigeria_administration`, `sandbox.fo_calendar` |
| Economic metrics | Data model built | `datamart.nigeria_economy_month`, `datamart.nigeria_economy_year`, `sandbox.nigeria_administration`, `sandbox.fo_calendar` |
| Elections | Planned | Needs a new source |

## Folder layout

```text
nigeria-data-dashboard/
├── README.md
├── NigeriaDataDashboard.pbip              open this in Power BI Desktop
├── NigeriaDataDashboard.SemanticModel/    tables, relationships and measures, as TMDL
├── NigeriaDataDashboard.Report/           pages and visuals, as PBIR JSON
├── queries/                               readable copy of each table's SQL
└── design/
    ├── make_backgrounds.py   draws the page and tooltip backgrounds, and placement.md
    ├── placement.md          x / y / w / h of every visual and nav button, tooltip pages included
    ├── tooltips.md           which visual uses which tooltip, metric definitions, tooltip DAX
    ├── make_state_map.py     builds maps/nigeria_states.json for the States page shape map
    ├── maps/                 nigeria_states.json: TopoJSON of the 36 states and the FCT
    └── backgrounds/          bg_*.png: one 2560x1440 image per page
                              tt_*.png: one image per tooltip page, at 2x its custom size
```

The project is saved as PBIP so every change shows up in a git diff. Power BI also writes a `.pbi/` folder with the data cache and per-user settings; `.gitignore` keeps those out, because the cache holds query results.

## Connecting to MotherDuck

The model reads MotherDuck through its Postgres endpoint. Two parameters (Transform data → Edit parameters) set where:

| Parameter | Value | Note |
|---|---|---|
| `MotherDuckHost` | `pg.eu-west-1-aws.motherduck.com` | Not a secret |
| `MotherDuckDatabase` | `prod_dwh` | Switch to `dev_dwh` to test model changes, then switch back |

The first refresh asks for credentials: choose **Database**, any user name, and a MotherDuck token as the password. Power BI keeps it in its own credential store, so the token is never written into the project files.

A fresh clone has no data until you refresh (Home → Refresh), because the cache isn't in git.

Each table loads with a native SQL query. The same SQL is in `queries/<table>.sql`, which is easier to read and review than the one-line copy inside the TMDL. Change both together.

## Page backgrounds

Each page uses a background image for everything that never changes: the sidebar, the header, the filter bar container, card shapes and static labels. Charts, numbers, slicers, dynamic titles, the refresh stamp and the navigation buttons are live Power BI visuals placed on top. This keeps the visuals light and the pages consistent.

In Power BI, for each page: Format page → Canvas background → Image, Image fit **Fit**, Transparency **0%**. The canvas is 1280x720; the images are drawn at 2x so they stay sharp on high-resolution screens. Place visuals with the positions in [`design/placement.md`](design/placement.md) and give them transparent backgrounds.

### Regenerating

The layout lives in `LAYOUT` and `NAV` in `make_backgrounds.py`. After changing them, run this from `design/`:

```bash
uv run --no-project --with pillow python make_backgrounds.py
```

This rewrites the images in `backgrounds/` and `placement.md`. Pillow is only needed for this script, so it isn't a project dependency. The script uses Segoe UI from `C:/Windows/Fonts`, the font Power BI uses, so it runs on Windows.

### Palette

| Role | Hex |
|---|---|
| Sidebar | `#0B3D2E` |
| Active nav item | `#14563F` |
| Accent (gold) | `#E2B53E` |
| Canvas | `#F3F6F4` |
| Cards | `#FFFFFF` |
| Title text | `#0F2019` |
| Series 1 / 2 | `#0E6B45` / `#8FC9AE` |
| Better / worse / equal (Compare page) | `#0E8A5F` / `#C93C3C` / `#C98A00` |

## States map

The States page uses Power BI's shape map with a custom map of Nigeria's 36 states and the FCT, `design/maps/nigeria_states.json`. A copy is packaged inside the report (`StaticResources/RegisteredResources/`), so the map needs no internet connection or map service.

The boundaries come from [geoBoundaries](https://www.geoboundaries.org/) (gbOpen NGA ADM1, state boundaries by GRID3, 2022), licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The licence allows reuse with credit, which is on the About page.

The map keys are the state names, matched to `dim_state[state]`. The FCT is renamed "Federal Capital Territory" and has no FAAC data, so it is drawn grey. To rebuild the file, run this from `design/`:

```bash
uv run --no-project --with topojson python make_state_map.py
```

Shape maps only read TopoJSON. TopoJSON stores each border between two states once, so simplifying it leaves no gaps or overlaps between neighbours.
