// FAAC Compare: two sides (administrations, states, zones or local government councils)
// line by line, as a butterfly. Councils' data is loaded per state when chosen, so the page
// doesn't carry all 774.

import {
	cubeSum,
	type Currency,
	DEDUCTION_LINES,
	type FaacCube,
	type LineKey,
	monthsBetween,
	REVENUE_LINES,
	ZONES,
} from "../faac";
import { esc, money, monthLabel, percent } from "../format";
import { fmt, LGA_DEDUCTION, LGA_REVENUE, type LgaStateData, lgaSum } from "./faac-lgas";
import { badge, banner, bannerTone, change, COLOURS, hl } from "../ui";

export interface CompareData {
	cube: FaacCube;
	presidents: string[];
	/** Councils by state, for the council pickers; their figures load from /data/lgas/<slug>.json. */
	lgaStates: { state: string; slug: string; councils: string[] }[];
	exportedAt: string;
}

/** Packed council data of the states loaded so far, by state name. */
export type LgaLoaded = Record<string, LgaStateData>;

export type CompareBy = "admin" | "state" | "zone" | "lga";
export type Basis = "total" | "monthly" | "perstate";

export interface CompareFilters {
	by: CompareBy;
	a: string;
	b: string;
	basis: Basis;
	from: string;
	to: string;
	currency: Currency;
}

export const BASIS_LABEL: Record<Basis, string> = {
	total: "Total",
	monthly: "Monthly average",
	perstate: "Per state per month",
};

export function choices(d: CompareData, by: CompareBy): string[] {
	if (by === "admin") return d.presidents;
	if (by === "zone") return ZONES;
	if (by === "lga") return d.lgaStates.flatMap((s) => s.councils.map((_, i) => `${s.state}|${i}`));
	return d.cube.states;
}

/** A side's name: a council is "Nassarawa (Kano)", the value being "Kano|<council index>". */
export function choiceLabel(d: CompareData, by: CompareBy, value: string): string {
	if (by !== "lga") return value;
	const [state, i] = value.split("|");
	const council = d.lgaStates.find((s) => s.state === state)?.councils[Number(i)];
	return council ? `${council} (${state})` : value;
}

/** Dropdown options, councils sorted by state then name. */
export function choiceOptions(d: CompareData, by: CompareBy): { value: string; label: string }[] {
	const list = choices(d, by).map((value) => ({ value, label: esc(choiceLabel(d, by, value)) }));
	if (by !== "lga") return list;
	return list.sort((a, b) => {
		const [sa] = a.value.split("|");
		const [sb] = b.value.split("|");
		return sa === sb ? a.label.localeCompare(b.label) : sa.localeCompare(sb);
	});
}

const councilValue = (d: CompareData, state: string, council: string) => {
	const i = d.lgaStates.find((s) => s.state === state)?.councils.indexOf(council) ?? -1;
	return `${state}|${Math.max(i, 0)}`;
};

export function defaultSides(d: CompareData, by: CompareBy): [string, string] {
	if (by === "admin") return [d.presidents[0], d.presidents[d.presidents.length - 1]];
	if (by === "zone") return ["North West", "South South"];
	if (by === "lga") return [councilValue(d, "Lagos", "Alimosho"), councilValue(d, "Kano", "Nassarawa")];
	return ["Lagos", "Kano"];
}

export function defaultCompare(d: CompareData): CompareFilters {
	const [a, b] = defaultSides(d, "admin");
	const m = d.cube.months;
	return { by: "admin", a, b, basis: "monthly", from: m[0], to: m[m.length - 1], currency: "NGN" };
}

interface Side {
	name: string;
	months: number[];
	states: number[];
	values: Record<string, number>;
	/** A council whose state's data hasn't loaded yet. */
	loading?: boolean;
}

function councilSide(d: CompareData, f: CompareFilters, value: string, lga: LgaLoaded): Side {
	const name = choiceLabel(d, "lga", value);
	const [state, i] = value.split("|");
	const data = lga[state];
	const keys = [...LGA_REVENUE.map((l) => l.key), ...LGA_DEDUCTION.map((l) => l.key), "gross", "deductions", "net"] as const;
	if (!data) return { name, months: [], states: [], values: {}, loading: true };
	const months = data.months.flatMap((k, m) => (data.has[m] && k >= f.from && k <= f.to ? [m] : []));
	const divisor = f.basis === "total" ? 1 : months.length;
	const values: Record<string, number> = {};
	for (const k of keys) values[k] = divisor ? lgaSum(data, k, months, Number(i), f.currency) / divisor : Number.NaN;
	return { name, months, states: [], values };
}

function side(d: CompareData, f: CompareFilters, name: string, lga: LgaLoaded): Side {
	if (f.by === "lga") return councilSide(d, f, name, lga);
	const c = d.cube;
	let months = monthsBetween(c.months, f.from, f.to);
	let states = c.states.map((_, i) => i);
	if (f.by === "admin") months = months.filter((m) => c.president[m] === name);
	if (f.by === "state") states = [c.states.indexOf(name)].filter((i) => i >= 0);
	if (f.by === "zone") states = states.filter((s) => c.zones[s] === name);
	const divisor = f.basis === "total" ? 1 : f.basis === "monthly" ? months.length : months.length * states.length;
	const keys: LineKey[] = [...REVENUE_LINES.map((l) => l.key), ...DEDUCTION_LINES.map((l) => l.key), "gross", "deductions", "net"];
	const values = {} as Record<LineKey, number>;
	for (const k of keys) values[k] = divisor ? cubeSum(c, k, months, states, f.currency) / divisor : Number.NaN;
	return { name, months, states, values };
}

