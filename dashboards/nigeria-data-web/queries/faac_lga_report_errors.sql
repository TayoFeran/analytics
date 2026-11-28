-- The known mistakes in the OAGF reports' LGA tables, one row per state and month, so a
-- state's page can say what was wrong in the report and how the site handles it.
select distinct disbursement_date, state, report_error as error
from nigeria.nigeria_faac_lga_allocation
where report_error is not null
order by disbursement_date, state
