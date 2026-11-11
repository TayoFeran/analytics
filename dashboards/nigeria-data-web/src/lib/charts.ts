// Hand-drawn SVG and HTML charts, so pages need no chart library (light on mobile data).
// Charts along a time axis put data-x0 / data-dx / data-n on the <svg> so the browser can
// tell which point the pointer is over; ranked bars put data-i on each row.

import { esc } from "./format";

export interface Frame {
	width: number;
	height: number;
	padL: number;
	padR: number;
	padT: number;
	padB: number;
}

const isNum = (v: number | null | undefined): v is number => v != null && Number.isFinite(v);

/** Roughly 4 round tick values covering [min, max]. */
export function niceTicks(min: number, max: number, count = 4): number[] {
	if (min === max) return [min];
	const raw = (max - min) / count;
	const mag = 10 ** Math.floor(Math.log10(raw));
	const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
	const ticks: number[] = [];
	for (let t = Math.ceil(min / step) * step; t <= max + step * 1e-9; t += step) ticks.push(Number(t.toFixed(10)));
	return ticks;
}

function scaleY(frame: Frame, min: number, max: number) {
	return (v: number) => frame.padT + ((max - v) / (max - min || 1)) * (frame.height - frame.padT - frame.padB);
}

/** Every k-th label so they don't overlap, always including the last. */
export function tickEvery(n: number, plotWidth: number, labelWidth = 56): number {
	return Math.max(1, Math.ceil((n * labelWidth) / Math.max(plotWidth, 1)));
}

function yAxis(frame: Frame, ticks: number[], y: (v: number) => number, format: (v: number) => string): string {
	return ticks
		.map(
			(t) =>
				`<line x1="${frame.padL}" x2="${frame.width - frame.padR}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}" class="grid${t === 0 ? " zero" : ""}"/><text x="${frame.padL - 6}" y="${(y(t) + 3.5).toFixed(1)}" text-anchor="end" class="axis">${format(t)}</text>`,
		)
		.join("");
}

function xTicks(labels: string[], x: (i: number) => number, frame: Frame, every: number): string {
	const last = labels.length - 1;
	return labels
		.map((label, i) => {
			const show = i === last || (i % every === 0 && last - i >= every);
			if (!show) return "";
			const anchor = labels.length === 1 ? "middle" : i === 0 ? "start" : i === last ? "end" : "middle";
			return `<text x="${x(i).toFixed(1)}" y="${frame.height - 8}" text-anchor="${anchor}" class="tick">${esc(label)}</text>`;
		})
		.join("");
}

