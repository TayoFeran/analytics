-- One row per local government council per FAAC month, with its revenue and deduction
-- lines, for the Local governments pages. Whole naira. Only the build reads this file:
-- each state's page packs its own councils, so a phone never downloads all 774. Gross,
-- deductions and net are worked out from the lines on the site, as for the states.
-- September 2021 has no LGA figures (ADR 0004), so it has no rows.
select
    disbursement_date,
    state,
    lga_sn,
    lga,
    -- Revenue lines (they add up to gross)
    round(statutory_allocation)::bigint as statutory_allocation,
    round(gross_vat_allocation)::bigint as vat,
    round(exchange_gain_difference)::bigint as exchange_gain,
    round(total_ecology_fund)::bigint as ecology_fund,
    round(others_income)::bigint as other_income,
    -- Deduction lines (they add up to deductions)
    round(deduction)::bigint as deduction,
    round(transfer_nddc_hyppadec)::bigint as transfer_nddc_hyppadec,
    -- The report's own Total Allocation for this council doesn't match its lines: the
    -- site shows the total of the lines and says so
    report_check = 'report_error' as printed_total_wrong
from nigeria.nigeria_faac_lga_allocation
order by disbursement_date, state, lga_sn
