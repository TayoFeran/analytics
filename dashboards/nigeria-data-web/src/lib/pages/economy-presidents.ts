// Presidents: inflation, the naira and growth for each term, within the selected years.

import { type RankRow, rankBars } from "../charts";
import { type Administration, type EconomyMonth, type EconomyYear, presidentColour, yearOf } from "../economy";
import { esc, monthKey, monthLabel, naira, percent, rate } from "../format";
import { banner, COLOURS, explainPanel, hl } from "../ui";

export interface PresidentsData {
	months: EconomyMonth[];
	years: EconomyYear[];
	admins: Administration[];
	exportedAt: string;
}

export interface YearRange {
	from: number;
	to: number;
}

interface Measure {
	value: number | null;
	/** Periods with data / periods of the term inside the range. */
	have: number;
	need: number;
	first?: string;
	last?: string;
	detail: string;
}

export interface Term {
	admin: Administration;
	label: string;
	inflation: Measure;
	naira: Measure;
	growth: Measure;
}

export type PresidentChart = "inflation" | "naira" | "growth";

const termYears = (a: Administration) => `${a.term_start.slice(0, 4)}–${a.term_end ? a.term_end.slice(0, 4) : "now"}`;

/** Months of a term that fall in the range: from its first disbursement month to the next term's. */
function termMonths(d: PresidentsData, a: Administration, r: YearRange): string[] {
	const next = d.admins[d.admins.indexOf(a) + 1];
	const start = monthKey(a.first_disbursement_month);
	const end = next ? monthKey(next.first_disbursement_month) : "9999-12";
	const lastData = monthKey(d.months[d.months.length - 1].month_date);
	const out: string[] = [];
	let y = Number(start.slice(0, 4));
	let m = Number(start.slice(5, 7));
	for (;;) {
		const key = `${y}-${String(m).padStart(2, "0")}`;
		if (key >= end || key > lastData) break;
		if (y >= r.from && y <= r.to) out.push(key);
		m++;
		if (m > 12) {
			m = 1;
			y++;
		}
	}
	return out;
}

export function buildTerms(d: PresidentsData, r: YearRange): Term[] {
	const byMonth = new Map(d.months.map((m) => [monthKey(m.month_date), m]));
	// A source that lags (CPI is often a month behind the exchange rate) isn't a gap in a term:
	// count only months up to where each source currently ends.
	const lastWith = (pick: (m: EconomyMonth) => number | null) => monthKey([...d.months].reverse().find((m) => pick(m) != null)!.month_date);
	const lastInflation = lastWith((m) => m.inflation_yoy);
	const lastFx = lastWith((m) => m.naira_per_usd);
	return d.admins
		.map((a) => {
			const months = termMonths(d, a, r);
			const rows = months.map((k) => byMonth.get(k)).filter((m): m is EconomyMonth => Boolean(m));
			// Inflation: simple average of the term's months with data
			const infl = rows.filter((m) => m.inflation_yoy != null);
			const inflation: Measure = {
				value: infl.length ? infl.reduce((s, m) => s + m.inflation_yoy!, 0) / infl.length : null,
				have: infl.length,
				need: months.filter((k) => k <= lastInflation).length,
				first: infl[0] ? monthKey(infl[0].month_date) : undefined,
				last: infl.at(-1) ? monthKey(infl.at(-1)!.month_date) : undefined,
				detail: "average inflation a month",
			};
			// Naira: from the rate inherited (the month before the first) to the rate left
			const fx = rows.filter((m) => m.naira_per_usd != null);
			const firstFx = fx[0];
			const before = firstFx ? d.months[d.months.indexOf(firstFx) - 1] : undefined;
			const found = before?.naira_per_usd ?? firstFx?.naira_per_usd ?? null;
			const left = fx.at(-1)?.naira_per_usd ?? null;
			const nairaM: Measure = {
				value: found && left ? found / left - 1 : null,
				have: fx.length,
				need: months.filter((k) => k <= lastFx).length,
				first: firstFx ? monthKey(firstFx.month_date) : undefined,
				last: fx.at(-1) ? monthKey(fx.at(-1)!.month_date) : undefined,
				detail: found && left ? `${naira(found)} → ${naira(left)} per $` : "",
			};
			// Growth: simple average of the term's years (a year belongs to the president in office on 1 July)
			const yrs = d.years.filter((y) => y.president === a.president && y.year >= r.from && y.year <= r.to);
			const withGrowth = yrs.filter((y) => y.real_gdp_growth != null);
			const growth: Measure = {
				value: withGrowth.length ? withGrowth.reduce((s, y) => s + y.real_gdp_growth!, 0) / withGrowth.length : null,
				have: withGrowth.length,
				need: yrs.length,
				first: withGrowth[0] ? String(withGrowth[0].year) : undefined,
				last: withGrowth.at(-1) ? String(withGrowth.at(-1)!.year) : undefined,
				detail: "average real growth a year",
			};
			return { admin: a, label: termYears(a), inflation, naira: nairaM, growth };
		})
		.filter((t) => t.inflation.need + t.growth.need > 0);
}

