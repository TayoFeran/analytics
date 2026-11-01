# 0001: MotherDuck is the warehouse; Fabric is being phased out

- Status: accepted
- Date: 2026-11-01

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
