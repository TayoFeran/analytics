// Economy size: GDP in naira and dollars, real growth and GDP per person, by year.

import { columnChart, lineChart } from "../charts";
import { type EconomyFilters, type EconomyYear, POPULATION_GROWTH, presidentColour } from "../economy";
import { bigMoney, esc, naira, percent, rate } from "../format";
import { badge, banner, change, COLOURS, explainPanel, hl, presidentRows } from "../ui";
import { presidentsIn } from "./economy-overview";

export interface SizeView {
	f: EconomyFilters;
	years: EconomyYear[];
	all: EconomyYear[];
}

export function buildSizeView(all: EconomyYear[], f: EconomyFilters): SizeView {
	return {
		f,
		all,
		years: all.filter((y) => y.year >= f.from && y.year <= f.to && (f.president === "All" || y.president === f.president)),
	};
}

export type SizeChart = "naira" | "usd" | "growth" | "perperson";

const PICK: Record<SizeChart, (y: EconomyYear) => number | null> = {
	naira: (y) => y.gdp_naira,
	usd: (y) => y.gdp_usd,
	growth: (y) => y.real_gdp_growth,
	perperson: (y) => y.gdp_per_person_usd,
};

const FORMAT: Record<SizeChart, (v: number) => string> = {
	naira: (v) => bigMoney(v, "₦", 0),
	usd: (v) => bigMoney(v, "$", 0),
	growth: (v) => rate(v),
	perperson: (v) => bigMoney(v, "$"),
};

/** Labels on the latest year and the peak (and the lowest for growth), or every bar when 12 or fewer. */
function labelled(values: (number | null)[], withLowest: boolean): (i: number) => boolean {
	if (values.length <= 12) return () => true;
	const idx = values.map((v, i) => (v == null ? -1 : i)).filter((i) => i >= 0);
	const keep = new Set<number>();
	if (idx.length) {
		keep.add(idx[idx.length - 1]);
		keep.add(idx.reduce((a, b) => (values[b]! > values[a]! ? b : a)));
		if (withLowest) keep.add(idx.reduce((a, b) => (values[b]! < values[a]! ? b : a)));
	}
	return (i) => keep.has(i);
}

export function renderSizeChart(v: SizeView, chart: SizeChart, width: number): string {
	const values = v.years.map(PICK[chart]);
	const labels = v.years.map((y) => String(y.year));
	if (chart === "perperson") {
		const keep = labelled(values, false);
		return lineChart({
			width,
			labels,
			series: [{ name: "GDP per person", values, colour: COLOURS.ink, colours: v.years.map((y) => presidentColour(y.president)), labelColour: "#14231D" }],
			format: FORMAT.perperson,
			valueLabel: (_, i) => (keep(i) ? "above" : null),
			includeZero: true,
			aria: "GDP per person in US dollars by year",
		});
	}
	const colours =
		chart === "growth"
			? values.map((g) => (g == null ? COLOURS.grey : g > 0 ? COLOURS.better : g < 0 ? COLOURS.worse : COLOURS.equal))
			: v.years.map((y) => presidentColour(y.president));
	return columnChart({
		width,
		labels,
		values,
		colours,
		format: FORMAT[chart],
		labelled: labelled(values, chart === "growth"),
		// The legend names the dashed line; a label on the chart would sit on the latest bars
		reference: chart === "growth" ? { value: POPULATION_GROWTH, colour: COLOURS.equal, label: "" } : undefined,
		aria: { naira: "GDP in naira by year", usd: "GDP in US dollars by year", growth: "Real GDP growth by year", perperson: "" }[chart],
	});
}

