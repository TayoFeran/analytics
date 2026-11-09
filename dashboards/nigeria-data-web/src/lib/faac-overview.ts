// FAAC Overview: every calculation and the HTML for each section of the page.
// The page runs this once at build time (so numbers show before any JavaScript loads) and the
// browser runs the same code when a filter changes, so the two can never disagree.

import { type NationalMonth, STATE_CODES, ZONE_COLOURS } from "./faac";
import { type Currency, esc, money, moneyParts, monthKey, monthLabel, naira, percent } from "./format";
import { FAAC_CLOCK, renderFreshness as sharedFreshness } from "./ui";

export type { Currency, NationalMonth };

export interface TopState {
	state: string;
	zone: string;
	net: number;
}

/** What the browser needs: national months plus the top 5 states of every month. */
export interface OverviewData {
	months: NationalMonth[];
	top5: Record<string, TopState[]>;
	exportedAt: string;
}

export interface Filters {
	from: string;
	to: string;
	currency: Currency;
}

export type Top5Style = "shelf" | "list";

// --- Reference lists -------------------------------------------------------------------

type LineKey = keyof NationalMonth;

// Names match the Power BI model (design/tooltips.md); short names fit the card backs.
const REVENUE_LINES: { key: LineKey; name: string; short: string }[] = [
	{ key: "statutory_allocation", name: "Statutory allocation", short: "Statutory" },
	{ key: "vat", name: "VAT", short: "VAT" },
	{ key: "oil_derivation", name: "Oil derivation", short: "Oil derivation" },
	{ key: "exchange_gain", name: "Exchange gain", short: "Exchange gain" },
	{ key: "ecology_fund", name: "Ecology fund", short: "Ecology fund" },
	{ key: "other_income", name: "Other income", short: "Other income" },
];

const DEDUCTION_LINES: { key: LineKey; name: string; short: string }[] = [
	{ key: "external_debt", name: "External debt", short: "External debt" },
	{ key: "contractual_obligation_ispo", name: "Contractual obligations (ISPO)", short: "ISPO" },
	{ key: "transfer_nddc_hyppadec", name: "NDDC / HYPPADEC transfer", short: "NDDC / HYPPADEC" },
	{ key: "other_deductions_note", name: "Other deductions (see note)", short: "Other (note)" },
	{ key: "deduction_misc", name: "Deduction (unlabelled)", short: "Unlabelled" },
	{ key: "other_deduction", name: "Other deductions", short: "Other" },
];

const COLOURS = { better: "#0E8A5F", worse: "#C93C3C", equal: "#C98A00", ink: "#0B3D2E", net: "#E2B53E" };

// --- Freshness ---------------------------------------------------------------------------

export function renderFreshness(data: OverviewData, today: Date): string {
	const latest = monthKey(data.months[data.months.length - 1].disbursement_date);
	return sharedFreshness([FAAC_CLOCK(latest)], data.exportedAt, today);
}

// --- Calculations ------------------------------------------------------------------------

interface Change {
	pct: number | null;
	colour: string;
	arrow: string;
	text: string;
}

/** Change vs the previous value, coloured by whether higher is better. */
function change(current: number, previous: number | undefined, higherIsBetter: boolean): Change {
	if (previous === undefined || !Number.isFinite(previous) || previous === 0 || !Number.isFinite(current)) {
		return { pct: null, colour: "#5E6E67", arrow: "", text: "n/a" };
	}
	const pct = (current - previous) / previous;
	if (Math.abs(pct) < 0.0005) return { pct, colour: COLOURS.equal, arrow: "■", text: "■ 0.0%" };
	const up = pct > 0;
	const good = up === higherIsBetter;
	const arrow = up ? "▲" : "▼";
	return { pct, colour: good ? COLOURS.better : COLOURS.worse, arrow, text: `${arrow} ${percent(Math.abs(pct))}` };
}

const tint = (colour: string) =>
	colour === COLOURS.better ? "#E3F4EC" : colour === COLOURS.worse ? "#FBE7E7" : colour === COLOURS.equal ? "#FBF1DC" : "#EDF2EF";

const badge = (c: Change) => `<span class="badge" style="color:${c.colour};background:${tint(c.colour)}">${c.text}</span>`;

