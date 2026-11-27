-- One row per state per FAAC month, from the original OAGF reports: what each state was
-- allocated by revenue line, what was deducted by deduction line, and the net it received.
-- Same lines as the refined workbooks had (#17), which this replaced in #36.
--
-- Totals are computed from the lines, because eight reports are cut off before their
-- totals. Where the report prints them, they're kept beside the computed ones and compared
-- in report_check.
with
    figures as (
        select * from {{ ref("stg_nigeria_faac_oagf__state_figure") }} where row_type = 'state'
    ),

    reports as (select * from {{ source("nigeria_faac_oagf", "reports") }}),

    administrations as (select * from {{ ref("nigeria_administration") }}),

    lines as (
        select
            shared_month,
            disbursement_date,
            state,
            any_value(lgc_count) as lg_count,
            {%- for line in [
                "statutory_allocation",
                "oil_derivation",
                "exchange_gain_difference",
                "total_ecology_fund",
                "gross_vat_allocation",
                "others_income",
            ] %}
                coalesce(
                    sum(amount) filter (where role = 'income' and line = '{{ line }}'), 0
                ) as {{ line }},
            {%- endfor %}
            {%- for line in [
                "external_debt",
                "contractual_obligation_ispo",
                "other_deductions_note",
                "transfer_nddc_hyppadec",
                "deduction_misc",
            ] %}
                coalesce(
                    sum(amount) filter (where role = 'deduction' and line = '{{ line }}'), 0
                ) as {{ line }},
            {%- endfor %}
            sum(amount) filter (where role = 'income') as total_gross_amount,
            coalesce(sum(amount) filter (where role = 'deduction'), 0) as total_deductions,
            max(amount) filter (
                where role = 'printed_total' and line = 'total_gross_amount'
            ) as total_gross_amount_reported,
            max(amount) filter (
                where role = 'printed_total' and line = 'total_net_amount'
            ) as net_amount_reported
        from figures
        group by shared_month, disbursement_date, state
    ),

    totals as (
        select *, total_gross_amount - total_deductions as net_amount_after_deductions from lines
    )

select
    totals.shared_month || ' ' || totals.state as state_month,
    totals.disbursement_date,
    year(totals.disbursement_date) as year,
    month(totals.disbursement_date) as month_number,
    strftime(totals.disbursement_date, '%B') as month_name,
    administrations.president,
    totals.state,
    totals.lg_count,
    totals.statutory_allocation,
    totals.oil_derivation,
    totals.exchange_gain_difference,
    totals.total_ecology_fund,
    totals.gross_vat_allocation,
    totals.others_income,
    totals.total_gross_amount,
    totals.external_debt,
    totals.contractual_obligation_ispo,
    totals.other_deductions_note,
    totals.transfer_nddc_hyppadec,
    totals.deduction_misc,
    totals.total_deductions,
    totals.net_amount_after_deductions,
    totals.total_gross_amount_reported,
    totals.net_amount_reported,
    -- Within N1 of the printed totals, for rounding in the report
    case
        when totals.total_gross_amount_reported is null and totals.net_amount_reported is null
        then 'not_printed'
        when
            abs(
                coalesce(totals.total_gross_amount_reported, totals.total_gross_amount)
                - totals.total_gross_amount
            )
            <= 1
            and abs(
                coalesce(totals.net_amount_reported, totals.net_amount_after_deductions)
                - totals.net_amount_after_deductions
            )
            <= 1
        then 'matches'
        else 'differs'
    end as report_check,
    reports.source_type,
    reports.file_name as source_file
from totals
left join reports on totals.shared_month = reports.shared_month
-- The administration whose first disbursement month is the latest on or before this one
asof left join
    administrations on totals.disbursement_date >= administrations.first_disbursement_month
