-- One row per state per FAAC disbursement month: what each state was allocated, what was
-- deducted, and the net it received, in naira and in US dollars. The fact table of the
-- OpenPurse site's and the Nigeria Data Dashboard's FAAC pages, from the original OAGF
-- reports (nigeria_faac_state_allocation, ADR 0004).
--
-- Dollar amounts use the official exchange rate of the disbursement month itself, so a
-- total across months is the sum of what each month was worth in dollars at the time.
-- Converting a multi-year naira total at a single rate would misstate it.
with
    allocation as (select * from {{ ref("nigeria_faac_state_allocation") }}),

    fx as (select date, exchange_rate from {{ ref("nigeria_fx_rate") }}),

    joined as (
        select
            allocation.state_month,
            allocation.disbursement_date,
            allocation.year,
            allocation.month_number,
            allocation.month_name,
            allocation.president,
            allocation.state,
            allocation.lg_count,
            allocation.statutory_allocation,
            allocation.oil_derivation,
            allocation.exchange_gain_difference,
            allocation.total_ecology_fund,
            allocation.gross_vat_allocation,
            allocation.others_income,
            allocation.total_gross_amount,
            allocation.external_debt,
            allocation.contractual_obligation_ispo,
            allocation.other_deductions_note,
            allocation.transfer_nddc_hyppadec,
            allocation.deduction_misc,
            -- The refined workbooks had a sixth deduction line that the OAGF reports don't
            -- print. Kept at 0 because the Power BI report still reads it.
            0::decimal(18, 2) as other_deduction,
            allocation.total_deductions,
            allocation.net_amount_after_deductions,
            -- Naira per US dollar in the disbursement month (World Bank official rate)
            fx.exchange_rate as naira_per_usd,
            allocation.source_file
        from allocation
        left join fx on allocation.disbursement_date = fx.date
    )

select
    *,
    -- Same amounts in US dollars. Blank (not 0) if the month has no exchange rate yet.
    statutory_allocation / naira_per_usd as statutory_allocation_usd,
    oil_derivation / naira_per_usd as oil_derivation_usd,
    exchange_gain_difference / naira_per_usd as exchange_gain_difference_usd,
    total_ecology_fund / naira_per_usd as total_ecology_fund_usd,
    gross_vat_allocation / naira_per_usd as gross_vat_allocation_usd,
    others_income / naira_per_usd as others_income_usd,
    total_gross_amount / naira_per_usd as total_gross_amount_usd,
    external_debt / naira_per_usd as external_debt_usd,
    contractual_obligation_ispo / naira_per_usd as contractual_obligation_ispo_usd,
    other_deductions_note / naira_per_usd as other_deductions_note_usd,
    transfer_nddc_hyppadec / naira_per_usd as transfer_nddc_hyppadec_usd,
    deduction_misc / naira_per_usd as deduction_misc_usd,
    other_deduction / naira_per_usd as other_deduction_usd,
    total_deductions / naira_per_usd as total_deductions_usd,
    net_amount_after_deductions / naira_per_usd as net_amount_after_deductions_usd
from joined