function smoothPath(points: [number, number][]): string {
	if (points.length === 1) return `M${points[0][0]},${points[0][1]}`;
	let d = `M${points[0][0].toFixed(1)},${points[0][1].toFixed(1)}`;
	for (let i = 0; i < points.length - 1; i++) {
		const p0 = points[i - 1] ?? points[i];
		const p1 = points[i];
		const p2 = points[i + 1];
		const p3 = points[i + 2] ?? p2;
		d += ` C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)},${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)},${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
	}
	return d;
}

const straightPath = (points: [number, number][]) =>
	points.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");

export interface LineSeries {
	name: string;
	values: (number | null)[];
	colour: string;
	/** Colour per point, e.g. by president; overrides `colour` for the segment ending at that point. */
	colours?: string[];
	dashed?: boolean;
	/** Text colour for this series' value labels. */
	labelColour?: string;
}

export interface LineChartOptions {
	width: number;
	height?: number;
	labels: string[];
	series: LineSeries[];
	format: (v: number) => string;
	axisFormat?: (v: number) => string;
	/** Which points get a value label; return "above" or "below". */
	valueLabel?: (series: number, i: number) => "above" | "below" | null;
	smooth?: boolean;
	includeZero?: boolean;
	aria: string;
}

export function lineChart(o: LineChartOptions): string {
	const height = o.height ?? (o.width < 520 ? 240 : 300);
	const frame: Frame = { width: o.width, height, padL: 52, padR: o.width < 520 ? 44 : 60, padT: 18, padB: 28 };
	const n = o.labels.length;
	const all = o.series.flatMap((s) => s.values).filter(isNum);
	if (!all.length) return `<p class="muted">No data in the selected range.</p>`;
	let lo = Math.min(...all);
	let hi = Math.max(...all);
	if (o.includeZero) lo = Math.min(lo, 0);
	const pad = (hi - lo) * 0.08 || Math.abs(hi) * 0.1 || 1;
	lo = o.includeZero && lo >= 0 ? 0 : lo - pad;
	hi += pad;
	const ticks = niceTicks(lo, hi);
	lo = Math.min(lo, ticks[0]);
	hi = Math.max(hi, ticks[ticks.length - 1]);
	const y = scaleY(frame, lo, hi);
	const plotW = frame.width - frame.padL - frame.padR;
	const dx = n > 1 ? plotW / (n - 1) : 0;
	const x = (i: number) => (n > 1 ? frame.padL + i * dx : frame.padL + plotW / 2);

	let s = yAxis(frame, ticks, y, o.axisFormat ?? o.format);
	o.series.forEach((series, si) => {
		const dash = series.dashed ? ` stroke-dasharray="6 4"` : "";
		// Split into runs: a gap (null) breaks the line, a colour change starts a new segment
		let run: [number, number][] = [];
		let runColour = "";
		const flush = () => {
			if (run.length > 1 || (run.length === 1 && n === 1)) {
				const d = o.smooth ? smoothPath(run) : straightPath(run);
				s += `<path d="${d}" fill="none" stroke="${runColour}" stroke-width="2.4" stroke-linejoin="round"${dash}/>`;
			}
		};
		series.values.forEach((v, i) => {
			if (!isNum(v)) {
				flush();
				run = [];
				return;
			}
			// The segment from point i-1 to point i takes point i's colour
			const colour = series.colours?.[i] ?? series.colour;
			const point: [number, number] = [x(i), y(v)];
			if (run.length && colour !== runColour) {
				const prev = run[run.length - 1];
				flush();
				run = [prev, point];
			} else run.push(point);
			runColour = colour;
		});
		flush();
		if (o.valueLabel) {
			series.values.forEach((v, i) => {
				if (!isNum(v)) return;
				const where = o.valueLabel!(si, i);
				if (!where) return;
				const colour = series.labelColour ?? series.colours?.[i] ?? series.colour;
				const last = i === n - 1 && n > 1;
				s += `<circle cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="3" fill="${series.colours?.[i] ?? series.colour}"/>`;
				if (last) {
					s += `<text x="${(x(i) + 6).toFixed(1)}" y="${(y(v) + 4).toFixed(1)}" class="vl" fill="${colour}">${o.format(v)}</text>`;
				} else {
					const anchor = i === 0 ? "start" : "middle";
					const ty = where === "above" ? y(v) - 8 : y(v) + 15;
					s += `<text x="${x(i).toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="${anchor}" class="vl" fill="${colour}">${o.format(v)}</text>`;
				}
			});
		}
	});
	s += xTicks(o.labels, x, frame, tickEvery(n, plotW));
	s += `<line class="guide" x1="0" x2="0" y1="${frame.padT - 6}" y2="${frame.height - frame.padB + 4}" visibility="hidden"/>`;
	return `<svg class="chart-svg" width="${o.width}" height="${height}" viewBox="0 0 ${o.width} ${height}" role="img" aria-label="${esc(o.aria)}" data-x0="${x(0).toFixed(2)}" data-dx="${dx.toFixed(4)}" data-n="${n}">${s}</svg>`;
}

export interface ColumnChartOptions {
	width: number;
	height?: number;
	labels: string[];
	values: (number | null)[];
	colours: string[];
	format: (v: number) => string;
	axisFormat?: (v: number) => string;
	/** Which columns get a value label. */
	labelled?: (i: number) => boolean;
	/** A second series drawn as a (dashed) line over the columns, on the same scale. */
	overlay?: { values: (number | null)[]; colour: string; dashed?: boolean };
	/** A horizontal reference line, e.g. population growth. */
	reference?: { value: number; colour: string; label: string };
	aria: string;
}

