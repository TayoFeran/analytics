-- The 36 states in the FAAC data (FCT isn't in the reports), with zone and region, so the
-- site can colour and group states by zone.
select state, zone, region
from sandbox.nigeria_state
where state in (select distinct state from datamart.nigeria_faac_state_month)
order by state
