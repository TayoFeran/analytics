-- The 36 states and the FCT in the LGA data, with their geopolitical zone, for the
-- zone -> state -> council levels of the Local governments pages.
select state, zone
from sandbox.nigeria_state
where state in (select distinct state from nigeria.nigeria_faac_lga_allocation)
order by state
