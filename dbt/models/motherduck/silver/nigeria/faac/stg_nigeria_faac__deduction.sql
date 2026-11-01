-- One row per state per FAAC disbursement month, from the Deduction sheet.
with
    source as (select * from {{ source("nigeria_faac", "deduction_sheet") }}),

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
            -- Blank cells mean nothing was deducted on that line
            cast(coalesce(external_debt, 0) as decimal(18, 2)) as external_debt,
            cast(
                coalesce(contractual_obligation_ispo, 0) as decimal(18, 2)
            ) as contractual_obligation_ispo,
            cast(coalesce(other_deductions_note, 0) as decimal(18, 2)) as other_deductions_note,
            cast(coalesce(transfer_nddc_hyppadec, 0) as decimal(18, 2)) as transfer_nddc_hyppadec,
            cast(coalesce(deduction_misc, 0) as decimal(18, 2)) as deduction_misc,
            cast(coalesce(other_deduction, 0) as decimal(18, 2)) as other_deduction,
            cast(total_deductions as decimal(18, 2)) as total_deductions_reported,
            cast(net_amount_after_deductions as decimal(18, 2)) as net_amount_reported,
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
    external_debt,
    contractual_obligation_ispo,
    other_deductions_note,
    transfer_nddc_hyppadec,
    deduction_misc,
    other_deduction,
    -- Recomputed for the same reason as the income total: the file's own total is blank
    -- in 23 files, and equals this sum exactly wherever it is filled in.
    external_debt
    + contractual_obligation_ispo
    + other_deductions_note
    + transfer_nddc_hyppadec
    + deduction_misc
    + other_deduction as total_deductions,
    total_deductions_reported,
    -- Blank in the same 23 files; gold derives it from the income sheet when missing
    net_amount_reported,
    disbursement_date,
    year,
    month_number,
    strftime(disbursement_date, '%B') as month_name,
    source_file,
    extracted_at
from cleaned
