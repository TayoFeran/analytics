// Economy Overview: inflation, the naira, growth and GDP per person.

import { lineChart } from "../charts";
import {
	type Administration,
	type EconomyFilters,
	type EconomyMonth,
	type EconomyYear,
	presidentColour,
	POPULATION_GROWTH,
	yearOf,
} from "../economy";
import { bigMoney, esc, monthKey, monthLabel, naira, percent, rate, shiftMonth } from "../format";
import { badge, banner, bannerTone, change, type Clock, CPI_CLOCK, explainPanel, flipCard, GDP_CLOCK, hl, legend, presidentRows } from "../ui";

export interface EconomyData {
	months: EconomyMonth[];
	years: EconomyYear[];
	admins: Administration[];
	exportedAt: string;
}

export function economyClocks(d: EconomyData): Clock[] {
	const cpi = d.months.filter((m) => m.cpi_index != null).at(-1)!;
	const gdp = d.years.filter((y) => y.gdp_usd != null).at(-1)!;
	return [CPI_CLOCK(monthKey(cpi.month_date)), GDP_CLOCK(String(gdp.year))];
}

export const presidentsIn = (rows: { president: string | null }[]) =>
	[...new Set(rows.map((r) => r.president).filter((p): p is string => Boolean(p)))];

export const presidentLegend = (names: string[]) => legend(names.map((n) => ({ name: n, colour: presidentColour(n) })));

export interface OverviewView {
	f: EconomyFilters;
	months: EconomyMonth[];
	years: EconomyYear[];
	all: EconomyMonth[];
	allYears: EconomyYear[];
}

export function buildEconomyView(d: EconomyData, f: EconomyFilters): OverviewView {
	const keep = (year: number, president: string | null) => year >= f.from && year <= f.to && (f.president === "All" || president === f.president);
	return {
		f,
		months: d.months.filter((m) => keep(yearOf(m.month_date), m.president)),
		years: d.years.filter((y) => keep(y.year, y.president)),
		all: d.months,
		allYears: d.years,
	};
}

const lastWith = <T>(rows: T[], pick: (r: T) => number | null) => [...rows].reverse().find((r) => pick(r) != null);
const monthBefore = (all: EconomyMonth[], m: EconomyMonth) => all[all.indexOf(m) - 1];
const monthsAgo = (all: EconomyMonth[], m: EconomyMonth, n: number) =>
	all.find((x) => monthKey(x.month_date) === shiftMonth(monthKey(m.month_date), -n));

export function renderEconomyCards(v: OverviewView): string {
	const infl = lastWith(v.months, (m) => m.inflation_yoy);
	const fx = lastWith(v.months, (m) => m.naira_per_usd);
	const gr = lastWith(v.years, (y) => y.real_gdp_growth);
	const pp = lastWith(v.years, (y) => y.gdp_per_person_usd);
	const cards: string[] = [];

	if (infl) {
		const prev = monthBefore(v.all, infl);
		const yearAgo = monthsAgo(v.all, infl, 12);
		const label = monthLabel(monthKey(infl.month_date), "medium");
		const cost = 1000 * (1 + (infl.inflation_yoy ?? 0));
		cards.push(
			flipCard({
				label: "Inflation",
				asOf: label,
				value: { value: rate(infl.inflation_yoy), unit: "" },
				change: change(infl.inflation_yoy, prev?.inflation_yoy, false, "pts"),
				vs: prev ? `vs ${monthLabel(monthKey(prev.month_date), "medium")}` : "",
				spark: v.all.slice(Math.max(0, v.all.indexOf(infl) - 11), v.all.indexOf(infl) + 1).map((m) => m.inflation_yoy),
				backTitle: "What it means",
				back: `<span class="p">Prices were ${rate(infl.inflation_yoy)} higher than a year earlier: what cost ₦1,000 in ${yearAgo ? monthLabel(monthKey(yearAgo.month_date), "medium") : "the same month last year"} cost about ${naira(cost)} in ${label}.</span>`,
			}),
		);
	}
	if (fx) {
		const prev = monthBefore(v.all, fx);
		const yearAgo = monthsAgo(v.all, fx, 12);
		const c = change(fx.naira_per_usd, prev?.naira_per_usd, false);
		const word = c.value === null ? "" : Math.abs(c.value) < 0.0005 ? "naira unchanged" : c.value > 0 ? "naira weaker" : "naira stronger";
		cards.push(
			flipCard({
				label: "Naira per US dollar",
				asOf: monthLabel(monthKey(fx.month_date), "medium"),
				value: { value: naira(fx.naira_per_usd ?? 0), unit: " / $" },
				change: c,
				vs: word,
				spark: v.all.slice(Math.max(0, v.all.indexOf(fx) - 11), v.all.indexOf(fx) + 1).map((m) => m.naira_per_usd),
				backTitle: "What it means",
				back: `<span class="p">₦100,000 bought about $${Math.round(100000 / (fx.naira_per_usd ?? 1)).toLocaleString("en-GB")} in ${monthLabel(monthKey(fx.month_date), "medium")}${yearAgo?.naira_per_usd ? `; a year earlier it bought $${Math.round(100000 / yearAgo.naira_per_usd).toLocaleString("en-GB")}` : ""}.</span>`,
			}),
		);
	}
	if (gr) {
		const prev = v.allYears.find((y) => y.year === gr.year - 1);
		const g = gr.real_gdp_growth ?? 0;
		const c = change(gr.real_gdp_growth, prev?.real_gdp_growth, true, "pts");
		// Slower growth is a change of pace, not a decline: amber, unless the economy shrank
		const pace = g < 0 ? c : c.value !== null && c.value < 0 ? { ...c, colour: "#C98A00" } : c;
		cards.push(
			flipCard({
				label: "Real GDP growth",
				asOf: String(gr.year),
				value: { value: rate(g), unit: "" },
				change: pace,
				vs: prev ? `${c.value !== null && c.value < 0 ? "slower than" : "faster than"} ${prev.year}` : "",
				spark: v.allYears.filter((y) => y.year > gr.year - 6 && y.year <= gr.year).map((y) => y.real_gdp_growth),
				backTitle: "What it means",
				back: `<span class="p">The economy produced ${rate(g)} more goods and services than in ${gr.year - 1}, after removing price rises.</span><span class="tip">The population grows about ${percent(POPULATION_GROWTH)} a year, so growth below that means less for each person.</span>`,
			}),
		);
	}
	if (pp) {
		const prev = v.allYears.find((y) => y.year === pp.year - 1);
		cards.push(
			flipCard({
				label: "GDP per person",
				asOf: String(pp.year),
				value: { value: bigMoney(pp.gdp_per_person_usd, "$"), unit: "" },
				change: change(pp.gdp_per_person_usd, prev?.gdp_per_person_usd, true),
				vs: prev ? `vs ${prev.year}` : "",
				spark: v.allYears.filter((y) => y.year > pp.year - 6 && y.year <= pp.year).map((y) => y.gdp_per_person_usd),
				backTitle: "What it means",
				back: `<span class="p">If the economy's output in ${pp.year} were shared equally, each Nigerian's share would be about ${bigMoney(pp.gdp_per_person_usd, "$")}, or ${bigMoney(pp.gdp_per_person_naira, "₦")}.</span>`,
			}),
		);
	}
	return cards.join("");
}

