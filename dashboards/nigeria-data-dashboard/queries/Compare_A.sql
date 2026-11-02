-- Everything a Compare side can be: administrations, states, zones, regions
-- that have FAAC data. Compare_B is a copy, so the two sides pick independently.
with
    faac as (select distinct president, state from datamart.nigeria_faac_state_month),
    states as (select * from sandbox.nigeria_state where state in (select state from faac))
select
    'Administration' as compare_by,
    1 as compare_by_order,
    president as member,
    row_number() over (order by term_start) as member_order
from sandbox.nigeria_administration
where president in (select president from faac)
union all
select 'State', 2, state, 100 + row_number() over (order by state)
from states
union all
select 'Zone', 3, zone, 200 + row_number() over (order by zone)
from (select distinct zone from states)
union all
select 'Region', 4, region, 300 + row_number() over (order by region)
from (select distinct region from states)
