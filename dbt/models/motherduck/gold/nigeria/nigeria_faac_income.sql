-- One row per state per FAAC disbursement month: what each state received, by revenue line.
select
    strftime(disbursement_date, '%Y-%m') || ' ' || state as state_month,
    disbursement_date,
    year,
    month_number,
    month_name,
    -- Administration in office in the disbursement month (inaugurations: 29 May 2015, 2023)
    case
        when disbursement_date < date '2015-05-01'
        then 'Jonathan'
        when disbursement_date < date '2023-05-01'
        then 'Buhari'
        else 'Tinubu'
    end as president,
    state,
    lg_count,
    statutory_allocation,
    oil_derivation,
    exchange_gain_difference,
    total_ecology_fund,
    gross_vat_allocation,
    others_income,
    total_gross_amount,
    source_file
from {{ ref("stg_nigeria_faac__income") }}
