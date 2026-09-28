# analytics

Git integration target for the Microsoft Fabric **`analytics`** workspace.

This repo is auto-synced by Fabric — connect the workspace via **Workspace settings → Git integration** in the Fabric portal, then use the Source Control panel there to commit/update. Items land in folders here that mirror the workspace's folder structure, so as more projects get added to the workspace, each gets its own subfolder.

Don't hand-edit synced item files unless you know what you're doing — Fabric overwrites unrelated files inside an item's folder on commit.

## Projects

| Folder | What it is |
| --- | --- |
| [`nigeria-faac/`](nigeria-faac) | FAAC (Federation Account Allocation Committee) pipeline, synced from the Fabric workspace folder of the same name: Lakehouse, Warehouse, notebooks, copy jobs and the orchestrating data pipeline. |
| [`nigeria-economic-indicators/`](nigeria-economic-indicators) | World Bank extraction to MotherDuck, dbt medallion models and tests, orchestrated with Airflow. Not a Fabric item. |

Related: [`nigeria`](https://github.com/TayoFeran/nigeria) — human-facing documentation/portfolio repo for the FAAC project. This repo holds the actual synced pipeline/notebook code; `nigeria` holds the narrative.
