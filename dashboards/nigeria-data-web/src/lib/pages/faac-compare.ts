// FAAC Compare: two sides (administrations, states or zones) line by line, as a butterfly.

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
import { badge, banner, bannerTone, change, COLOURS, hl } from "../ui";

export interface CompareData {
	cube: FaacCube;
	presidents: string[];
	exportedAt: string;
}

export type CompareBy = "admin" | "state" | "zone";
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
	return d.cube.states;
}

export function defaultSides(d: CompareData, by: CompareBy): [string, string] {
	if (by === "admin") return [d.presidents[0], d.presidents[d.presidents.length - 1]];
	if (by === "zone") return ["North West", "South South"];
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
	values: Record<LineKey, number>;
}

function side(d: CompareData, f: CompareFilters, name: string): Side {
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

export const buildCompareView = (d: CompareData, f: CompareFilters): CompareView => ({ f, a: side(d, f, f.a), b: side(d, f, f.b) });

function coverage(d: CompareData, s: Side): string {
	if (!s.months.length) return "no months in range";
	const m = d.cube.months;
	const first = monthLabel(m[s.months[0]], "medium");
	const last = monthLabel(m[s.months[s.months.length - 1]], "medium");
	return `${s.months.length} month${s.months.length === 1 ? "" : "s"}, ${first === last ? first : `${first} – ${last}`}`;
}

export function renderButterfly(d: CompareData, v: CompareView): string {
	const cur = v.f.currency;
	const row = (key: LineKey, name: string, upGood: boolean, total = false) => {
		const a = v.a.values[key];
		const b = v.b.values[key];
		const max = Math.max(Math.abs(a) || 0, Math.abs(b) || 0, 1e-9);
		const c = change(b, a, upGood);
		const bColour = c.value === null ? COLOURS.grey : c.colour;
		const w = (x: number) => (Number.isFinite(x) ? ((Math.abs(x) / max) * 100).toFixed(1) : "0");
		return `<div class="row${total ? " total" : ""}">
			<div class="side a"><span class="num">${money(a, cur)}</span><span class="track"><span style="width:${w(a)}%;background:#B9C6C0"></span></span></div>
			<div class="mid"><b>${esc(name)}</b>${badge(c)}</div>
			<div class="side b"><span class="track"><span style="width:${w(b)}%;background:${bColour}"></span></span><span class="num">${money(b, cur)}</span></div>
		</div>`;
	};
	const head = `<div class="bfly-head"><div class="a">${esc(v.a.name)}<br /><small class="muted">${coverage(d, v.a)}</small></div><div class="mid">${BASIS_LABEL[v.f.basis]}<br />B vs A</div><div>${esc(v.b.name)}<br /><small class="muted">${coverage(d, v.b)}</small></div></div>`;
	return `${head}<div class="bfly">
		<div class="grp">Income</div>
		${REVENUE_LINES.map((l) => row(l.key, l.name, true)).join("")}
		${row("gross", "Gross allocation", true, true)}
		<div class="grp">Deductions</div>
		${DEDUCTION_LINES.map((l) => row(l.key, l.name, false)).join("")}
		${row("deductions", "All deductions", false, true)}
		<div class="grp">Net</div>
		${row("net", "Net received", true, true)}
	</div>`;
}

export function renderCompareInsight(v: CompareView): string {
	const cur = v.f.currency;
	const { a, b } = v;
	const basis = BASIS_LABEL[v.f.basis].toLowerCase();
	if (!a.months.length || !b.months.length) {
		return banner("Compare", [`${esc(!a.months.length ? a.name : b.name)} has no FAAC months in the selected dates. Widen the date range to compare.`]);
	}
	const net = change(b.values.net, a.values.net, true);
	const ded = change(b.values.deductions, a.values.deductions, false);
	const shareA = a.values.deductions / a.values.gross;
	const shareB = b.values.deductions / b.values.gross;
	return `${banner(`${BASIS_LABEL[v.f.basis]}`, [
		`On a ${basis} basis, ${esc(b.name)} received ${hl(money(b.values.net, cur))} net against ${hl(money(a.values.net, cur))} for ${esc(a.name)}: <span class="${bannerTone(net)}">${net.text}</span>.`,
		`Deductions were <span class="${bannerTone(ded)}">${ded.text}</span>, taking ${hl(percent(shareB))} of gross for ${esc(b.name)} and ${hl(percent(shareA))} for ${esc(a.name)}.`,
		v.f.by === "admin" ? `These are amounts as paid; prices rose a lot between the two, so see FAAC in real terms for a fair comparison.` : "",
	])}<div class="key-row"><span>Grey bars: ${esc(a.name)} (A)</span><span>Coloured bars: ${esc(b.name)} (B) · green = better for the states, red = worse, amber = the same</span></div>`;
}
