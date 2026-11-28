// The Local governments pages: zones, then a zone's states (/faac/lgas/), then one page per
// state with its councils (/faac/lgas/<state>/). The build packs each state's data with
// packAllStates(); the render functions run at build time and again in the browser. The
// Compare page loads the same packed data per state from /data/lgas/<state>.json.

import { type LineSeries, lineChart, type RankRow, rankBars } from "../charts";
import { bigMoney, type Currency, esc, monthKey, monthLabel, percent } from "../format";
import { latestPeriod, type Period, periodIndexes, periodLabel, periodYears, readPeriod, writePeriod } from "../period";
import { COLOURS } from "../ui";

export { latestPeriod, monthOptions, type Period, periodLabel, periodYears, yearMonths } from "../period";

export interface LgaMonthRow {
	disbursement_date: string;
	state: string;
	lga_sn: number;
	lga: string;
	statutory_allocation: number;
	vat: number;
	exchange_gain: number;
	ecology_fund: number;
	other_income: number;
	deduction: number;
	transfer_nddc_hyppadec: number;
	printed_total_wrong: boolean;
}

export interface LgaReportError {
	disbursement_date: string;
	state: string;
	error: string;
}

export const LGA_REVENUE = [
	{ key: "statutory_allocation", name: "Statutory allocation" },
	{ key: "vat", name: "VAT" },
	{ key: "exchange_gain", name: "Exchange gain" },
	{ key: "ecology_fund", name: "Ecology fund" },
	{ key: "other_income", name: "Other income" },
] as const;

export const LGA_DEDUCTION = [
	{ key: "deduction", name: "Deduction" },
	{ key: "transfer_nddc_hyppadec", name: "NDDC / HYPPADEC transfer" },
] as const;

export type LgaLine = (typeof LGA_REVENUE)[number]["key"] | (typeof LGA_DEDUCTION)[number]["key"];
export type LgaTotal = "gross" | "deductions" | "net";
const LINES: LgaLine[] = [...LGA_REVENUE.map((l) => l.key), ...LGA_DEDUCTION.map((l) => l.key)];

export const ZONES = ["North Central", "North East", "North West", "South East", "South South", "South West"];

// Council amounts are ₦10m to ₦1bn a month and shown to ₦0.1m, so whole thousands lose
// nothing visible and keep each page's download small
const UNIT = 1_000;

/** "Akwa Ibom" -> "akwa-ibom", for the page address. */
export const stateSlug = (state: string): string => state.toLowerCase().replace(/[^a-z]+/g, "-");

/** The reports write naira as "N2.19bn"; the site uses the naira sign. */
export const nairaSign = (text: string): string => text.replace(/\bN(?=\d)/g, "₦");

const byName = (a: string, b: string) => a.localeCompare(b);
export const convert = (naira: number, rate: number | null | undefined, cur: Currency): number => (cur === "NGN" ? naira : rate ? naira / rate : Number.NaN);
export const fmt = (v: number, cur: Currency, decimals = 1): string => bigMoney(v, cur === "USD" ? "$" : "₦", decimals);

// --- One state's councils --------------------------------------------------------------

export interface LgaStateData {
	state: string;
	zone: string;
	months: string[];
	rate: (number | null)[];
	/** Whether the month has LGA figures (September 2021 doesn't). */
	has: boolean[];
	councils: string[];
	unit: number;
	/** Each line's values, indexed [month * councils.length + council]. */
	cols: Record<LgaLine, number[]>;
	/** [month * councils.length + council] where the report's printed total is wrong. */
	wrong: number[];
	/** Month key -> what the report got wrong for this state that month. */
	errors: Record<string, string>;
	exportedAt: string;
}

