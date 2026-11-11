// FAAC Revenue mix and Deductions: the lines that make up gross and deductions, over time,
// by state, and in a table. One module because the two pages mirror each other.

import { lineChart, type RankRow, rankBars, stackedArea } from "../charts";
import {
	cubeValue,
	type DeductionKey,
	DEDUCTION_LINES,
	type FaacCube,
	type FaacFilters,
	type NationalMonth,
	type RevenueKey,
	REVENUE_LINES,
	toCurrency,
	ZONE_COLOURS,
} from "../faac";
import { esc, money, monthKey, monthLabel, percent } from "../format";
import { badge, banner, bannerTone, change, hl, legend, zeroAwareChange } from "../ui";

export interface LinesData {
	months: NationalMonth[];
	cube: FaacCube;
	exportedAt: string;
}

type Line = { key: RevenueKey | DeductionKey; name: string; short: string; colour: string };

export interface LinesView {
	f: FaacFilters;
	index: number;
	current: NationalMonth;
	previous?: NationalMonth;
	range: NationalMonth[];
	rangeStart: number;
}

export function buildLinesView(d: LinesData, f: FaacFilters): LinesView {
	const keys = d.months.map((m) => monthKey(m.disbursement_date));
	let index = keys.indexOf(f.to);
	if (index < 0) index = keys.length - 1;
	const rangeStart = Math.max(0, keys.findIndex((k) => k >= f.from));
	return {
		f,
		index,
		current: d.months[index],
		previous: index > 0 ? d.months[index - 1] : undefined,
		range: d.months.slice(rangeStart, index + 1),
		rangeStart,
	};
}

const cur = (v: LinesView, naira: number, m: NationalMonth) => toCurrency(naira, m.naira_per_usd, v.f.currency);
const fmt0 = (v: LinesView) => (x: number) => money(x, v.f.currency, 0);
const ticks = (v: LinesView) => v.range.map((m) => monthLabel(monthKey(m.disbursement_date), "tick"));

/** Tooltip for month i of the range: every line with amount, share and change. */
export function linesTooltip(d: LinesData, v: LinesView, i: number, kind: "revenue" | "deductions"): string | null {
	const m = v.range[i];
	if (!m) return null;
	const at = v.rangeStart + i;
	const prev = at > 0 ? d.months[at - 1] : undefined;
	const lines: readonly Line[] = kind === "revenue" ? REVENUE_LINES : DEDUCTION_LINES;
	const totalKey = kind === "revenue" ? "gross" : "deductions";
	const upGood = kind === "revenue";
	const total = m[totalKey];
	const rows = lines
		.map((l) => {
			const now = cur(v, m[l.key], m);
			const before = prev ? cur(v, prev[l.key], prev) : undefined;
			return `<div class="r4"><span><i class="sw" style="background:${l.colour}"></i>${esc(l.short)}</span><b>${money(now, v.f.currency)}</b><span class="sh">${total ? percent(m[l.key] / total, 0) : ""}</span>${badge(zeroAwareChange(now, before, upGood))}</div>`;
		})
		.join("");
	const totalNow = cur(v, total, m);
	const totalPrev = prev ? cur(v, prev[totalKey], prev) : undefined;
	return `<div class="m">${monthLabel(monthKey(m.disbursement_date), "long")}</div>${rows}
		<div class="r4 tot"><span>${kind === "revenue" ? "Gross" : "All deductions"}</span><b>${money(totalNow, v.f.currency)}</b><span class="sh"></span>${badge(change(totalNow, totalPrev, upGood))}</div>
		<div class="vs">${prev ? `Change vs ${monthLabel(monthKey(prev.disbursement_date), "long")}` : "No earlier month"}</div>`;
}

// --- Revenue mix --------------------------------------------------------------------------

export function renderRevenueArea(v: LinesView, width: number): string {
	return stackedArea({
		width,
		labels: ticks(v),
		series: REVENUE_LINES.map((l) => ({ name: l.name, colour: l.colour, values: v.range.map((m) => cur(v, m[l.key], m)) })),
		format: fmt0(v),
		aria: `Stacked area of the six revenue lines that make up gross FAAC allocation, ${ticks(v)[0]} to ${ticks(v).at(-1)}.`,
	});
}

export const revenueLegend = () => legend(REVENUE_LINES.map((l) => ({ name: l.name, colour: l.colour })));

/** Ranked bars by state for one line in the To month, coloured by zone. */
function stateBars(d: LinesData, v: LinesView, key: RevenueKey | DeductionKey, aria: string, limit = 40): string {
	const c = d.cube;
	const m = v.index;
	const rows: RankRow[] = c.states
		.map((name, s) => ({ name, zone: c.zones[s], value: toCurrency(cubeValue(c, key, m, s), c.rate[m], v.f.currency) }))
		.filter((r) => r.value > 0)
		.sort((a, b) => b.value - a.value)
		.map((r) => ({ label: r.name, sub: r.zone, subColour: ZONE_COLOURS[r.zone], value: r.value, display: money(r.value, v.f.currency), colour: ZONE_COLOURS[r.zone], key: r.name }));
	if (!rows.length) return `<p class="muted">No state had any in ${monthLabel(c.months[m], "long")}.</p>`;
	const more = rows.length > limit ? `<p class="note-line">Top ${limit} of ${rows.length} states · the table below has every state</p>` : "";
	return rankBars(rows.slice(0, limit), { aria }) + more;
}

