// FAAC in real terms: the states' net FAAC as paid, and in today's prices (adjusted by CPI).

import { columnChart } from "../charts";
import { presidentColour } from "../economy";
import { esc, money, monthLabel, percent } from "../format";
import { badge, banner, bannerTone, change, COLOURS, explainPanel, flipCard, hl, presidentRows } from "../ui";

export interface RealRow {
	month: string;
	president: string;
	net: number;
	cpi: number | null;
}

export interface RealData {
	rows: RealRow[];
	exportedAt: string;
	/** The month whose prices "today's prices" means: the latest FAAC month with CPI. */
	base: string;
	baseCpi: number;
}

export type Prices = "paid" | "today";

export interface RealFilters {
	from: number;
	to: number;
	president: string;
	prices: Prices;
}

export interface RealView {
	f: RealFilters;
	rows: (RealRow & { real: number | null; times: number | null })[];
	all: (RealRow & { real: number | null; times: number | null })[];
}

export function buildRealView(d: RealData, f: RealFilters): RealView {
	const all = d.rows.map((r) => ({
		...r,
		real: r.cpi ? (r.net * d.baseCpi) / r.cpi : null,
		times: r.cpi ? d.baseCpi / r.cpi : null,
	}));
	const year = (m: string) => Number(m.slice(0, 4));
	return { f, all, rows: all.filter((r) => year(r.month) >= f.from && year(r.month) <= f.to && (f.president === "All" || r.president === f.president)) };
}

const value = (v: RealView, r: RealView["rows"][number]) => (v.f.prices === "today" ? r.real : r.net);
const other = (v: RealView, r: RealView["rows"][number]) => (v.f.prices === "today" ? r.net : r.real);
const m = (k: string) => monthLabel(k, "medium");

export function renderRealCards(v: RealView, d: RealData): string {
	const first = v.rows[0];
	const last = v.rows[v.rows.length - 1];
	if (!first) return "";
	const paid = change(last.net, first.net, true);
	const real = change(last.real, first.real, true);
	const both = (r: RealView["rows"][number]) =>
		`<span class="p">As paid: <b>${money(r.net, "NGN")}</b></span><span class="p">In ${m(d.base)} prices: <b>${r.real != null ? money(r.real, "NGN") : "–"}</b></span>`;
	return [
		flipCard({
			label: "First month",
			asOf: m(first.month),
			value: { value: money(value(v, first) ?? Number.NaN, "NGN").replace("bn", ""), unit: "bn" },
			change: { value: null, colour: "#5E6E67", text: v.f.prices === "today" ? "today's prices" : "as paid" },
			vs: "",
			backTitle: "Both ways",
			back: both(first),
		}),
		flipCard({
			label: "Latest month",
			asOf: m(last.month),
			value: { value: money(value(v, last) ?? Number.NaN, "NGN").replace("bn", ""), unit: "bn" },
			change: { value: null, colour: "#5E6E67", text: v.f.prices === "today" ? "today's prices" : "as paid" },
			vs: "",
			backTitle: "Both ways",
			back: both(last),
		}),
		flipCard({
			label: "Change as paid",
			value: { value: paid.text.replace(/^[▲▼■] /, ""), unit: "" },
			change: paid,
			vs: `${m(first.month)} → ${m(last.month)}`,
			backTitle: "What it means",
			back: `<span class="p">The naira amount the states received ${paid.value !== null && paid.value >= 0 ? "grew" : "fell"} ${paid.value !== null ? percent(Math.abs(paid.value)) : ""} between the two months, before allowing for price rises.</span>`,
		}),
		flipCard({
			label: "Change in real terms",
			value: { value: real.text.replace(/^[▲▼■] /, ""), unit: "" },
			change: real,
			vs: `${m(first.month)} → ${m(last.month)}`,
			backTitle: "What it means",
			back: `<span class="p">After allowing for price rises, what the states received could buy ${real.value !== null && real.value >= 0 ? `${percent(Math.abs(real.value))} more` : `${percent(Math.abs(real.value ?? 0))} less`} in ${m(last.month)} than in ${m(first.month)}.</span>`,
		}),
	].join("");
}