export function columnChart(o: ColumnChartOptions): string {
	const height = o.height ?? (o.width < 520 ? 240 : 300);
	const frame: Frame = { width: o.width, height, padL: 52, padR: 12, padT: 22, padB: 28 };
	const n = o.labels.length;
	const all = [...o.values, ...(o.overlay?.values ?? []), o.reference?.value ?? null].filter(isNum);
	if (!all.length) return `<p class="muted">No data in the selected range.</p>`;
	let lo = Math.min(0, ...all);
	let hi = Math.max(0, ...all);
	const pad = (hi - lo) * 0.1 || 1;
	if (hi > 0) hi += pad;
	if (lo < 0) lo -= pad;
	const ticks = niceTicks(lo, hi);
	lo = Math.min(lo, ticks[0]);
	hi = Math.max(hi, ticks[ticks.length - 1]);
	const y = scaleY(frame, lo, hi);
	const plotW = frame.width - frame.padL - frame.padR;
	const band = plotW / Math.max(n, 1);
	const barW = Math.max(2, Math.min(band * 0.72, 44));
	const cx = (i: number) => frame.padL + (i + 0.5) * band;

	let s = yAxis(frame, ticks, y, o.axisFormat ?? o.format);
	o.values.forEach((v, i) => {
		if (!isNum(v)) return;
		const top = y(Math.max(v, 0));
		const h = Math.max(1, Math.abs(y(v) - y(0)));
		s += `<rect x="${(cx(i) - barW / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${barW.toFixed(1)}" height="${h.toFixed(1)}" rx="2" fill="${o.colours[i]}"/>`;
	});
	if (o.overlay) {
		const pts = o.overlay.values.map((v, i) => (isNum(v) ? ([cx(i), y(v)] as [number, number]) : null));
		const runs: [number, number][][] = [[]];
		for (const p of pts) p ? runs[runs.length - 1].push(p) : runs.push([]);
		for (const r of runs.filter((r) => r.length > 1))
			s += `<path d="${straightPath(r)}" fill="none" stroke="${o.overlay.colour}" stroke-width="2"${o.overlay.dashed ? ` stroke-dasharray="6 4"` : ""}/>`;
	}
	if (o.reference) {
		const ry = y(o.reference.value);
		s += `<line x1="${frame.padL}" x2="${frame.width - frame.padR}" y1="${ry.toFixed(1)}" y2="${ry.toFixed(1)}" stroke="${o.reference.colour}" stroke-width="1.5" stroke-dasharray="5 4"/>`;
		if (o.reference.label) s += `<text x="${frame.width - frame.padR}" y="${(ry - 5).toFixed(1)}" text-anchor="end" class="axis" fill="${o.reference.colour}">${esc(o.reference.label)}</text>`;
	}
	if (o.labelled) {
		o.values.forEach((v, i) => {
			if (!isNum(v) || !o.labelled!(i)) return;
			const ty = v >= 0 ? y(v) - 5 : y(v) + 13;
			s += `<text x="${cx(i).toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="middle" class="vl" fill="#14231D">${o.format(v)}</text>`;
		});
	}
	s += xTicks(o.labels, cx, frame, tickEvery(n, plotW, 44));
	s += `<line class="guide" x1="0" x2="0" y1="${frame.padT - 6}" y2="${frame.height - frame.padB + 4}" visibility="hidden"/>`;
	return `<svg class="chart-svg" width="${o.width}" height="${height}" viewBox="0 0 ${o.width} ${height}" role="img" aria-label="${esc(o.aria)}" data-x0="${cx(0).toFixed(2)}" data-dx="${band.toFixed(4)}" data-n="${n}">${s}</svg>`;
}

export interface StackedAreaOptions {
	width: number;
	height?: number;
	labels: string[];
	series: { name: string; values: number[]; colour: string }[];
	format: (v: number) => string;
	axisFormat?: (v: number) => string;
	aria: string;
}

