-- Nigeria's administrations since 1999, in term order, for the president filters,
-- colours and the Presidents page.
select president, full_name, party, term_start, term_end, first_disbursement_month
from sandbox.nigeria_administration
order by term_start