export function stateLineTooltip(d: LinesData, v: LinesView, key: RevenueKey | DeductionKey, state: string, label: string): string | null {
	const c = d.cube;
	const s = c.states.indexOf(state);
	if (s < 0) return null;
	const m = v.index;
	const value = (month: number, st: number) => toCurrency(cubeValue(c, key, month, st), c.rate[month], v.f.currency);
	const now = value(m, s);
	const total = c.states.reduce((a, _, i) => a + value(m, i), 0);
	const before = m > 0 ? value(m - 1, s) : undefined;
	const upGood = REVENUE_LINES.some((l) => l.key === key);
	return `<div class="m">${esc(state)} <span class="muted" style="font-weight:500">· ${esc(c.zones[s])}</span></div>
		<div class="r"><span>${esc(label)}</span><b>${money(now, v.f.currency)}</b>${badge(zeroAwareChange(now, before, upGood))}</div>
		<div class="r"><span>Share of all states</span><b>${percent(now / (total || 1))}</b><span></span></div>
		<div class="vs">${monthLabel(c.months[m], "long")} · change vs the previous month</div>`;
}

export const renderOilByState = (d: LinesData, v: LinesView) => stateBars(d, v, "oil_derivation", "Oil derivation by state");

function linesTable(v: LinesView, lines: readonly Line[], total: "gross" | "deductions"): string {
	const m = v.current;
	const p = v.previous;
	const upGood = total === "gross";
	const rows = lines
		.map((l) => {
			const now = cur(v, m[l.key], m);
			const before = p ? cur(v, p[l.key], p) : undefined;
			const share = m[total] ? m[l.key] / m[total] : 0;
			return `<tr><td><i class="sw" style="display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;background:${l.colour}"></i>${esc(l.name)}</td>
				<td>${money(now, v.f.currency)}</td>
				<td><span class="share-bar"><span style="width:${(share * 100).toFixed(1)}%"></span></span>${percent(share)}</td>
				<td>${badge(zeroAwareChange(now, before, upGood))}</td></tr>`;
		})
		.join("");
	const totalNow = cur(v, m[total], m);
	const totalPrev = p ? cur(v, p[total], p) : undefined;
	return `<div class="table-scroll"><table class="data">
		<thead><tr><th>Line</th><th>Amount</th><th>Share of ${total === "gross" ? "gross" : "deductions"}</th><th>vs ${p ? monthLabel(monthKey(p.disbursement_date), "medium") : "previous"}</th></tr></thead>
		<tbody>${rows}</tbody>
		<tfoot><tr><td>${total === "gross" ? "Gross allocation" : "All deductions"}</td><td>${money(totalNow, v.f.currency)}</td><td>100%</td><td>${badge(change(totalNow, totalPrev, upGood))}</td></tr></tfoot>
	</table></div>`;
}

export const renderRevenueTable = (v: LinesView) => linesTable(v, REVENUE_LINES, "gross");

/** The line that moved most since last month, among lines paid in both months. */
function fastestMover(v: LinesView, lines: readonly Line[]): { line: Line; pct: number } | null {
	if (!v.previous) return null;
	let best: { line: Line; pct: number } | null = null;
	for (const l of lines) {
		const now = v.current[l.key];
		const before = v.previous[l.key];
		if (!now || !before) continue;
		const pct = (now - before) / before;
		if (!best || Math.abs(pct) > Math.abs(best.pct)) best = { line: l, pct };
	}
	return best;
}

function topState(d: LinesData, v: LinesView, key: RevenueKey | DeductionKey): { name: string; share: number } | null {
	const c = d.cube;
	const values = c.states.map((name, s) => ({ name, value: cubeValue(c, key, v.index, s) }));
	const total = values.reduce((a, x) => a + x.value, 0);
	const top = values.sort((a, b) => b.value - a.value)[0];
	return total > 0 ? { name: top.name, share: top.value / total } : null;
}

