-- One row per FAAC month for all 36 states together: what was allocated, what was deducted,
-- and what the states received, with each revenue line and each deduction line.
-- Whole naira, and naira only: the site converts to dollars with naira_per_usd, the same
-- month's rate the datamart uses, so dollar columns don't double the file size.
select
    disbursement_date,
    round(sum(total_gross_amount))::bigint as gross,
    round(sum(total_deductions))::bigint as deductions,
    round(sum(net_amount_after_deductions))::bigint as net,
    -- Revenue lines (they add up to gross)
    round(sum(statutory_allocation))::bigint as statutory_allocation,
    round(sum(gross_vat_allocation))::bigint as vat,
    round(sum(oil_derivation))::bigint as oil_derivation,
    round(sum(exchange_gain_difference))::bigint as exchange_gain,
    round(sum(total_ecology_fund))::bigint as ecology_fund,
    round(sum(others_income))::bigint as other_income,
    -- Deduction lines (they add up to deductions)
    round(sum(external_debt))::bigint as external_debt,
    round(sum(contractual_obligation_ispo))::bigint as contractual_obligation_ispo,
    round(sum(transfer_nddc_hyppadec))::bigint as transfer_nddc_hyppadec,
    round(sum(other_deductions_note))::bigint as other_deductions_note,
    round(sum(deduction_misc))::bigint as deduction_misc,
    round(sum(other_deduction))::bigint as other_deduction,
    -- One rate per month, so any() picks it
    round(any_value(naira_per_usd), 4) as naira_per_usd,
    count(*) as states
from datamart.nigeria_faac_state_month
group by disbursement_date
order by disbursement_date
