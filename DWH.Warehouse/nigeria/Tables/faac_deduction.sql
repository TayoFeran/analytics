CREATE TABLE [nigeria].[faac_deduction] (

	[state] varchar(8000) NULL, 
	[lg_count] bigint NULL, 
	[external_debt] bigint NULL, 
	[contractual_obligation_ispo] bigint NULL, 
	[other_deductions_note] bigint NULL, 
	[other_deduction] bigint NULL, 
	[net_amount_after_deductions] bigint NULL, 
	[year] int NULL, 
	[month_number] int NULL, 
	[month_name] varchar(8000) NULL, 
	[disbursement_date] date NULL, 
	[president] varchar(8000) NULL, 
	[source_file] varchar(8000) NULL, 
	[deduction_misc] bigint NULL, 
	[transfer_nddc_hyppadec] bigint NULL, 
	[total_deductions] bigint NULL
);