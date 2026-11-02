-- One row per state per FAAC disbursement month: what each state was allocated, what was
-- deducted, and the net it received, in naira and in US dollars. The fact table of the
-- Nigeria Data Dashboard's FAAC section.
--
-- Dollar amounts use the official exchange rate of the disbursement month itself, so a
-- total across months is the sum of what each month was worth in dollars at the time.
-- Converting a multi-year naira total at a single rate would misstate it.
with
    income as (select * from {{ ref("nigeria_faac_income") }}),

    deduction as (select * from {{ ref("nigeria_faac_deduction") }}),

    fx as (select date, exchange_rate from {{ ref("nigeria_fx_rate") }}),

    joined as (
        select
            income.state_month,
            income.disbursement_date,
            income.year,
            income.month_number,
            income.month_name,
            income.president,
            income.state,
            income.lg_count,
            income.statutory_allocation,
            income.oil_derivation,
            income.exchange_gain_difference,
            income.total_ecology_fund,
            income.gross_vat_allocation,
            income.others_income,
            income.total_gross_amount,
            deduction.external_debt,
            deduction.contractual_obligation_ispo,
            deduction.other_deductions_note,
            deduction.transfer_nddc_hyppadec,
            deduction.deduction_misc,
            deduction.other_deduction,
            deduction.total_deductions,
            deduction.net_amount_after_deductions,
            -- Naira per US dollar in the disbursement month (World Bank official rate)
            fx.exchange_rate as naira_per_usd,
            income.source_file
        from income
        left join deduction on income.state_month = deduction.state_month
        left join fx on income.disbursement_date = fx.date
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