export interface CompareView {
	f: CompareFilters;
	a: Side;
	b: Side;
}

export const buildCompareView = (d: CompareData, f: CompareFilters, lga: LgaLoaded = {}): CompareView => ({ f, a: side(d, f, f.a, lga), b: side(d, f, f.b, lga) });

function coverage(d: CompareData, s: Side): string {
	if (s.loading) return "loading…";
	if (!s.months.length) return "no months in range";
	const m = d.cube.months;
	const first = monthLabel(m[s.months[0]], "medium");
	const last = monthLabel(m[s.months[s.months.length - 1]], "medium");
	return `${s.months.length} month${s.months.length === 1 ? "" : "s"}, ${first === last ? first : `${first} – ${last}`}`;
}

export function renderButterfly(d: CompareData, v: CompareView): string {
	const cur = v.f.currency;
	const lga = v.f.by === "lga";
	// Council amounts are millions, so they need more than the states' billions
	const show = (x: number) => (lga ? fmt(x, cur) : money(x, cur));
	const revenue: { key: string; name: string }[] = lga ? [...LGA_REVENUE] : REVENUE_LINES.map((l) => ({ key: l.key, name: l.name }));
	const deductions: { key: string; name: string }[] = lga ? [...LGA_DEDUCTION] : DEDUCTION_LINES.map((l) => ({ key: l.key, name: l.name }));
	const row = (key: string, name: string, upGood: boolean, total = false) => {
		const a = v.a.values[key];
		const b = v.b.values[key];
		const max = Math.max(Math.abs(a) || 0, Math.abs(b) || 0, 1e-9);
		const c = change(b, a, upGood);
		const bColour = c.value === null ? COLOURS.grey : c.colour;
		// A gets the opposite colour: when B did better, A did worse, and the other way round
		const aColour = c.value === null ? COLOURS.grey : c.colour === COLOURS.better ? COLOURS.worse : c.colour === COLOURS.worse ? COLOURS.better : c.colour;
		const w = (x: number) => (Number.isFinite(x) ? ((Math.abs(x) / max) * 100).toFixed(1) : "0");
		return `<div class="row${total ? " total" : ""}">
			<div class="side a"><span class="num">${show(a)}</span><span class="track"><span style="width:${w(a)}%;background:${aColour}"></span></span></div>
			<div class="mid"><b>${esc(name)}</b>${badge(c)}</div>
			<div class="side b"><span class="track"><span style="width:${w(b)}%;background:${bColour}"></span></span><span class="num">${show(b)}</span></div>
		</div>`;
	};
	const head = `<div class="bfly-head"><div class="a">${esc(v.a.name)}<br /><small class="muted">${coverage(d, v.a)}</small></div><div class="mid">${BASIS_LABEL[v.f.basis]}<br />B vs A</div><div>${esc(v.b.name)}<br /><small class="muted">${coverage(d, v.b)}</small></div></div>`;
	return `${head}<div class="bfly">
		<div class="sec income">
			<div class="grp">Income</div>
			${revenue.map((l) => row(l.key, l.name, true)).join("")}
			${row("gross", "Gross allocation", true, true)}
		</div>
		<div class="sec deductions">
			<div class="grp">Deductions</div>
			${deductions.map((l) => row(l.key, l.name, false)).join("")}
			${row("deductions", "All deductions", false, true)}
		</div>
		<div class="sec">
			<div class="grp">Net</div>
			${row("net", "Net received", true, true)}
		</div>
	</div>`;
}

export function renderCompareInsight(v: CompareView): string {
	const cur = v.f.currency;
	const { a, b } = v;
	const basis = BASIS_LABEL[v.f.basis].toLowerCase();
	const lga = v.f.by === "lga";
	const show = (x: number) => (lga ? fmt(x, cur) : money(x, cur));
	if (a.loading || b.loading) return banner("Compare", ["Loading the councils' figures…"]);
	if (!a.months.length || !b.months.length) {
		return banner("Compare", [`${esc(!a.months.length ? a.name : b.name)} has no FAAC months in the selected dates. Widen the date range to compare.`]);
	}
	const net = change(b.values.net, a.values.net, true);
	const ded = change(b.values.deductions, a.values.deductions, false);
	const shareA = a.values.deductions / a.values.gross;
	const shareB = b.values.deductions / b.values.gross;
	return `${banner(`${BASIS_LABEL[v.f.basis]}`, [
		`On a ${basis} basis, ${esc(b.name)} received ${hl(show(b.values.net))} net against ${hl(show(a.values.net))} for ${esc(a.name)}: <span class="${bannerTone(net)}">${net.text}</span>.`,
		`Deductions were <span class="${bannerTone(ded)}">${ded.text}</span>, taking ${hl(percent(shareB))} of gross for ${esc(b.name)} and ${hl(percent(shareA))} for ${esc(a.name)}.`,
		v.f.by === "admin" ? `These are amounts as paid; prices rose a lot between the two, so see FAAC in real terms for a fair comparison.` : "",
	])}<div class="key-row"><span>Left bars: ${esc(a.name)} (A) · right bars: ${esc(b.name)} (B)</span><span>Green = the side that did better for the ${lga ? "councils" : "states"} on that line, red = worse, amber = the same</span></div>`;
}
