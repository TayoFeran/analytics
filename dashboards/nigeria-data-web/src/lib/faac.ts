// FAAC data shared by the FAAC pages: line names, zone colours, the president per month,
// and a compact state x month "cube" that pages send to the browser.

import { type Currency, monthKey } from "./format";

export type { Currency };

export const REVENUE_LINES = [
	{ key: "statutory_allocation", name: "Statutory allocation", short: "Statutory", colour: "#0B3D2E" },
	{ key: "vat", name: "VAT", short: "VAT", colour: "#0E8A5F" },
	{ key: "oil_derivation", name: "Oil derivation", short: "Oil derivation", colour: "#E2B53E" },
	{ key: "exchange_gain", name: "Exchange gain", short: "Exchange gain", colour: "#93A59D" },
	{ key: "ecology_fund", name: "Ecology fund", short: "Ecology fund", colour: "#5FB38E" },
	{ key: "other_income", name: "Other income", short: "Other income", colour: "#C8D3CE" },
] as const;

// Greens and gold (no brown), agreed for the Deductions page
export const DEDUCTION_LINES = [
	{ key: "external_debt", name: "External debt", short: "External debt", colour: "#0B3D2E" },
	{ key: "contractual_obligation_ispo", name: "Contractual obligations (ISPO)", short: "ISPO", colour: "#0E8A5F" },
	{ key: "transfer_nddc_hyppadec", name: "NDDC / HYPPADEC transfer", short: "NDDC / HYPPADEC", colour: "#E2B53E" },
	{ key: "other_deductions_note", name: "Other deductions (see note)", short: "Other (note)", colour: "#5FB38E" },
	{ key: "deduction_misc", name: "Deduction (unlabelled)", short: "Unlabelled", colour: "#93A59D" },
	{ key: "other_deduction", name: "Other deductions", short: "Other", colour: "#B9CCC3" },
] as const;

export type RevenueKey = (typeof REVENUE_LINES)[number]["key"];
export type DeductionKey = (typeof DEDUCTION_LINES)[number]["key"];
export type LineKey = RevenueKey | DeductionKey | "gross" | "deductions" | "net";

// Uniform across the whole dashboard wherever states appear.
export const ZONE_COLOURS: Record<string, string> = {
	"North Central": "#2E9B72",
	"North East": "#D9A21B",
	"North West": "#3A6EA5",
	"South East": "#8E5BB5",
	"South South": "#C8693A",
	"South West": "#0B3D2E",
};
export const ZONES = Object.keys(ZONE_COLOURS);

export const STATE_CODES: Record<string, string> = {
	Abia: "AB", Adamawa: "AD", "Akwa Ibom": "AK", Anambra: "AN", Bauchi: "BA", Bayelsa: "BY",
	Benue: "BE", Borno: "BO", "Cross River": "CR", Delta: "DE", Ebonyi: "EB", Edo: "ED",
	Ekiti: "EK", Enugu: "EN", Gombe: "GO", Imo: "IM", Jigawa: "JI", Kaduna: "KD", Kano: "KN",
	Katsina: "KT", Kebbi: "KE", Kogi: "KO", Kwara: "KW", Lagos: "LA", Nasarawa: "NA", Niger: "NI",
	Ogun: "OG", Ondo: "ON", Osun: "OS", Oyo: "OY", Plateau: "PL", Rivers: "RI", Sokoto: "SO",
	Taraba: "TA", Yobe: "YO", Zamfara: "ZA",
};

export interface NationalMonth {
	disbursement_date: string;
	president: string;
	gross: number;
	deductions: number;
	net: number;
	statutory_allocation: number;
	vat: number;
	oil_derivation: number;
	exchange_gain: number;
	ecology_fund: number;
	other_income: number;
	external_debt: number;
	contractual_obligation_ispo: number;
	transfer_nddc_hyppadec: number;
	other_deductions_note: number;
	deduction_misc: number;
	other_deduction: number;
	naira_per_usd: number | null;
	states: number;
}

export interface StateMonthRow extends Record<string, string | number> {
	disbursement_date: string;
	state: string;
}

/**
 * State x month values for the browser. Amounts are stored as whole units of ₦100,000:
 * the site shows millions and billions to one decimal, so this loses nothing visible and
 * keeps the download small. Index a value with [monthIndex * states.length + stateIndex].
 */