/** Convert a naira amount to the chosen currency at that month's rate. */
function inCurrency(value: number, month: NationalMonth, currency: Currency): number {
	if (currency === "NGN") return value;
	return month.naira_per_usd ? value / month.naira_per_usd : Number.NaN;
}

/**
 * How many months in a row before `index` sit below (or above) the value at `index`.
 * Used for "the highest in 6 months" style wording.
 */
function streak(values: number[], index: number, direction: "highest" | "lowest"): number {
	let count = 0;
	for (let i = index - 1; i >= 0; i--) {
		const beaten = direction === "highest" ? values[i] < values[index] : values[i] > values[index];
		if (!beaten) break;
		count++;
	}
	return count;
}

/** " , the lowest in 6 months" / ", the highest since Jan 2020" / "" (nothing notable). */
function recordPhrase(values: number[], index: number, months: NationalMonth[], noun: string): string {
	for (const direction of ["highest", "lowest"] as const) {
		const run = streak(values, index, direction);
		if (run === index && index >= 6) {
			return `, the ${direction} ${noun} since ${monthLabel(monthKey(months[0].disbursement_date), "medium")}`;
		}
		if (run >= 2) return `, the ${direction} ${noun} in ${run + 1} months`;
	}
	return "";
}

export interface View {
	filters: Filters;
	current: NationalMonth;
	previous?: NationalMonth;
	index: number;
	range: NationalMonth[];
	months: NationalMonth[];
	top5: TopState[];
}

export function buildView(data: OverviewData, filters: Filters): View {
	const months = data.months;
	let index = months.findIndex((m) => monthKey(m.disbursement_date) === filters.to);
	if (index < 0) index = months.length - 1;
	const current = months[index];
	const range = months.filter((m) => {
		const key = monthKey(m.disbursement_date);
		return key >= filters.from && key <= monthKey(current.disbursement_date);
	});
	return {
		filters,
		current,
		// The month before the To month, even when it's outside the selected range
		previous: index > 0 ? months[index - 1] : undefined,
		index,
		range,
		months,
		top5: data.top5[monthKey(current.disbursement_date)] ?? [],
	};
}

// --- KPI flip cards ----------------------------------------------------------------------

