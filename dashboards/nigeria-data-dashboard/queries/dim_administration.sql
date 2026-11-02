-- Administrations, including ones without FAAC data yet
select
    president,
    full_name,
    party,
    term_start::date as term_start,
    term_end::date as term_end,
    first_disbursement_month::date as first_disbursement_month
from sandbox.nigeria_administration
