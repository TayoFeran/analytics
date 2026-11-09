-- One row per state per FAAC month, with every revenue and deduction line, for the States,
-- Revenue mix, Deductions and Compare pages. Whole naira: the site shows millions and
-- billions, and dropping kobo keeps the file small on mobile data. Zone is in faac_states
-- and the exchange rate in faac_national_month, so neither is repeated on every row here.
select
    disbursement_date,
    state,
    round(total_gross_amount)::bigint as gross,
    round(total_deductions)::bigint as deductions,
    round(net_amount_after_deductions)::bigint as net,
    -- Revenue lines (they add up to gross)
    round(statutory_allocation)::bigint as statutory_allocation,
    round(gross_vat_allocation)::bigint as vat,
    round(oil_derivation)::bigint as oil_derivation,
    round(exchange_gain_difference)::bigint as exchange_gain,
    round(total_ecology_fund)::bigint as ecology_fund,
    round(others_income)::bigint as other_income,
    -- Deduction lines (they add up to deductions)
    round(external_debt)::bigint as external_debt,
    round(contractual_obligation_ispo)::bigint as contractual_obligation_ispo,
    round(transfer_nddc_hyppadec)::bigint as transfer_nddc_hyppadec,
    round(other_deductions_note)::bigint as other_deductions_note,
    round(deduction_misc)::bigint as deduction_misc,
    round(other_deduction)::bigint as other_deduction
from datamart.nigeria_faac_state_month
order by disbursement_date, state
