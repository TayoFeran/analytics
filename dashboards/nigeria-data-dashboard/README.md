# Nigeria Data Dashboard

A Power BI dashboard for public Nigerian data, organised in sections. Tracked in #2.

| Section | Status | Source tables (`prod_dwh`) |
|---|---|---|
| FAAC | In design | `datamart.nigeria_faac_state_month`, `sandbox.nigeria_state`, `sandbox.nigeria_administration`, `sandbox.fo_calendar` |
| Economic metrics | Planned | `nigeria.*` World Bank indicators |
| Elections | Planned | Needs a new source |

## Folder layout

```text
nigeria-data-dashboard/
├── README.md
└── design/
    ├── make_backgrounds.py   draws the page backgrounds and placement.md
    ├── placement.md          x / y / w / h of every visual and nav button
    └── backgrounds/          one 2560x1440 PNG per page
```

The Power BI project files (`.pbip`, semantic model and report) will be added here once they're built.

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
