-- One row per state per FAAC month, for the top-5 states and later the state pages.
-- Whole naira: the site shows millions and billions, and dropping kobo keeps the file
-- small on mobile data. Zone is in faac_states and the exchange rate in
-- faac_national_month, so neither is repeated on every row here.
select
    disbursement_date,
    state,
    round(total_gross_amount)::bigint as gross,
    round(total_deductions)::bigint as deductions,
    round(net_amount_after_deductions)::bigint as net
from datamart.nigeria_faac_state_month
order by disbursement_date, state