export function renderRealChart(v: RealView, width: number): string {
	const values = v.rows.map((r) => value(v, r));
	const peak = values.reduce<number>((best, x, i) => (x != null && (best < 0 || x > (values[best] ?? -Infinity)) ? i : best), -1);
	const last = v.rows.length - 1;
	return columnChart({
		width,
		labels: v.rows.map((r) => monthLabel(r.month, "tick")),
		values,
		colours: v.rows.map((r) => presidentColour(r.president)),
		overlay: { values: v.rows.map((r) => other(v, r)), colour: COLOURS.gold, dashed: true },
		format: (x) => money(x, "NGN", 0),
		labelled: (i) => i === 0 || i === last || i === peak,
		aria: `States' net FAAC by month, ${v.f.prices === "today" ? "in today's prices" : "as paid"}, with the other basis as a dashed line`,
	});
}

export function realTooltip(v: RealView, i: number, d: RealData): string | null {
	const r = v.rows[i];
	if (!r) return null;
	const at = v.all.indexOf(r);
	const prev = at > 0 ? v.all[at - 1] : undefined;
	return `<div class="m">${monthLabel(r.month, "long")}</div>
		<div class="r"><span>President</span><b>${esc(r.president)}</b><span></span></div>
		<div class="r"><span>As paid</span><b>${money(r.net, "NGN")}</b>${badge(change(r.net, prev?.net, true))}</div>
		<div class="r"><span>In ${m(d.base)} prices</span><b>${r.real != null ? money(r.real, "NGN") : "–"}</b>${badge(change(r.real, prev?.real, true))}</div>
		<div class="vs">${r.times ? `Prices have risen ${r.times.toFixed(2)} times since then` : "No price index for this month"} · change vs the previous month</div>`;
}

export function renderRealExplain(v: RealView, d: RealData): string {
	const first = v.rows[0];
	const rows = [...new Set(v.rows.map((r) => r.president))].map((p) => {
		const mine = v.rows.filter((r) => r.president === p && r.real != null);
		const avgPaid = mine.reduce((a, r) => a + r.net, 0) / (mine.length || 1);
		const avgReal = mine.reduce((a, r) => a + (r.real ?? 0), 0) / (mine.length || 1);
		return { name: p, colour: presidentColour(p), from: money(avgPaid, "NGN"), to: money(avgReal, "NGN"), note: "a month on average: as paid → in today's prices" };
	});
	const example = first?.real
		? `<p>Example: in ${monthLabel(first.month, "long")} the states received ${hl(money(first.net, "NGN"))}. Prices have risen ${first.times!.toFixed(2)} times since, so that money would be worth about ${hl(money(first.real, "NGN"))} in ${monthLabel(d.base, "long")} prices.</p>`
		: "";
	return explainPanel(
		`<p>"Real terms" means adjusting old amounts for price rises, so months can be compared fairly. We use the consumer price index (CPI): an amount is multiplied by how much prices have risen since its month. "Today's prices" means ${monthLabel(d.base, "long")}, the latest FAAC month.</p>${example}`,
		presidentRows(rows),
	);
}

export function renderRealInsight(v: RealView, d: RealData): string {
	const first = v.rows[0];
	const last = v.rows[v.rows.length - 1];
	if (!first) return banner("FAAC in real terms", ["No months in the selected range."]);
	const paid = change(last.net, first.net, true);
	const real = change(last.real, first.real, true);
	const peak = v.rows.filter((r) => r.real != null).sort((a, b) => b.real! - a.real!)[0];
	return banner(monthLabel(last.month, "long"), [
		`As paid, the states' monthly net FAAC went from ${hl(money(first.net, "NGN"))} in ${m(first.month)} to ${hl(money(last.net, "NGN"))} in ${m(last.month)}: <span class="${bannerTone(paid)}">${paid.text}</span>.`,
		`In ${m(d.base)} prices the change was <span class="${bannerTone(real)}">${real.text}</span>, because prices rose ${first.times ? `${first.times.toFixed(2)} times` : "a lot"} over the period.`,
		peak ? `In real terms the best month was ${hl(monthLabel(peak.month, "long"))}, at ${hl(money(peak.real!, "NGN"))}.` : "",
	]);
}