/** Labels: the latest month and each president's peak in the range. */
function peakLabels(rows: EconomyMonth[], pick: (m: EconomyMonth) => number | null) {
	const keep = new Set<number>();
	const lastIdx = rows.map(pick).map((x, i) => (x != null ? i : -1)).filter((i) => i >= 0).at(-1);
	if (lastIdx !== undefined) keep.add(lastIdx);
	for (const p of presidentsIn(rows)) {
		let best = -1;
		rows.forEach((m, i) => {
			const x = pick(m);
			if (m.president === p && x != null && (best < 0 || x > (pick(rows[best]) ?? -Infinity))) best = i;
		});
		if (best >= 0) keep.add(best);
	}
	return keep;
}

export function renderMonthChart(v: OverviewView, kind: "inflation" | "naira", width: number): string {
	const pick = kind === "inflation" ? (m: EconomyMonth) => m.inflation_yoy : (m: EconomyMonth) => m.naira_per_usd;
	const rows = v.months;
	const labels = peakLabels(rows, pick);
	return lineChart({
		width,
		labels: rows.map((m) => monthLabel(monthKey(m.month_date), "tick")),
		series: [{ name: kind, values: rows.map(pick), colour: "#0E6B45", colours: rows.map((m) => presidentColour(m.president)), labelColour: "#14231D" }],
		format: kind === "inflation" ? (x) => rate(x) : (x) => naira(x),
		axisFormat: kind === "inflation" ? (x) => rate(x, 0) : (x) => naira(x),
		valueLabel: (_, i) => (labels.has(i) ? "above" : null),
		includeZero: kind === "inflation",
		aria: kind === "inflation" ? "Inflation by month, coloured by president" : "Naira per US dollar by month, coloured by president",
	});
}

export function monthTooltip(v: OverviewView, i: number, kind: "inflation" | "naira"): string | null {
	const m = v.months[i];
	if (!m) return null;
	const pick = kind === "inflation" ? (x: EconomyMonth) => x.inflation_yoy : (x: EconomyMonth) => x.naira_per_usd;
	const value = pick(m);
	if (value == null) return null;
	const prev = monthBefore(v.all, m);
	const yearAgo = monthsAgo(v.all, m, 12);
	const fmt = kind === "inflation" ? (x: number) => rate(x) : (x: number) => naira(x);
	const kindOf = kind === "inflation" ? "pts" : "pct";
	return `<div class="m">${monthLabel(monthKey(m.month_date), "long")}</div>
		<div class="r"><span>President</span><b>${esc(m.president ?? "–")}</b><span></span></div>
		<div class="r"><span>${kind === "inflation" ? "Inflation" : "₦ per $"}</span><b>${fmt(value)}</b><span></span></div>
		<div class="r"><span>vs previous month</span><b>${prev && pick(prev) != null ? fmt(pick(prev)!) : "–"}</b>${badge(change(value, prev ? pick(prev) : null, false, kindOf))}</div>
		<div class="r"><span>vs a year earlier</span><b>${yearAgo && pick(yearAgo) != null ? fmt(pick(yearAgo)!) : "–"}</b>${badge(change(value, yearAgo ? pick(yearAgo) : null, false, kindOf))}</div>`;
}