const FORMAT: Record<PresidentChart, (v: number) => string> = {
	inflation: (v) => rate(v),
	naira: (v) => `${v > 0 ? "+" : ""}${percent(v)}`,
	growth: (v) => rate(v),
};

const signColour = (v: number) => (v > 0 ? COLOURS.better : v < 0 ? COLOURS.worse : COLOURS.equal);

export function renderPresidentBars(terms: Term[], chart: PresidentChart): string {
	const rows: RankRow[] = terms
		.filter((t) => t[chart].value != null)
		.map((t) => {
			const m = t[chart];
			return {
				label: t.admin.president,
				sub: t.label,
				value: m.value!,
				display: FORMAT[chart](m.value!),
				// Inflation is always above zero, so it keeps the president colours; the others show the sign
				colour: chart === "inflation" ? presidentColour(t.admin.president) : signColour(m.value!),
				hatched: m.have < m.need,
				key: t.admin.president,
			};
		});
	return rankBars(rows, { aria: { inflation: "Average inflation by president", naira: "Change in the naira's value by president", growth: "Average real growth by president" }[chart] });
}

function period(m: Measure, chart: PresidentChart): string {
	if (!m.first) return "no data";
	const f = (k: string) => (chart === "growth" ? k : monthLabel(k, "medium"));
	return m.first === m.last ? f(m.first) : `${f(m.first)} – ${f(m.last!)}`;
}

export function presidentTooltip(terms: Term[], key: string, chart: PresidentChart): string | null {
	const t = terms.find((x) => x.admin.president === key);
	if (!t || t[chart].value == null) return null;
	const ranked = terms.filter((x) => x[chart].value != null).sort((a, b) => (chart === "inflation" ? a[chart].value! - b[chart].value! : b[chart].value! - a[chart].value!));
	const rank = ranked.indexOf(t) + 1;
	const m = t[chart];
	return `<div class="m">${esc(t.admin.full_name)} <span class="muted" style="font-weight:500">· ${t.label}</span></div>
		<div class="r"><span>${chart === "naira" ? "Naira's value" : m.detail}</span><b>${FORMAT[chart](m.value!)}</b><span></span></div>
		${chart === "naira" ? `<div class="r"><span>Rate</span><b>${m.detail}</b><span></span></div>` : ""}
		<div class="r"><span>Rank</span><b>#${rank} of ${ranked.length}</b><span></span></div>
		<div class="r"><span>Data</span><b>${period(m, chart)}</b><span></span></div>
		<div class="vs">${m.have < m.need ? `Partial: ${m.have} of ${m.need} ${chart === "growth" ? "years" : "months"} have data` : "Full term in range"}${chart === "inflation" ? " · #1 = lowest inflation" : ""}</div>`;
}