function sparkline(values: number[], colour: string): string {
	const clean = values.filter(Number.isFinite);
	if (clean.length < 2) return "";
	const w = 84;
	const h = 28;
	const min = Math.min(...clean);
	const max = Math.max(...clean);
	const points = values.map((v, i) => [
		(i * (w - 6)) / (values.length - 1) + 3,
		h - 3 - ((v - min) / (max - min || 1)) * (h - 8),
	]);
	const last = points[points.length - 1];
	const line = points.map((p) => p.map((n) => n.toFixed(1)).join(",")).join(" ");
	return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${line}" fill="none" stroke="${colour}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="3" fill="${colour}"/></svg>`;
}

function topLines(lines: typeof REVENUE_LINES, month: NationalMonth, total: number, currency: Currency): string {
	const ranked = lines
		.map((line) => ({ ...line, value: month[line.key] as number }))
		.filter((line) => line.value > 0)
		.sort((a, b) => b.value - a.value)
		.slice(0, 3);
	const rows = ranked
		.map(
			(line, i) =>
				`<b>${i + 1}</b><span class="nm" title="${esc(line.name)}">${esc(line.short)}</span><span class="v">${money(inCurrency(line.value, month, currency), currency)}</span><span class="sh">${percent(line.value / total, 0)}</span>`,
		)
		.join("");
	return `<span class="top3">${rows}</span>`;
}

interface Card {
	id: string;
	label: string;
	value: { value: string; unit: string };
	change: Change;
	vs: string;
	spark: number[];
	backTitle: string;
	back: string;
}

function card(c: Card): string {
	return `<button type="button" class="fc" aria-pressed="false" aria-label="${esc(c.label)}: ${esc(c.value.value + c.value.unit)}. Tap for detail.">
		<span class="fc-inner">
			<span class="face front">
				<span class="lbl">${c.label}</span>
				<span class="val">${c.value.value}<small>${c.value.unit}</small></span>
				<span class="chg">${badge(c.change)}<span>${c.vs}</span></span>
				<span class="foot">${sparkline(c.spark, COLOURS.ink)}<span class="hint">Tap for detail ↻</span></span>
			</span>
			<span class="face back">
				<span class="bt">${c.backTitle}</span>
				${c.back}
			</span>
		</span>
	</button>`;
}

export function renderKpis(view: View): string {
	const { current: cur, previous: prev, months, index, filters } = view;
	const currency = filters.currency;
	const vsText = prev ? `vs ${monthLabel(monthKey(prev.disbursement_date), "medium")}` : "no earlier month";
	const last6 = months.slice(Math.max(0, index - 5), index + 1);
	const series = (key: LineKey) => last6.map((m) => inCurrency(m[key] as number, m, currency));
	const amount = (key: LineKey, m: NationalMonth | undefined) =>
		m ? inCurrency(m[key] as number, m, currency) : undefined;

	// Net: how much of every ₦100 allocated the states kept
	const kept = months.map((m) => (m.gross ? (m.net / m.gross) * 100 : Number.NaN));
	const keptNow = Math.round(kept[index]);
	const keptPhrase = recordPhrase(kept, index, months, "share");
	const keptBefore = prev ? Math.round(kept[index - 1]) : undefined;
	const keptCompare =
		keptPhrase ||
		(keptBefore === undefined
			? ""
			: keptBefore === keptNow
				? `, the same as in ${monthLabel(monthKey(prev!.disbursement_date), "name")}`
				: `, ${keptNow > keptBefore ? "up" : "down"} from ₦${keptBefore} in ${monthLabel(monthKey(prev!.disbursement_date), "name")}`);

	// Exchange rate: more naira per dollar = weaker naira = red
	const fxNow = cur.naira_per_usd ?? Number.NaN;
	const fxChange = change(fxNow, prev?.naira_per_usd ?? undefined, false);
	const fxWord = fxChange.pct === null ? "" : Math.abs(fxChange.pct) < 0.0005 ? "unchanged" : fxChange.pct > 0 ? "weaker" : "stronger";
	const otherCurrency: Currency = currency === "NGN" ? "USD" : "NGN";
	const fxBack =
		fxChange.pct === null
			? `<span class="p">No earlier month to compare with.</span>`
			: `<span class="p">The naira ${fxWord === "unchanged" ? "held steady" : `${fxWord === "weaker" ? "weakened" : "strengthened"} ${percent(Math.abs(fxChange.pct))}`} against the dollar. In ${otherCurrency === "USD" ? "dollars" : "naira"}, states received ${money(inCurrency(cur.net, cur, otherCurrency), otherCurrency)} net.</span><span class="tip">Switch to ${otherCurrency === "USD" ? "$" : "₦"} above to see every figure in ${otherCurrency === "USD" ? "dollars" : "naira"}.</span>`;

	const cards: Card[] = [
		{
			id: "gross",
			label: "Gross allocation",
			value: moneyParts(amount("gross", cur)!, currency),
			change: change(amount("gross", cur)!, amount("gross", prev), true),
			vs: vsText,
			spark: series("gross"),
			backTitle: "Top 3 revenue streams",
			back: topLines(REVENUE_LINES, cur, cur.gross, currency),
		},
		{
			id: "deductions",
			label: "Deductions",
			value: moneyParts(amount("deductions", cur)!, currency),
			change: change(amount("deductions", cur)!, amount("deductions", prev), false),
			vs: vsText,
			spark: series("deductions"),
			backTitle: "Top 3 deduction lines",
			back: topLines(DEDUCTION_LINES, cur, cur.deductions, currency),
		},
		{
			id: "net",
			label: "Net received",
			value: moneyParts(amount("net", cur)!, currency),
			change: change(amount("net", cur)!, amount("net", prev), true),
			vs: vsText,
			spark: series("net"),
			backTitle: "What it means",
			back: `<span class="p">States kept ₦${keptNow} of every ₦100 allocated${keptCompare}.</span>`,
		},
		{
			id: "fx",
			label: "Exchange rate",
			value: { value: Number.isFinite(fxNow) ? naira(fxNow) : "–", unit: " / $" },
			change: fxChange,
			vs: fxWord ? `naira ${fxWord}` : vsText,
			spark: last6.map((m) => m.naira_per_usd ?? Number.NaN),
			backTitle: "What it means",
			back: fxBack,
		},
	];
	return cards.map(card).join("");
}

// --- Line chart --------------------------------------------------------------------------

export interface ChartGeometry {
	width: number;
	height: number;
	padL: number;
	padR: number;
	padT: number;
	padB: number;
	step: number;
}

export function chartGeometry(width: number, count: number): ChartGeometry {
	const height = width < 520 ? 250 : 340;
	const padL = 10;
	const padR = width < 520 ? 58 : 70;
	const step = count > 1 ? (width - padL - padR) / (count - 1) : 0;
	return { width, height, padL, padR, padT: 34, padB: 30, step };
}

/** Smooth line through the points (Catmull-Rom), like the mock-up. */
function smoothPath(points: [number, number][]): string {
	if (points.length === 1) return `M${points[0][0]},${points[0][1]}`;
	let d = `M${points[0][0].toFixed(1)},${points[0][1].toFixed(1)}`;
	for (let i = 0; i < points.length - 1; i++) {
		const p0 = points[i - 1] ?? points[i];
		const p1 = points[i];
		const p2 = points[i + 1];
		const p3 = points[i + 2] ?? p2;
		const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
		const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
		d += ` C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
	}
	return d;
}