export function packLgaState(
	state: string,
	zone: string,
	rows: LgaMonthRow[],
	errors: LgaReportError[],
	months: string[],
	rate: (number | null)[],
	exportedAt: string,
): LgaStateData {
	const mine = rows.filter((r) => r.state === state);
	const bySn = new Map<number, string>();
	for (const r of mine) bySn.set(r.lga_sn, r.lga);
	const sns = [...bySn.keys()].sort((a, b) => a - b);
	const councilIndex = new Map(sns.map((sn, i) => [sn, i]));
	const monthIndex = new Map(months.map((m, i) => [m, i]));
	const n = sns.length;
	const cols = Object.fromEntries(LINES.map((k) => [k, new Array(months.length * n).fill(0)])) as Record<LgaLine, number[]>;
	const has = months.map(() => false);
	const wrong: number[] = [];
	for (const r of mine) {
		const m = monthIndex.get(monthKey(r.disbursement_date));
		const c = councilIndex.get(r.lga_sn);
		if (m === undefined || c === undefined) continue;
		has[m] = true;
		for (const k of LINES) cols[k][m * n + c] = Math.round(Number(r[k] ?? 0) / UNIT);
		if (r.printed_total_wrong) wrong.push(m * n + c);
	}
	return {
		state,
		zone,
		months,
		rate,
		has,
		councils: sns.map((sn) => bySn.get(sn)!),
		unit: UNIT,
		cols,
		wrong,
		errors: Object.fromEntries(errors.filter((e) => e.state === state).map((e) => [monthKey(e.disbursement_date), nairaSign(e.error)])),
		exportedAt,
	};
}

let packed: { rows: unknown; data: LgaStateData[] } | undefined;

/** Every state's packed data, A to Z with the FCT last. Packed once per build. */
export function packAllStates(
	rows: LgaMonthRow[],
	errors: LgaReportError[],
	zones: { state: string; zone: string }[],
	national: { disbursement_date: string; naira_per_usd: number | null }[],
	exportedAt: string,
): LgaStateData[] {
	if (packed?.rows === rows) return packed.data;
	const months = national.map((m) => monthKey(m.disbursement_date));
	const rate = national.map((m) => m.naira_per_usd);
	const zoneOf = new Map(zones.map((z) => [z.state, z.zone]));
	const states = [...new Set(rows.map((r) => r.state))].sort((a, b) => (a === "FCT" ? 1 : b === "FCT" ? -1 : byName(a, b)));
	const data = states.map((s) => packLgaState(s, zoneOf.get(s) ?? "", rows, errors, months, rate, exportedAt));
	packed = { rows, data };
	return data;
}

/** Naira for one council and month; gross, deductions and net are worked out from the lines. */
export function lgaValue(d: LgaStateData, line: LgaLine | LgaTotal, m: number, c: number): number {
	const n = d.councils.length;
	if (line === "gross") return LGA_REVENUE.reduce((a, l) => a + d.cols[l.key][m * n + c], 0) * d.unit;
	if (line === "deductions") return LGA_DEDUCTION.reduce((a, l) => a + d.cols[l.key][m * n + c], 0) * d.unit;
	if (line === "net") return lgaValue(d, "gross", m, c) - lgaValue(d, "deductions", m, c);
	return d.cols[line][m * n + c] * d.unit;
}

/** Sum over months, converting each month at its own rate. */
export const lgaSum = (d: LgaStateData, line: LgaLine | LgaTotal, ms: number[], c: number, cur: Currency): number =>
	ms.reduce((a, m) => a + convert(lgaValue(d, line, m, c), d.rate[m], cur), 0);

export interface LgaStateFilters extends Period {
	council: number;
	currency: Currency;
	sort: "name" | "net";
}

/** The council with the most net received in the period (the default selection). */
export function topCouncil(d: LgaStateData, p: Period): number {
	const ms = periodIndexes(d, p);
	let best = 0;
	for (let c = 1; c < d.councils.length; c++) if (lgaSum(d, "net", ms, c, "NGN") > lgaSum(d, "net", ms, best, "NGN")) best = c;
	return best;
}

export function defaultLgaStateFilters(d: LgaStateData): LgaStateFilters {
	const p = latestPeriod(d);
	return { ...p, council: topCouncil(d, p), currency: "NGN", sort: "name" };
}

export function readLgaStateFilters(params: URLSearchParams, d: LgaStateData): LgaStateFilters {
	const p = readPeriod(params, d);
	const asked = d.councils.indexOf(params.get("council") ?? "");
	return {
		...p,
		council: asked >= 0 ? asked : topCouncil(d, p),
		currency: params.get("cur") === "usd" ? "USD" : "NGN",
		sort: params.get("sort") === "net" ? "net" : "name",
	};
}

