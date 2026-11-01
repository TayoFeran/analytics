-- One row per state per FAAC disbursement month: what was deducted from each state's
-- allocation, by deduction line, and the net amount it received.
with
    deduction as (select * from {{ ref("stg_nigeria_faac__deduction") }}),

    income as (select * from {{ ref("stg_nigeria_faac__income") }})

select
    strftime(deduction.disbursement_date, '%Y-%m') || ' ' || deduction.state as state_month,
    deduction.disbursement_date,
    deduction.year,
    deduction.month_number,
    deduction.month_name,
    case
        when deduction.disbursement_date < date '2015-05-01'
        then 'Jonathan'
        when deduction.disbursement_date < date '2023-05-01'
        then 'Buhari'
        else 'Tinubu'
    end as president,
    deduction.state,
    deduction.lg_count,
    deduction.external_debt,
    deduction.contractual_obligation_ispo,
    deduction.other_deductions_note,
    deduction.transfer_nddc_hyppadec,
    deduction.deduction_misc,
    deduction.other_deduction,
    deduction.total_deductions,
    -- The files' own net amount is blank in 23 files. Wherever it is filled in it equals
    -- income total minus total deductions exactly (all 1,872 rows checked), so the same
    -- formula fills the gaps. The Fabric notebook's version of this fallback left out
    -- Statutory Allocation and missed Nasarawa.
    coalesce(
        deduction.net_amount_reported, income.total_gross_amount - deduction.total_deductions
    ) as net_amount_after_deductions,
    deduction.source_file
from deduction
left join
    income
    on deduction.disbursement_date = income.disbursement_date
    and deduction.state = income.state