export function renderLineChart(view: View, width: number): string {
	const { range, filters } = view;
	const currency = filters.currency;
	const g = chartGeometry(width, range.length);
	const gross = range.map((m) => inCurrency(m.gross, m, currency));
	const net = range.map((m) => inCurrency(m.net, m, currency));
	const all = [...gross, ...net].filter(Number.isFinite);
	const lo = Math.min(...all);
	const hi = Math.max(...all);
	const pad = (hi - lo) * 0.08 || hi * 0.1 || 1;
	const min = lo - pad;
	const max = hi + pad;
	const x = (i: number) => (range.length > 1 ? g.padL + i * g.step : width / 2);
	const y = (v: number) => g.padT + ((max - v) / (max - min)) * (g.height - g.padT - g.padB);
	const label = (v: number) => money(v, currency, 0);

	// Label every k-th month and the latest, so labels never overlap
	const every = Math.max(1, Math.ceil((range.length * 72) / (width - g.padL - g.padR)));
	const last = range.length - 1;
	const labelled = (i: number) => i === last || (i % every === 0 && last - i >= every / 2);

	let s = `<path d="${smoothPath(gross.map((v, i) => [x(i), y(v)]))}" fill="none" stroke="${COLOURS.ink}" stroke-width="2.4"/>`;
	s += `<path d="${smoothPath(net.map((v, i) => [x(i), y(v)]))}" fill="none" stroke="${COLOURS.net}" stroke-width="2.4"/>`;
	range.forEach((m, i) => {
		if (!labelled(i)) return;
		const anchor = i === 0 && range.length > 1 ? "start" : "middle";
		const isLast = i === last;
		s += `<circle cx="${x(i)}" cy="${y(gross[i])}" r="${isLast ? 3.5 : 2.5}" fill="${COLOURS.ink}"/>`;
		s += `<circle cx="${x(i)}" cy="${y(net[i])}" r="${isLast ? 3.5 : 2.5}" fill="#C99A1E"/>`;
		if (isLast) {
			s += `<text x="${x(i) + 7}" y="${y(gross[i]) + 4}" class="vl-last" fill="${COLOURS.ink}">${label(gross[i])}</text>`;
			s += `<text x="${x(i) + 7}" y="${y(net[i]) + 4}" class="vl-last" fill="#9A7414">${label(net[i])}</text>`;
		} else {
			s += `<text x="${x(i)}" y="${y(gross[i]) - 8}" text-anchor="${anchor}" class="vl" fill="${COLOURS.ink}">${label(gross[i])}</text>`;
			s += `<text x="${x(i)}" y="${y(net[i]) + 15}" text-anchor="${anchor}" class="vl" fill="#9A7414">${label(net[i])}</text>`;
		}
		const tickAnchor = isLast && range.length > 1 ? "end" : anchor;
		s += `<text x="${isLast && range.length > 1 ? x(i) + 4 : x(i)}" y="${g.height - 8}" text-anchor="${tickAnchor}" class="tick">${monthLabel(monthKey(m.disbursement_date), "tick")}</text>`;
	});
	s += `<line class="guide" x1="0" x2="0" y1="${g.padT - 10}" y2="${g.height - g.padB + 4}" visibility="hidden"/>`;

	const first = monthLabel(monthKey(range[0].disbursement_date), "medium");
	const lastLabel = monthLabel(monthKey(range[last].disbursement_date), "medium");
	const summary = `Line chart of gross and net FAAC allocation from ${first} to ${lastLabel}. In ${lastLabel}, gross was ${label(gross[last])} and net was ${label(net[last])}.`;
	return `<svg class="line-svg" width="${width}" height="${g.height}" viewBox="0 0 ${width} ${g.height}" role="img" aria-label="${esc(summary)}">${s}</svg>`;
}