export function writeLgaStateFilters(f: LgaStateFilters, d: LgaStateData): URLSearchParams {
	const q = new URLSearchParams();
	writePeriod(f, d, q);
	if (f.council !== topCouncil(d, f)) q.set("council", d.councils[f.council]);
	if (f.currency === "USD") q.set("cur", "usd");
	if (f.sort === "net") q.set("sort", "net");
	return q;
}

export function renderLgaRanking(d: LgaStateData, f: LgaStateFilters): string {
	const ms = periodIndexes(d, f);
	const rows: RankRow[] = d.councils
		.map((name, c) => ({ name, c, net: lgaSum(d, "net", ms, c, f.currency) }))
		.sort((a, b) => (f.sort === "name" ? byName(a.name, b.name) : b.net - a.net))
		.map((r, i) => ({
			label: f.sort === "net" ? `${i + 1}. ${r.name}` : r.name,
			value: r.net,
			display: fmt(r.net, f.currency),
			colour: r.c === f.council ? COLOURS.gold : COLOURS.ink,
			key: String(r.c),
		}));
	return rankBars(rows, { clickable: true, aria: `Net received by each council in ${d.state}` });
}

export function lgaRankTooltip(d: LgaStateData, f: LgaStateFilters, key: string): string | null {
	const c = Number(key);
	if (!d.councils[c]) return null;
	const ms = periodIndexes(d, f);
	const v = (line: LgaTotal) => fmt(lgaSum(d, line, ms, c, f.currency), f.currency);
	return `<div class="m">${esc(d.councils[c])}, ${periodLabel(d, f)}</div>
		<div>Gross <b>${v("gross")}</b></div><div>Deductions <b>${v("deductions")}</b></div><div>Net received <b>${v("net")}</b></div>`;
}

export function renderLgaTrend(d: LgaStateData, f: LgaStateFilters, width: number): string {
	const c = f.council;
	const series = (line: LgaTotal, colour: string, dashed = false): LineSeries => ({
		name: line,
		values: d.months.map((_, m) => (d.has[m] ? convert(lgaValue(d, line, m, c), d.rate[m], f.currency) : null)),
		colour,
		dashed,
	});
	return lineChart({
		width,
		labels: d.months.map((k) => monthLabel(k, "tick")),
		series: [series("gross", COLOURS.grey, true), series("net", COLOURS.ink)],
		format: (v) => fmt(v, f.currency),
		axisFormat: (v) => fmt(v, f.currency, 0),
		includeZero: true,
		aria: `Line chart of ${d.councils[c]}'s gross and net FAAC allocation by month, ${monthLabel(d.months[0], "medium")} to ${monthLabel(d.months.at(-1)!, "medium")}.`,
	});
}

export function lgaTrendTooltip(d: LgaStateData, f: LgaStateFilters, key: string): string | null {
	const m = Number(key);
	if (!d.months[m]) return null;
	if (!d.has[m]) return `<div class="m">${monthLabel(d.months[m], "long")}</div><div>No LGA figures this month</div>`;
	const v = (line: LgaTotal) => fmt(convert(lgaValue(d, line, m, f.council), d.rate[m], f.currency), f.currency);
	return `<div class="m">${monthLabel(d.months[m], "long")}</div><div>Gross <b>${v("gross")}</b></div><div>Net received <b>${v("net")}</b></div>`;
}

export function renderLgaLines(d: LgaStateData, f: LgaStateFilters): string {
	const ms = periodIndexes(d, f);
	const c = f.council;
	const sum = (line: LgaLine | LgaTotal) => lgaSum(d, line, ms, c, f.currency);
	const gross = sum("gross");
	const row = (name: string, value: number, cls = "") =>
		`<tr class="${cls}"><td>${esc(name)}</td><td>${fmt(value, f.currency)}</td><td>${gross ? percent(value / gross) : "–"}</td></tr>`;
	const body = [
		...LGA_REVENUE.map((l) => row(l.name, sum(l.key))),
		row("Gross allocation", gross, "sum"),
		...LGA_DEDUCTION.map((l) => row(l.name, 0 - sum(l.key))),
		row("Net received", sum("net"), "sum"),
	].join("");
	const n = d.councils.length;
	const flagged = ms.filter((m) => d.wrong.includes(m * n + c)).map((m) => monthLabel(d.months[m], "medium"));
	const flag = flagged.length
		? `<p class="psub">The report's own Total Allocation for ${esc(d.councils[c])} doesn't match these lines in ${flagged.join(", ")} (see the note above). Net received here is the total of the lines.</p>`
		: "";
	return `<div class="table-scroll"><table class="data"><thead><tr><th>Line</th><th>Amount</th><th>% of gross</th></tr></thead><tbody>${body}</tbody></table></div>${flag}`;
}

