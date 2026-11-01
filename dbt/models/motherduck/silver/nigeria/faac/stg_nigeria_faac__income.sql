-- One row per state per FAAC disbursement month, from the Income sheet.
with
    source as (select * from {{ source("nigeria_faac", "income_sheet") }}),

    cleaned as (
        select
            -- Every sheet spells Nasarawa "NASSARAWA"
            case
                upper(trim(beneficiary))
                when 'NASSARAWA'
                then 'NASARAWA'
                else upper(trim(beneficiary))
            end as state_upper,
            cast(lgs as integer) as lg_count,
            -- Blank cells mean nothing was paid on that line
            cast(coalesce(statutory_allocation, 0) as decimal(18, 2)) as statutory_allocation,
            cast(coalesce(oil_derivation, 0) as decimal(18, 2)) as oil_derivation,
            cast(
                coalesce(exchange_gain_difference, 0) as decimal(18, 2)
            ) as exchange_gain_difference,
            cast(coalesce(total_ecology_fund, 0) as decimal(18, 2)) as total_ecology_fund,
            cast(coalesce(gross_vat_allocation, 0) as decimal(18, 2)) as gross_vat_allocation,
            cast(coalesce(others_income, 0) as decimal(18, 2)) as others_income,
            cast(total_gross_amount as decimal(18, 2)) as total_gross_amount_reported,
            make_date(disbursement_year, disbursement_month, 1) as disbursement_date,
            disbursement_year as year,
            disbursement_month as month_number,
            source_file,
            extracted_at
        from source
    )

select
    case
        when state_upper = 'FCT'
        then 'FCT'
        else
            array_to_string(
                list_transform(
                    string_split(lower(state_upper), ' '), lambda w:upper(w[1]) || w[2:]
                ),
                ' '
            )
    end as state,
    lg_count,
    statutory_allocation,
    oil_derivation,
    exchange_gain_difference,
    total_ecology_fund,
    gross_vat_allocation,
    others_income,
    -- Recomputed: the file's own total is a cached formula, blank in files saved without
    -- recalculating (2020 Jan, 2024 Jun-Dec, 2025, 2026). Where it is filled in, it equals
    -- this sum exactly.
    statutory_allocation
    + oil_derivation
    + exchange_gain_difference
    + total_ecology_fund
    + gross_vat_allocation
    + others_income as total_gross_amount,
    total_gross_amount_reported,
    disbursement_date,
    year,
    month_number,
    strftime(disbursement_date, '%B') as month_name,
    source_file,
    extracted_at
from cleaned