export function renderLineSub(view: View): string {
	const { range, filters } = view;
	const unit = filters.currency === "USD" ? "US dollars" : "naira";
	const from = monthLabel(monthKey(range[0].disbursement_date), "medium");
	const to = monthLabel(monthKey(range[range.length - 1].disbursement_date), "medium");
	return `All 36 states · ${unit} · ${from === to ? from : `${from} to ${to}`}`;
}

/** Tooltip card for month `i` of the range, with change vs the month before it. */
export function renderLineTooltip(view: View, i: number): string {
	const m = view.range[i];
	const index = view.months.indexOf(m);
	const prev = index > 0 ? view.months[index - 1] : undefined;
	const currency = view.filters.currency;
	const row = (name: string, key: "gross" | "net") => {
		const now = inCurrency(m[key], m, currency);
		const before = prev ? inCurrency(prev[key], prev, currency) : undefined;
		return `<div class="r"><span>${name}</span><b>${money(now, currency)}</b>${badge(change(now, before, true))}</div>`;
	};
	return `<div class="m">${monthLabel(monthKey(m.disbursement_date), "long")}</div>
		${row("Gross", "gross")}${row("Net received", "net")}
		<div class="vs">${prev ? `Change vs ${monthLabel(monthKey(prev.disbursement_date), "long")}` : "No earlier month"}</div>`;
}

// --- Top 5 states ------------------------------------------------------------------------

function zoneGradient(zone: string): string {
	const colour = ZONE_COLOURS[zone] ?? "#5E6E67";
	return `linear-gradient(150deg, color-mix(in srgb, ${colour} 60%, #000), ${colour})`;
}

export function renderTop5(view: View, style: Top5Style): string {
	const { current: cur, top5, filters } = view;
	const currency = filters.currency;
	const month = monthLabel(monthKey(cur.disbursement_date), "long");
	const items = top5.map((s, i) => {
		const amount = moneyParts(inCurrency(s.net, cur, currency), currency);
		const share = percent(s.net / cur.net);
		const code = STATE_CODES[s.state] ?? s.state.slice(0, 2).toUpperCase();
		return { ...s, rank: i + 1, amount, share, code };
	});

	const sub = `<p class="shelfsub">${month} · net received and share of the national net</p>`;
	if (style === "list") {
		const maxNet = Math.max(...top5.map((s) => s.net), 1);
		const rows = items
			.map(
				(s) => `<li>
				<span class="rk">#${s.rank}</span>
				<span class="who"><span class="nm">${esc(s.state)}</span><span class="zn" style="color:${ZONE_COLOURS[s.zone] ?? "#5E6E67"}">${esc(s.zone)}</span></span>
				<span class="amt">${s.amount.value}<small>${s.amount.unit}</small></span>
				<span class="share">${s.share}</span>
				<span class="bar"><span style="width:${((s.net / maxNet) * 100).toFixed(1)}%;background:${ZONE_COLOURS[s.zone] ?? "#5E6E67"}"></span></span>
			</li>`,
			)
			.join("");
		return `${sub}<ol class="top-list">${rows}</ol>`;
	}

	const cards = items
		.map(
			(s) => `<div class="item r${s.rank}" style="background:${zoneGradient(s.zone)}">
				<span class="rk">#${s.rank}</span>
				<span class="code">${s.code}</span>
				<span class="nm">${esc(s.state)}</span>
				<span class="zn">${esc(s.zone)}</span>
				<span class="amt">${s.amount.value}<small>${s.amount.unit}</small></span>
				<span class="share">${s.share} of national net</span>
			</div>`,
		)
		.join("");
	// The rotating cards are decoration for sighted users; screen readers get the ranked list.
	const hidden = items.map((s) => `<li>${esc(s.state)}: ${s.amount.value}${s.amount.unit}, ${s.share}</li>`).join("");
	return `${sub}<div class="stage" aria-hidden="true">${cards}</div><ol class="visually-hidden">${hidden}</ol>`;
}