/** Per president in the range: the value they inherited (the month before their first) and the value they left. */
function foundLeft(v: OverviewView, pick: (m: EconomyMonth) => number | null) {
	return presidentsIn(v.months).map((p) => {
		const mine = v.months.filter((m) => m.president === p && pick(m) != null);
		const first = mine[0];
		const last = mine[mine.length - 1];
		const before = first ? monthBefore(v.all, first) : undefined;
		const found = before && pick(before) != null ? pick(before)! : first ? pick(first)! : null;
		return { p, first, last, found, left: last ? pick(last) : null };
	});
}

export function renderExplain(v: OverviewView, kind: "inflation" | "naira"): string {
	if (kind === "inflation") {
		const rows = foundLeft(v, (m) => m.inflation_yoy).filter((r) => r.last);
		const peak = [...v.months].filter((m) => m.inflation_yoy != null).sort((a, b) => b.inflation_yoy! - a.inflation_yoy!)[0];
		return explainPanel(
			`<p>Inflation is how much prices rose over the past 12 months. At 20%, something that cost ₦1,000 a year ago costs ₦1,200 now. Lower inflation is better for households; it doesn't mean prices fell, only that they rose more slowly.</p>`,
			`${peak ? `<p>The highest in the selected years was ${hl(rate(peak.inflation_yoy))} in ${monthLabel(monthKey(peak.month_date), "long")}.</p>` : ""}${presidentRows(
				rows.map((r) => ({
					name: r.p,
					colour: presidentColour(r.p),
					from: rate(r.found),
					to: rate(r.left),
					note: `found → left, ${monthLabel(monthKey(r.first!.month_date), "medium")} to ${monthLabel(monthKey(r.last!.month_date), "medium")}`,
				})),
			)}`,
		);
	}
	const rows = foundLeft(v, (m) => m.naira_per_usd).filter((r) => r.last);
	return explainPanel(
		`<p>How many naira one US dollar costs. When the number goes up, the naira buys less abroad: imports, fuel and school fees in dollars cost more. A higher number means a weaker naira.</p>`,
		presidentRows(
			rows.map((r) => {
				const lost = r.found && r.left ? r.found / r.left - 1 : null;
				return {
					name: r.p,
					colour: presidentColour(r.p),
					from: naira(r.found ?? 0),
					to: naira(r.left ?? 0),
					note: lost === null ? "" : `the naira ${lost < 0 ? "lost" : "gained"} ${percent(Math.abs(lost))} of its value`,
				};
			}),
		),
	);
}

export function renderEconomyInsight(v: OverviewView): string {
	const infl = lastWith(v.months, (m) => m.inflation_yoy);
	const fx = lastWith(v.months, (m) => m.naira_per_usd);
	const firstFx = v.months.find((m) => m.naira_per_usd != null);
	const peak = [...v.months].filter((m) => m.inflation_yoy != null).sort((a, b) => b.inflation_yoy! - a.inflation_yoy!)[0];
	const sentences: string[] = [];
	if (infl && peak) {
		const at = monthLabel(monthKey(infl.month_date), "long");
		sentences.push(
			peak === infl
				? `Inflation was ${hl(rate(infl.inflation_yoy))} in ${at}, the highest in the selected years.`
				: `Inflation was ${hl(rate(infl.inflation_yoy))} in ${at}, down from a peak of ${hl(rate(peak.inflation_yoy))} in ${monthLabel(monthKey(peak.month_date), "long")}.`,
		);
	}
	if (fx && firstFx && fx !== firstFx) {
		const lost = firstFx.naira_per_usd! / fx.naira_per_usd! - 1;
		const c = change(fx.naira_per_usd, firstFx.naira_per_usd, false);
		sentences.push(
			`A dollar cost ${hl(naira(fx.naira_per_usd!))} in ${monthLabel(monthKey(fx.month_date), "long")}, against ${naira(firstFx.naira_per_usd!)} in ${monthLabel(monthKey(firstFx.month_date), "long")}: the naira <span class="${bannerTone(c)}">${lost < 0 ? "lost" : "gained"} ${percent(Math.abs(lost))}</span> of its value.`,
		);
	}
	const kicker = infl ? monthLabel(monthKey(infl.month_date), "long") : "Economy";
	return banner(kicker, sentences.length ? sentences : ["No data in the selected years."]);
}
