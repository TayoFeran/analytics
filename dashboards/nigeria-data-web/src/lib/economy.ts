// Economy data shared by the Economy pages and FAAC in real terms.

export interface EconomyMonth {
	month_date: string;
	president: string | null;
	naira_per_usd: number | null;
	cpi_index: number | null;
	inflation_yoy: number | null;
}

export interface EconomyYear {
	year: number;
	president: string | null;
	gdp_usd: number | null;
	gdp_naira: number | null;
	real_gdp_growth: number | null;
	population: number | null;
	gdp_per_person_usd: number | null;
	gdp_per_person_naira: number | null;
	avg_naira_per_usd: number | null;
}

export interface Administration {
	president: string;
	full_name: string;
	party: string;
	term_start: string;
	term_end: string | null;
	first_disbursement_month: string;
}

// The dashboard's president greens, light to dark in term order; years before 1999 are grey.
export const PRESIDENT_COLOURS: Record<string, string> = {
	Obasanjo: "#B9D9C9",
	"Yar'Adua": "#8FC9AE",
	Jonathan: "#4E9C78",
	Buhari: "#0E6B45",
	Tinubu: "#0F2019",
};
export const NO_PRESIDENT = "#D5DDD9";

export const presidentColour = (p: string | null | undefined): string => (p ? (PRESIDENT_COLOURS[p] ?? NO_PRESIDENT) : NO_PRESIDENT);

/** Population growth used as the reference line on the growth chart (about 2.5% a year). */
export const POPULATION_GROWTH = 0.025;

/** Economy filters: a year range and an optional president. */
export interface EconomyFilters {
	from: number;
	to: number;
	president: string;
}

export function readEconomyFilters(params: URLSearchParams, years: number[], presidents: string[], defaults: EconomyFilters): EconomyFilters {
	const year = (v: string | null, fallback: number) => (v && years.includes(Number(v)) ? Number(v) : fallback);
	const f = {
		from: year(params.get("from"), defaults.from),
		to: year(params.get("to"), defaults.to),
		president: presidents.includes(params.get("president") ?? "") ? (params.get("president") as string) : "All",
	};
	if (f.from > f.to) f.from = f.to;
	return f;
}

export function writeEconomyFilters(f: EconomyFilters, defaults: EconomyFilters, p = new URLSearchParams()): URLSearchParams {
	if (f.from !== defaults.from) p.set("from", String(f.from));
	if (f.to !== defaults.to) p.set("to", String(f.to));
	if (f.president !== "All") p.set("president", f.president);
	return p;
}

export const yearOf = (date: string): number => Number(date.slice(0, 4));