/** Report mistakes in the period, for the note banner. Empty when there are none. */
export function renderLgaNote(d: LgaStateData, f: Period): string {
	const found = periodIndexes(d, f)
		.map((m) => d.months[m])
		.filter((k) => d.errors[k]);
	if (!found.length) return "";
	const what = found.map((k) => (f.month ? esc(d.errors[k]) : `${monthLabel(k, "name")}: ${esc(d.errors[k])}`)).join(". ");
	return `<div class="ico" aria-hidden="true" style="color:var(--gold);font-weight:700">!</div>
		<div class="kick">A mistake in<br />the report</div>
		<p class="txt">The OAGF report's LGA table for ${esc(d.state)} has an error${found.length > 1 ? " in these months" : ""}. ${what}. The figures on this page are the report's revenue and deduction lines as printed, added up by us, so a council's net received can differ from the report's printed total.</p>`;
}

// --- Zones and states (the index page) ---------------------------------------------------

export interface LgaIndexData {
	months: string[];
	rate: (number | null)[];
	has: boolean[];
	states: string[];
	zones: string[];
	councils: string[][];
	unit: number;
	/** Net received by all a state's councils, indexed [month * states.length + state]. */
	net: number[];
	/** Council with the most net, as an index into councils[state]: per month, and per year. */
	topMonth: number[];
	topYear: Record<string, number[]>;
	exportedAt: string;
}

export interface LgaIndexFilters extends Period {
	zone: string;
	currency: Currency;
	sort: "name" | "net";
}

export function packLgaIndex(perState: LgaStateData[], exportedAt: string): LgaIndexData {
	const first = perState[0];
	const S = perState.length;
	const net = new Array(first.months.length * S).fill(0);
	const topMonth = new Array(first.months.length * S).fill(0);
	const has = first.months.map((_, m) => perState.some((d) => d.has[m]));
	const topYear: Record<string, number[]> = {};
	for (const year of periodYears({ months: first.months, has })) topYear[year] = perState.map((d) => topCouncil(d, { year, month: "" }));
	perState.forEach((d, s) => {
		first.months.forEach((k, m) => {
			if (!d.has[m]) return;
			let total = 0;
			for (let c = 0; c < d.councils.length; c++) total += lgaValue(d, "net", m, c);
			net[m * S + s] = Math.round(total / UNIT);
			topMonth[m * S + s] = topCouncil(d, { year: k.slice(0, 4), month: k });
		});
	});
	return {
		months: first.months,
		rate: first.rate,
		has,
		states: perState.map((d) => d.state),
		zones: perState.map((d) => d.zone),
		councils: perState.map((d) => d.councils),
		unit: UNIT,
		net,
		topMonth,
		topYear,
		exportedAt,
	};
}

export function defaultLgaIndexFilters(d: LgaIndexData): LgaIndexFilters {
	return { ...latestPeriod(d), zone: "", currency: "NGN", sort: "name" };
}

export function readLgaIndexFilters(params: URLSearchParams, d: LgaIndexData): LgaIndexFilters {
	return {
		...readPeriod(params, d),
		zone: ZONES.includes(params.get("zone") ?? "") ? params.get("zone")! : "",
		currency: params.get("cur") === "usd" ? "USD" : "NGN",
		sort: params.get("sort") === "net" ? "net" : "name",
	};
}

export function writeLgaIndexFilters(f: LgaIndexFilters, d: LgaIndexData, withZone = true): URLSearchParams {
	const q = new URLSearchParams();
	if (withZone && f.zone) q.set("zone", f.zone);
	writePeriod(f, d, q);
	if (f.currency === "USD") q.set("cur", "usd");
	if (f.sort === "net") q.set("sort", "net");
	return q;
}

