# 0001: MotherDuck is the warehouse; Fabric is retired

- Status: accepted, carried out
- Date: 2026-11-01
- Carried out: 2026-11-02

## Context

The repo had two stacks that shared nothing:

- **World Bank:** Python into MotherDuck, modelled with dbt.
- **FAAC:** PySpark notebooks and copy jobs in Microsoft Fabric, writing to a Fabric Lakehouse and Warehouse.

Running two platforms doubled the tools, the scheduling and the documentation for a one-person project. dbt only covered MotherDuck: the `dbt-duckdb` adapter can't build models in Fabric, and the two can't share one dbt project.

## Decision

MotherDuck, with dbt, is the single warehouse. FAAC will be migrated to MotherDuck (`pipelines/faac/`, then bronze/silver/gold models), and Fabric may then be discontinued. The migration is deferred to its own GitHub issue. Until it's done, the Fabric items in `nigeria-faac/` and `shared/` stay where they are and are not hand-edited.

There is no `dbt/models/fabric/` folder. The `dbt/models/motherduck/` level is kept in case another platform is ever added as a separate dbt project.

## Consequences

- One place for transformations (`dbt/`), one set of tests and one schedule.
- Before Fabric can go, the FAAC Excel files, which today live only in the Fabric Lakehouse, need a home that GitHub Actions can reach.
- Fabric Git integration still commits straight to `main` with the owner's account. That is one reason `main` has no branch protection yet.

## Outcome (2026-11-02)

- FAAC was migrated in #17 (PR #18): the workbooks moved to `data/nigeria/faac/`, and `nigeria.nigeria_faac_income` / `nigeria_faac_deduction` replaced the Fabric Warehouse tables. A row-by-row reconciliation found 5 bugs in the Fabric notebooks, the largest understating net allocations by about ₦4.48 trillion (details in #17).
- The workspace's Git integration was disconnected, the `Analytics_Engineering` workspace was deleted, and `nigeria-faac/` and `shared/` were removed from the repo. They remain in git history.
- With Fabric no longer committing to `main`, branch protection was turned on: PRs only, and the `validate` and `dbt-dev` checks must pass.
