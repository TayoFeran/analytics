// The Year + Month filter ("Whole year" or one month) shared by the pages with a single
// month filter: States and Local governments. Works on any month list with a flag for the
// months that have data.

import { monthLabel } from "./format";

export interface Period {
	year: string;
	/** A month key, or "" for the whole year. */
	month: string;
}

export interface Months {
	months: string[];
	has: boolean[];
}

/** Years with LGA figures, latest first. */
export const periodYears = (d: Months): string[] => [...new Set(d.months.filter((_, i) => d.has[i]).map((k) => k.slice(0, 4)))].sort().reverse();

/** Months of a year with LGA figures, in calendar order. */
export const yearMonths = (d: Months, year: string): string[] => d.months.filter((k, i) => d.has[i] && k.startsWith(year));

/** Month indexes the period covers. */
export function periodIndexes(d: Months, p: Period): number[] {
	const out: number[] = [];
	d.months.forEach((k, i) => {
		if (d.has[i] && k.startsWith(p.year) && (!p.month || k === p.month)) out.push(i);
	});
	return out;
}

export function periodLabel(d: Months, p: Period): string {
	if (p.month) return monthLabel(p.month, "long");
	const n = yearMonths(d, p.year).length;
	return n === 12 ? p.year : `${p.year} (${n} months)`;
}

/** The latest month, the default period. */
export function latestPeriod(d: Months): Period {
	const year = periodYears(d)[0];
	return { year, month: yearMonths(d, year).at(-1)! };
}

export function readPeriod(params: URLSearchParams, d: Months): Period {
	const latest = latestPeriod(d);
	const year = periodYears(d).includes(params.get("year") ?? "") ? params.get("year")! : latest.year;
	const asked = params.get("month");
	if (asked === "all") return { year, month: "" };
	if (asked && yearMonths(d, year).includes(asked)) return { year, month: asked };
	return year === latest.year ? latest : { year, month: yearMonths(d, year).at(-1)! };
}

export function writePeriod(p: Period, d: Months, q: URLSearchParams): void {
	const latest = latestPeriod(d);
	if (p.year !== latest.year) q.set("year", p.year);
	if (!p.month) q.set("month", "all");
	else if (p.month !== (p.year === latest.year ? latest.month : yearMonths(d, p.year).at(-1))) q.set("month", p.month);
}

/** The Month dropdown's options for a year, for the build and the browser. */
export function monthOptions(d: Months, year: string): { value: string; label: string }[] {
	return [{ value: "", label: "Whole year" }, ...yearMonths(d, year).map((k) => ({ value: k, label: monthLabel(k, "name") }))];
}

/** The same period a year earlier: the month before for a month, the same months of the year before for a year. */
export function previousIndexes(d: Months, p: Period): number[] {
	if (p.month) {
		const i = d.months.indexOf(p.month);
		return i > 0 && d.has[i - 1] ? [i - 1] : [];
	}
	const prevYear = String(Number(p.year) - 1);
	const wanted = new Set(periodIndexes(d, p).map((i) => d.months[i].slice(5)));
	return periodIndexes(d, { year: prevYear, month: "" }).filter((i) => wanted.has(d.months[i].slice(5)));
}

/** What the change is measured against: "June" or "Jan–Aug 2025". */
export function previousLabel(d: Months, p: Period): string {
	const prev = previousIndexes(d, p);
	if (!prev.length) return "";
	if (p.month) return monthLabel(d.months[prev[0]], "name");
	const first = monthLabel(d.months[prev[0]], "tick").slice(0, 3);
	const last = monthLabel(d.months[prev.at(-1)!], "tick").slice(0, 3);
	const year = d.months[prev[0]].slice(0, 4);
	return prev.length === 12 ? year : `${first}–${last} ${year}`;
}