const withQuery = (path: string, q: URLSearchParams) => (q.toString() ? `${path}?${q}` : path);

/** Breadcrumb for the Local governments levels; the last part is the current page. */
export function lgaCrumb(zone: string, state: string, q: URLSearchParams): string {
	const parts = [`<a href="${withQuery("/faac/lgas/", q)}" data-zone="">All zones</a>`];
	if (zone) {
		const zq = new URLSearchParams(q);
		zq.set("zone", zone);
		parts.push(state ? `<a href="${withQuery("/faac/lgas/", zq)}" data-zone="${esc(zone)}">${esc(zone)}</a>` : `<span>${esc(zone)}</span>`);
	}
	if (state) parts.push(`<span>${esc(state)}</span>`);
	return `<nav class="crumb" aria-label="Local government levels">${parts.join(" › ")}</nav>`;
}

export function renderLgaIndex(d: LgaIndexData, f: LgaIndexFilters): string {
	const ms = periodIndexes(d, f);
	const S = d.states.length;
	const stateNet = (s: number) => ms.reduce((a, m) => a + convert(d.net[m * S + s] * d.unit, d.rate[m], f.currency), 0);
	const states = d.states.map((name, s) => ({ name, s, zone: d.zones[s], net: stateNet(s), councils: d.councils[s].length }));
	const order = <T extends { name: string; net: number }>(rows: T[]) => rows.sort((a, b) => (f.sort === "name" ? byName(a.name, b.name) : b.net - a.net));
	const q = writeLgaIndexFilters(f, d, false);

	if (!f.zone) {
		const zones = ZONES.map((name) => {
			const members = states.filter((s) => s.zone === name);
			return { name, states: members.length, councils: members.reduce((a, s) => a + s.councils, 0), net: members.reduce((a, s) => a + s.net, 0) };
		});
		const all = zones.reduce((a, z) => a + z.net, 0);
		const body = order(zones)
			.map((z) => {
				const zq = new URLSearchParams(q);
				zq.set("zone", z.name);
				return `<tr><td><a href="${withQuery("/faac/lgas/", zq)}" data-zone="${esc(z.name)}">${esc(z.name)}</a></td><td>${z.states}</td><td>${z.councils}</td>
				<td>${fmt(z.net, f.currency)}</td><td>${all ? percent(z.net / all) : "–"}</td></tr>`;
			})
			.join("");
		return `<div class="table-scroll"><table class="data"><thead><tr><th>Zone</th><th>States</th><th>Councils</th><th>Net to councils</th><th>Share of all councils</th></tr></thead>
			<tbody>${body}</tbody><tfoot><tr><td>All zones</td><td>${states.length}</td><td>${states.reduce((a, s) => a + s.councils, 0)}</td><td>${fmt(all, f.currency)}</td><td>100%</td></tr></tfoot></table></div>`;
	}

	const members = states.filter((s) => s.zone === f.zone);
	const zoneNet = members.reduce((a, s) => a + s.net, 0);
	const top = (s: number) => d.councils[s][f.month ? d.topMonth[d.months.indexOf(f.month) * S + s] : d.topYear[f.year][s]];
	const body = order(members)
		.map(
			(s) => `<tr><td><a href="${withQuery(`/faac/lgas/${stateSlug(s.name)}/`, q)}">${esc(s.name)}</a></td><td>${s.councils}</td>
			<td>${fmt(s.net, f.currency)}</td><td>${zoneNet ? percent(s.net / zoneNet) : "–"}</td><td>${esc(top(s.s))}</td></tr>`,
		)
		.join("");
	return `<div class="table-scroll"><table class="data lga-index"><thead><tr><th>State</th><th>Councils</th><th>Net to councils</th><th>Share of the zone</th><th>Largest council</th></tr></thead>
		<tbody>${body}</tbody><tfoot><tr><td>${esc(f.zone)}</td><td>${members.reduce((a, s) => a + s.councils, 0)}</td><td>${fmt(zoneNet, f.currency)}</td><td>100%</td><td></td></tr></tfoot></table></div>`;
}