export function sizeTooltip(v: SizeView, i: number, chart: SizeChart): string | null {
	const y = v.years[i];
	if (!y) return null;
	const value = PICK[chart](y);
	if (value == null) return null;
	const prev = v.all.find((x) => x.year === y.year - 1);
	const before = prev ? PICK[chart](prev) : null;
	const kind = chart === "growth" ? "pts" : "pct";
	let extra = "";
	if (chart === "usd" && y.avg_naira_per_usd) extra = `<div class="r"><span>Average ₦ per $</span><b>${naira(y.avg_naira_per_usd)}</b><span></span></div>`;
	if (chart === "perperson") extra = `<div class="r"><span>In naira</span><b>${bigMoney(y.gdp_per_person_naira, "₦")}</b><span></span></div>`;
	return `<div class="m">${y.year}</div>
		<div class="r"><span>President</span><b>${esc(y.president ?? "none (before 1999)")}</b><span></span></div>
		<div class="r"><span>Value</span><b>${FORMAT[chart](value)}</b><span></span></div>
		${extra}
		<div class="r"><span>vs ${y.year - 1}</span><b>${before != null ? FORMAT[chart](before) : "–"}</b>${badge(change(value, before, true, kind))}</div>`;
}

const DEFINITIONS: Record<SizeChart, string> = {
	naira: `<p>GDP (gross domestic product) is the value of everything the economy produced in a year. This chart is in naira at the prices of each year (nominal), so it also rises when prices rise.</p>`,
	usd: `<p>The same GDP converted to US dollars at each year's average exchange rate. When the naira weakens, GDP in dollars can fall even if the economy grew.</p>`,
	growth: `<p>Real growth is how much more the economy produced than the year before, after removing price rises. Below 0 means the economy shrank. The dashed line is population growth: growth below it means less for each person.</p>`,
	perperson: `<p>GDP divided by the number of people: each Nigerian's share of the year's output if it were shared equally. It is an average, not what a typical person earns.</p>`,
};

export function renderSizeExplain(v: SizeView, chart: SizeChart): string {
	const pick = PICK[chart];
	const rows = presidentsIn(v.years).map((p) => {
		const mine = v.years.filter((y) => y.president === p && pick(y) != null);
		const first = mine[0];
		const last = mine[mine.length - 1];
		if (chart === "growth") {
			const avg = mine.reduce((a, y) => a + (y.real_gdp_growth ?? 0), 0) / (mine.length || 1);
			const shrank = mine.filter((y) => (y.real_gdp_growth ?? 0) < 0).length;
			return {
				name: p,
				colour: presidentColour(p),
				from: `${first?.year ?? ""}–${last?.year ?? ""}`,
				to: `${rate(avg)} a year`,
				note: shrank ? `the economy shrank in ${shrank} year${shrank === 1 ? "" : "s"}` : "no year of decline",
			};
		}
		// What they inherited: the year before their first year
		const before = first ? v.all.find((y) => y.year === first.year - 1) : undefined;
		const found = before && pick(before) != null ? pick(before)! : first ? pick(first)! : null;
		const left = last ? pick(last) : null;
		const c = found && left ? left / found - 1 : null;
		return {
			name: p,
			colour: presidentColour(p),
			from: found != null ? FORMAT[chart](found) : "–",
			to: left != null ? FORMAT[chart](left) : "–",
			note: c === null ? "" : `found → left, ${c >= 0 ? "up" : "down"} ${percent(Math.abs(c))}`,
		};
	});
	return explainPanel(DEFINITIONS[chart], presidentRows(rows.filter((r) => r.from !== "–" || r.to !== "–")));
}

export function renderSizeInsight(v: SizeView): string {
	const latest = [...v.years].reverse().find((y) => y.gdp_usd != null);
	if (!latest) return banner("Economy size", ["No data in the selected years."]);
	const peak = v.years.filter((y) => y.gdp_usd != null).sort((a, b) => b.gdp_usd! - a.gdp_usd!)[0];
	const g = latest.real_gdp_growth;
	return banner(String(latest.year), [
		`In ${latest.year} Nigeria's economy was worth ${hl(bigMoney(latest.gdp_naira, "₦"))}, or ${hl(bigMoney(latest.gdp_usd, "$"))}.`,
		peak !== latest ? `In dollars it peaked at ${hl(bigMoney(peak.gdp_usd, "$"))} in ${peak.year}, before the naira lost value.` : `That is the highest in dollars in the selected years.`,
		g != null
			? `Real growth was ${hl(rate(g))}, ${g >= POPULATION_GROWTH ? "faster" : "slower"} than the population's ${percent(POPULATION_GROWTH)}, so output per person ${g >= POPULATION_GROWTH ? "rose" : "fell"}.`
			: "",
	]);
}