export function renderCoverage(terms: Term[]): string {
	const chips: string[] = [];
	for (const t of terms) {
		for (const [chart, name] of [["inflation", "inflation"], ["naira", "naira"], ["growth", "growth"]] as const) {
			const m = t[chart];
			if (m.need && m.have < m.need) {
				chips.push(`<li><b>${esc(t.admin.president)}</b> · ${name}: ${m.have ? `${m.have} of ${m.need} ${chart === "growth" ? "years" : "months"} (${period(m, chart)})` : "no data yet"}</li>`);
			}
		}
	}
	if (!chips.length) return "";
	return `<p class="note-line">Partial terms are hatched. The data doesn't yet cover every month of these terms:</p><ul class="chips">${chips.join("")}</ul>`;
}

const DEFINITIONS: Record<PresidentChart, string> = {
	inflation: `<p>The average of each month's inflation (how much prices rose over the previous 12 months) during the term. Lower is better.</p>`,
	naira: `<p>How much the naira's value against the dollar changed during the term: from the rate the president inherited (the month before their first) to the rate they left. −50% means a dollar cost twice as many naira by the end.</p>`,
	growth: `<p>The average of each year's real GDP growth during the term. A year counts for the president in office on 1 July. Growth below about 2.5% (population growth) means less output per person.</p>`,
};

export function renderPresidentExplain(terms: Term[], chart: PresidentChart): string {
	const withData = terms.filter((t) => t[chart].value != null);
	if (!withData.length) return explainPanel(DEFINITIONS[chart], `<p class="muted">No president with data in the selected years.</p>`);
	const best = [...withData].sort((a, b) => (chart === "inflation" ? a[chart].value! - b[chart].value! : b[chart].value! - a[chart].value!))[0];
	const worst = withData.filter((t) => t !== best).sort((a, b) => (chart === "inflation" ? b[chart].value! - a[chart].value! : a[chart].value! - b[chart].value!))[0];
	const says = `<p>Best: ${hl(esc(best.admin.president))}, ${FORMAT[chart](best[chart].value!)}${best[chart].have < best[chart].need ? " (partial term)" : ""}.</p>${worst ? `<p>Worst: ${hl(esc(worst.admin.president))}, ${FORMAT[chart](worst[chart].value!)}${worst[chart].have < worst[chart].need ? " (partial term)" : ""}.</p>` : ""}<p>Conditions differ between terms (oil prices, global shocks), so these compare outcomes, not blame.</p>`;
	return explainPanel(DEFINITIONS[chart], says);
}

export function renderPresidentsInsight(terms: Term[]): string {
	const pick = (chart: PresidentChart, dir: 1 | -1) =>
		terms.filter((t) => t[chart].value != null).sort((a, b) => dir * (a[chart].value! - b[chart].value!))[0];
	const lowInfl = pick("inflation", 1);
	const highInfl = pick("inflation", -1);
	const fall = pick("naira", 1);
	const fast = pick("growth", -1);
	return banner("By president", [
		highInfl && lowInfl && highInfl !== lowInfl
			? `Average inflation was highest under ${esc(highInfl.admin.president)} (${hl(rate(highInfl.inflation.value))}) and lowest under ${esc(lowInfl.admin.president)} (${hl(rate(lowInfl.inflation.value))}).`
			: "",
		fall && fall.naira.value! < 0 ? `The naira lost most under ${esc(fall.admin.president)}: ${hl(percent(Math.abs(fall.naira.value!)))} of its value.` : "",
		fast ? `Growth was fastest under ${esc(fast.admin.president)}, ${hl(rate(fast.growth.value))} a year on average.` : "",
	]);
}

export const yearsOfData = (d: PresidentsData): number[] => {
	const first = Math.min(yearOf(d.admins[0].first_disbursement_month), ...d.years.map((y) => y.year).filter((y) => y >= 1999));
	const last = Math.max(yearOf(d.months.at(-1)!.month_date), d.years.at(-1)!.year);
	return Array.from({ length: last - first + 1 }, (_, i) => first + i);
};