export function stackedArea(o: StackedAreaOptions): string {
	const height = o.height ?? (o.width < 520 ? 240 : 300);
	const frame: Frame = { width: o.width, height, padL: 52, padR: o.width < 520 ? 48 : 64, padT: 18, padB: 28 };
	const n = o.labels.length;
	const totals = o.labels.map((_, i) => o.series.reduce((a, s) => a + Math.max(0, s.values[i] ?? 0), 0));
	const ticks = niceTicks(0, Math.max(...totals, 1) * 1.08);
	const y = scaleY(frame, 0, ticks[ticks.length - 1]);
	const plotW = frame.width - frame.padL - frame.padR;
	const dx = n > 1 ? plotW / (n - 1) : 0;
	const x = (i: number) => (n > 1 ? frame.padL + i * dx : frame.padL + plotW / 2);

	let s = yAxis(frame, ticks, y, o.axisFormat ?? o.format);
	const base = new Array(n).fill(0);
	for (const series of o.series) {
		const top = base.map((b, i) => b + Math.max(0, series.values[i] ?? 0));
		const upper = top.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
		const lower = base.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).reverse();
		const shape = n > 1 ? `M${upper.join(" L")} L${lower.join(" L")} Z` : "";
		if (shape) s += `<path d="${shape}" fill="${series.colour}" stroke="#fff" stroke-width="0.6"/>`;
		top.forEach((v, i) => (base[i] = v));
	}
	const last = n - 1;
	s += `<text x="${(x(last) + 6).toFixed(1)}" y="${(y(totals[last]) + 4).toFixed(1)}" class="vl" fill="#0B3D2E">${o.format(totals[last])}</text>`;
	s += xTicks(o.labels, x, frame, tickEvery(n, plotW));
	s += `<line class="guide" x1="0" x2="0" y1="${frame.padT - 6}" y2="${frame.height - frame.padB + 4}" visibility="hidden"/>`;
	return `<svg class="chart-svg" width="${o.width}" height="${height}" viewBox="0 0 ${o.width} ${height}" role="img" aria-label="${esc(o.aria)}" data-x0="${x(0).toFixed(2)}" data-dx="${dx.toFixed(4)}" data-n="${n}">${s}</svg>`;
}

export interface RankRow {
	label: string;
	sub?: string;
	subColour?: string;
	value: number;
	display: string;
	colour: string;
	faded?: boolean;
	/** Index passed back to the tooltip and click handlers. */
	key: string;
	/** Optional hatching for partial data. */
	hatched?: boolean;
}

/** Ranked horizontal bars as HTML. Negative values grow left from a centre line. */
export function rankBars(rows: RankRow[], options: { clickable?: boolean; aria: string }): string {
	if (!rows.length) return `<p class="muted">Nothing to show for this selection.</p>`;
	const hasNeg = rows.some((r) => r.value < 0);
	const max = Math.max(...rows.map((r) => Math.abs(r.value)), 1e-9);
	const items = rows
		.map((r) => {
			const w = (Math.abs(r.value) / max) * (hasNeg ? 50 : 100);
			const left = hasNeg ? (r.value < 0 ? 50 - w : 50) : 0;
			const fill = r.hatched
				? `repeating-linear-gradient(135deg, ${r.colour} 0 6px, color-mix(in srgb, ${r.colour} 45%, #fff) 6px 10px)`
				: r.colour;
			const tag = options.clickable ? "button" : "div";
			return `<li class="${r.faded ? "faded" : ""}"><${tag} ${options.clickable ? 'type="button" ' : ""}class="rk-row" data-i="${esc(r.key)}">
				<span class="rk-name">${esc(r.label)}${r.sub ? `<small style="color:${r.subColour ?? "var(--muted)"}">${esc(r.sub)}</small>` : ""}</span>
				<span class="rk-track${hasNeg ? " diverging" : ""}"><span class="rk-bar" style="left:${left.toFixed(2)}%;width:${Math.max(w, 0.4).toFixed(2)}%;background:${fill}"></span></span>
				<span class="rk-val">${r.display}</span>
			</${tag}></li>`;
		})
		.join("");
	return `<ol class="rank" aria-label="${esc(options.aria)}">${items}</ol>`;
}