// --- Revenue mix -------------------------------------------------------------------------

export function renderMix(view: View): string {
	const cur = view.current;
	const segments = [
		{ name: "Statutory allocation", short: "Statutory", value: cur.statutory_allocation, colour: "#0B3D2E", text: "#fff" },
		{ name: "VAT", short: "VAT", value: cur.vat, colour: "#0E8A5F", text: "#fff" },
		{ name: "Oil derivation", short: "Oil", value: cur.oil_derivation, colour: "#E2B53E", text: "#14231D" },
		{ name: "Exchange gain", short: "FX gain", value: cur.exchange_gain, colour: "#93A59D", text: "#14231D" },
		{ name: "Ecology fund + other income", short: "Ecology + other", value: cur.ecology_fund + cur.other_income, colour: "#C8D3CE", text: "#14231D" },
	].map((s) => ({ ...s, share: cur.gross ? s.value / cur.gross : 0 }));

	const bar = segments
		.filter((s) => s.share > 0)
		.map((s) => {
			const label = s.share >= 0.14 ? `${s.short} ${percent(s.share, 0)}` : s.share >= 0.07 ? percent(s.share, 0) : "";
			return `<span style="width:${(s.share * 100).toFixed(2)}%;background:${s.colour};color:${s.text}" title="${esc(s.name)}: ${percent(s.share)}">${label}</span>`;
		})
		.join("");
	const legend = segments
		.map((s) => `<li style="--c:${s.colour}">${esc(s.name)} <b>${percent(s.share, 0)}</b></li>`)
		.join("");
	return `<p class="psub">${monthLabel(monthKey(cur.disbursement_date), "long")} · share of gross allocation by revenue stream</p>
		<div class="mixrow" role="img" aria-label="${esc(segments.map((s) => `${s.name} ${percent(s.share, 0)}`).join(", "))}">${bar}</div>
		<ul class="legend">${legend}</ul>`;
}

// --- Insight banner ----------------------------------------------------------------------

export function renderInsight(view: View): string {
	const { current: cur, previous: prev, months, index, top5, filters } = view;
	const currency = filters.currency;
	const monthLong = monthLabel(monthKey(cur.disbursement_date), "long");
	const netNow = inCurrency(cur.net, cur, currency);

	let first = `States received <span class="hl">${money(netNow, currency)}</span> net in ${monthLong}`;
	if (prev) {
		const c = change(netNow, inCurrency(prev.net, prev, currency), true);
		const cls = c.colour === COLOURS.better ? "up" : c.colour === COLOURS.worse ? "dn" : "eq";
		first += `, <span class="${cls}">${c.text}</span> on ${monthLabel(monthKey(prev.disbursement_date), "name")}`;
	}
	first += ".";

	const dedShare = months.map((m) => (m.gross ? m.deductions / m.gross : Number.NaN));
	const record = recordPhrase(dedShare, index, months, "share");
	const before = prev ? ` (${percent(dedShare[index - 1])} in ${monthLabel(monthKey(prev.disbursement_date), "name")})` : "";
	const second = `Deductions took <span class="hl">${percent(dedShare[index])}</span> of gross${record || before}.`;

	const leader = top5[0];
	const third = leader
		? `${esc(leader.state)} received the most, with <span class="hl">${percent(leader.net / cur.net)}</span> of the national net.`
		: "";

	return `<div class="ico" aria-hidden="true"><svg width="16" height="16" viewBox="0 0 16 16"><path d="M8 1.5a4.5 4.5 0 0 0-2.6 8.2V12h5.2V9.7A4.5 4.5 0 0 0 8 1.5zM6 13.2h4V14.5H6z" fill="#E2B53E"/></svg></div>
		<div class="kick">Key takeaway<br />${monthLong}</div>
		<p class="txt">${first} ${second} ${third}</p>`;
}