export interface FaacCube {
	months: string[];
	rate: (number | null)[];
	president: string[];
	states: string[];
	zones: string[];
	unit: number;
	cols: Partial<Record<LineKey, number[]>>;
}

const UNIT = 100_000;

export function makeCube(
	national: NationalMonth[],
	stateMonth: StateMonthRow[],
	states: { state: string; zone: string }[],
	fields: LineKey[],
): FaacCube {
	const months = national.map((m) => monthKey(m.disbursement_date));
	const names = states.map((s) => s.state);
	const monthIndex = new Map(months.map((m, i) => [m, i]));
	const stateIndex = new Map(names.map((s, i) => [s, i]));
	const cols: Partial<Record<LineKey, number[]>> = {};
	for (const f of fields) cols[f] = new Array(months.length * names.length).fill(0);
	for (const row of stateMonth) {
		const m = monthIndex.get(monthKey(row.disbursement_date));
		const s = stateIndex.get(row.state);
		if (m === undefined || s === undefined) continue;
		for (const f of fields) cols[f]![m * names.length + s] = Math.round(Number(row[f] ?? 0) / UNIT);
	}
	return {
		months,
		rate: national.map((m) => m.naira_per_usd),
		president: national.map((m) => m.president),
		states: names,
		zones: states.map((s) => s.zone),
		unit: UNIT,
		cols,
	};
}

const REVENUE_KEYS = REVENUE_LINES.map((l) => l.key);
const DEDUCTION_KEYS = DEDUCTION_LINES.map((l) => l.key);

/** Value in naira for one state and month. Gross, deductions and net are derived from their lines when not stored. */
export function cubeValue(c: FaacCube, line: LineKey, m: number, s: number): number {
	const col = c.cols[line];
	if (col) return col[m * c.states.length + s] * c.unit;
	if (line === "gross") return REVENUE_KEYS.reduce((a, k) => a + cubeValue(c, k, m, s), 0);
	if (line === "deductions") return DEDUCTION_KEYS.reduce((a, k) => a + cubeValue(c, k, m, s), 0);
	if (line === "net") return cubeValue(c, "gross", m, s) - cubeValue(c, "deductions", m, s);
	return 0;
}

/** Naira or dollars at the month's own rate. */
export function toCurrency(naira: number, rate: number | null | undefined, currency: Currency): number {
	if (currency === "NGN") return naira;
	return rate ? naira / rate : Number.NaN;
}

/** Sum over months and states, converting each month at its own rate. */
export function cubeSum(c: FaacCube, line: LineKey, months: number[], states: number[], currency: Currency): number {
	let total = 0;
	for (const m of months) {
		let monthTotal = 0;
		for (const s of states) monthTotal += cubeValue(c, line, m, s);
		total += toCurrency(monthTotal, c.rate[m], currency);
	}
	return total;
}

/** Month indexes between from and to (month keys, inclusive). */
export function monthsBetween(months: string[], from: string, to: string): number[] {
	const out: number[] = [];
	months.forEach((m, i) => {
		if (m >= from && m <= to) out.push(i);
	});
	return out;
}

/** The FAAC date-range filters every FAAC page shares. */
export interface FaacFilters {
	from: string;
	to: string;
	currency: Currency;
}

export function defaultFaacFilters(months: string[]): FaacFilters {
	return { from: months[Math.max(0, months.length - 24)], to: months[months.length - 1], currency: "NGN" };
}

export function readFaacFilters(params: URLSearchParams, months: string[]): FaacFilters {
	const d = defaultFaacFilters(months);
	const pick = (v: string | null, fallback: string) => (v && months.includes(v) ? v : fallback);
	const f = { from: pick(params.get("from"), d.from), to: pick(params.get("to"), d.to), currency: (params.get("cur") === "usd" ? "USD" : "NGN") as Currency };
	if (f.from > f.to) f.from = f.to;
	return f;
}

export function writeFaacFilters(f: FaacFilters, months: string[], p = new URLSearchParams()): URLSearchParams {
	const d = defaultFaacFilters(months);
	if (f.from !== d.from) p.set("from", f.from);
	if (f.to !== d.to) p.set("to", f.to);
	if (f.currency === "USD") p.set("cur", "usd");
	return p;
}
