-- One row per local government council per FAAC month, from the OAGF reports' LGA table:
-- what each council was allocated by revenue line, what was deducted, and the net.
--
-- The net is computed from the lines, not taken from the report's Total Allocation column:
-- in some months that column is wrong (May 2023 for 18 states, for example). The printed
-- figure is kept beside it, and report_check says whether they agree.
with
    figures as (
        select * from {{ ref("stg_nigeria_faac_oagf__lga_figure") }} where row_type = 'lga'
    ),

    report_errors as (select * from {{ source("nigeria_faac_oagf", "known_report_errors") }}),

    reports as (select * from {{ source("nigeria_faac_oagf", "reports") }}),

    administrations as (select * from {{ ref("nigeria_administration") }}),

    lines as (
        select
            shared_month,
            disbursement_date,
            report_state,
            state,
            lga_sn,
            any_value(lga) as lga,
            {%- for line in [
                "statutory_allocation",
                "exchange_gain_difference",
                "total_ecology_fund",
                "gross_vat_allocation",
                "others_income",
            ] %}
                coalesce(
                    sum(line_amount) filter (where role = 'income' and line = '{{ line }}'), 0
                ) as {{ line }},
            {%- endfor %}
            {%- for line in ["deduction", "transfer_nddc_hyppadec"] %}
                coalesce(
                    sum(line_amount) filter (where role = 'deduction' and line = '{{ line }}'), 0
                ) as {{ line }},
            {%- endfor %}
            sum(line_amount) filter (where role = 'income') as total_gross_amount,
            coalesce(sum(line_amount) filter (where role = 'deduction'), 0) as total_deductions,
            max(amount) filter (where role = 'printed_total') as net_amount_reported
        from figures
        group by shared_month, disbursement_date, report_state, state, lga_sn
    ),

    totals as (
        select *, total_gross_amount - total_deductions as net_amount_after_deductions from lines
    )

select
    totals.shared_month || ' ' || totals.state || ' ' || totals.lga_sn as lga_month,
    totals.disbursement_date,
    year(totals.disbursement_date) as year,
    month(totals.disbursement_date) as month_number,
    strftime(totals.disbursement_date, '%B') as month_name,
    administrations.president,
    totals.state,
    totals.lga_sn,
    totals.lga,
    totals.statutory_allocation,
    totals.exchange_gain_difference,
    totals.total_ecology_fund,
    totals.gross_vat_allocation,
    totals.others_income,
    totals.total_gross_amount,
    totals.deduction,
    totals.transfer_nddc_hyppadec,
    totals.total_deductions,
    totals.net_amount_after_deductions,
    totals.net_amount_reported,
    -- Within N1 of the printed Total Allocation, for rounding in the report. A difference
    -- in a state listed in known_report_errors is the report's mistake; any other
    -- difference fails the accepted_values test, because it means a line is mapped wrong.
    case
        when totals.net_amount_reported is null
        then 'not_printed'
        when abs(totals.net_amount_reported - totals.net_amount_after_deductions) <= 1
        then 'matches'
        when report_errors.error is not null
        then 'report_error'
        else 'differs'
    end as report_check,
    report_errors.error as report_error,
    reports.source_type,
    reports.file_name as source_file
from totals
left join
    report_errors
    on totals.shared_month = report_errors.shared_month
    and totals.report_state = report_errors.state
left join reports on totals.shared_month = reports.shared_month
asof left join
    administrations on totals.disbursement_date >= administrations.first_disbursement_month
