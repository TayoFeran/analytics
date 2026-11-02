-- States with FAAC data (FCT is not in the reports), with zone and region
select state, zone, region
from sandbox.nigeria_state
where state in (select distinct state from datamart.nigeria_faac_state_month)