export function renderRevenueInsight(d: LinesData, v: LinesView): string {
	const m = v.current;
	const month = monthLabel(monthKey(m.disbursement_date), "long");
	const biggest = [...REVENUE_LINES].sort((a, b) => m[b.key] - m[a.key])[0];
	const mover = fastestMover(v, REVENUE_LINES);
	const oil = topState(d, v, "oil_derivation");
	const moverText = mover
		? `${esc(mover.line.name)} moved most since ${monthLabel(monthKey(v.previous!.disbursement_date), "name")}, <span class="${bannerTone(change(1 + mover.pct, 1, true))}">${mover.pct > 0 ? "▲" : "▼"} ${percent(Math.abs(mover.pct))}</span>.`
		: "";
	return banner(month, [
		`${esc(biggest.name)} was the biggest source of the states' gross allocation in ${month}, ${hl(percent(m[biggest.key] / m.gross))} of ${hl(money(cur(v, m.gross, m), v.f.currency))}.`,
		moverText,
		oil ? `${esc(oil.name)} received the most oil derivation, ${hl(percent(oil.share))} of it.` : "",
	]);
}

// --- Deductions ----------------------------------------------------------------------------

export function renderDeductionLines(v: LinesView, width: number): string {
	// The two smallest lines over the range are dashed so the bigger ones stand out
	const totals = DEDUCTION_LINES.map((l) => ({ key: l.key, total: v.range.reduce((a, m) => a + m[l.key], 0) }));
	const smallest = new Set([...totals].sort((a, b) => a.total - b.total).slice(0, 2).map((t) => t.key));
	const last = v.range.length - 1;
	return lineChart({
		width,
		labels: ticks(v),
		series: DEDUCTION_LINES.map((l) => ({ name: l.name, colour: l.colour, dashed: smallest.has(l.key), values: v.range.map((m) => cur(v, m[l.key], m)) })),
		format: fmt0(v),
		valueLabel: (s, i) => (i === last && !smallest.has(DEDUCTION_LINES[s].key) ? "above" : null),
		includeZero: true,
		aria: `Line chart of the six deduction lines, ${ticks(v)[0]} to ${ticks(v).at(-1)}.`,
	});
}

export const deductionLegend = () => legend(DEDUCTION_LINES.map((l) => ({ name: l.name, colour: l.colour })));

export const renderExternalDebtByState = (d: LinesData, v: LinesView) => stateBars(d, v, "external_debt", "External debt deducted by state", 12);

export const renderDeductionTotals = (v: LinesView) => linesTable(v, DEDUCTION_LINES, "deductions");

/** States x deduction lines for the To month, with green shading per column. */
export function renderDeductionMatrix(d: LinesData, v: LinesView): string {
	const c = d.cube;
	const m = v.index;
	const value = (key: DeductionKey | "gross", s: number) => toCurrency(cubeValue(c, key, m, s), c.rate[m], v.f.currency);
	const rows = c.states.map((name, s) => {
		const lines = DEDUCTION_LINES.map((l) => value(l.key, s));
		const total = lines.reduce((a, x) => a + x, 0);
		return { name, lines, total, ofGross: total / (value("gross", s) || 1) };
	});
	rows.sort((a, b) => b.total - a.total);
	const maxes = DEDUCTION_LINES.map((_, i) => Math.max(...rows.map((r) => r.lines[i]), 1e-9));
	const maxTotal = Math.max(...rows.map((r) => r.total), 1e-9);
	const shade = (x: number, max: number) => {
		const t = Math.max(0, Math.min(1, x / max));
		return t > 0 ? `background:rgba(14,138,95,${(0.06 + t * 0.5).toFixed(2)})` : "";
	};
	const body = rows
		.map(
			(r) =>
				`<tr><td>${esc(r.name)}</td>${r.lines.map((x, i) => `<td style="${shade(x, maxes[i])}">${x ? money(x, v.f.currency) : "–"}</td>`).join("")}<td style="${shade(r.total, maxTotal)}"><b>${money(r.total, v.f.currency)}</b></td><td>${percent(r.ofGross)}</td></tr>`,
		)
		.join("");
	const head = DEDUCTION_LINES.map((l) => `<th>${esc(l.short)}</th>`).join("");
	return `<div class="table-scroll"><table class="data"><thead><tr><th>State</th>${head}<th>Total</th><th>% of gross</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

export function renderDeductionsInsight(d: LinesData, v: LinesView): string {
	const m = v.current;
	const month = monthLabel(monthKey(m.disbursement_date), "long");
	const total = cur(v, m.deductions, m);
	const prev = v.previous ? cur(v, v.previous.deductions, v.previous) : undefined;
	const ch = change(total, prev, false);
	const biggest = [...DEDUCTION_LINES].sort((a, b) => m[b.key] - m[a.key])[0];
	const debt = topState(d, v, "external_debt");
	return banner(month, [
		`Deductions took ${hl(money(total, v.f.currency))} from the states in ${month}${ch.value !== null ? `, <span class="${bannerTone(ch)}">${ch.text}</span> on ${monthLabel(monthKey(v.previous!.disbursement_date), "name")}` : ""}, ${hl(percent(m.deductions / m.gross))} of gross.`,
		`${esc(biggest.name)} was the biggest line, ${hl(percent(m[biggest.key] / (m.deductions || 1)))} of all deductions.`,
		debt ? `${esc(debt.name)} had the most external debt deducted, ${hl(percent(debt.share))} of the total.` : "",
	]);
}
