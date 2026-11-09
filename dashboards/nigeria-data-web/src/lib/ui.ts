// HTML pieces shared by every page: colour rules, change chips, flip cards, banners,
// the freshness strip and "What it means" panels. Pages build HTML strings with these, at
// build time and again in the browser when a filter changes.

import { esc, formatDate, monthEnd, monthLabel, percent } from "./format";

export const COLOURS = {
	better: "#0E8A5F",
	worse: "#C93C3C",
	equal: "#C98A00",
	neutral: "#5E6E67",
	ink: "#0B3D2E",
	gold: "#E2B53E",
	goldText: "#9A7414",
	grey: "#93A59D",
};

// --- Change chips ------------------------------------------------------------------------

export interface Change {
	value: number | null;
	colour: string;
	text: string;
}

/**
 * Change from `previous` to `current`, coloured by whether up is good.
 * kind "pct": relative change (▲ 5.2%); kind "pts": difference in percentage points of two
 * shares (▲ 1.3 pts).
 */
export function change(
	current: number | null | undefined,
	previous: number | null | undefined,
	upIsGood: boolean,
	kind: "pct" | "pts" = "pct",
): Change {
	if (current == null || previous == null || !Number.isFinite(current) || !Number.isFinite(previous)) {
		return { value: null, colour: COLOURS.neutral, text: "n/a" };
	}
	if (kind === "pct" && previous === 0) return { value: null, colour: COLOURS.neutral, text: "n/a" };
	const value = kind === "pct" ? (current - previous) / Math.abs(previous) : current - previous;
	const flat = kind === "pct" ? Math.abs(value) < 0.0005 : Math.abs(value) < 0.0005;
	if (flat) return { value, colour: COLOURS.equal, text: kind === "pct" ? "■ 0.0%" : "■ 0.0 pts" };
	const up = value > 0;
	const arrow = up ? "▲" : "▼";
	const amount = kind === "pct" ? percent(Math.abs(value)) : `${(Math.abs(value) * 100).toFixed(1)} pts`;
	return { value, colour: up === upIsGood ? COLOURS.better : COLOURS.worse, text: `${arrow} ${amount}` };
}

/** Lines that can be ₦0: words instead of a percentage. */
export function zeroAwareChange(current: number, previous: number | undefined, upIsGood: boolean): Change {
	if (previous === undefined) return change(current, previous, upIsGood);
	if (current === 0 && previous === 0) return { value: null, colour: COLOURS.neutral, text: "–" };
	if (previous === 0) return { value: null, colour: COLOURS.neutral, text: "Resumed" };
	if (current === 0) return { value: null, colour: COLOURS.neutral, text: "Not paid" };
	return change(current, previous, upIsGood);
}

export function tint(colour: string): string {
	if (colour === COLOURS.better) return "#E3F4EC";
	if (colour === COLOURS.worse) return "#FBE7E7";
	if (colour === COLOURS.equal) return "#FBF1DC";
	return "#EDF2EF";
}

export const badge = (c: Change): string =>
	`<span class="badge" style="color:${c.colour};background:${tint(c.colour)}">${c.text}</span>`;

/** Banner classes for a change: green, red or gold text on the dark banner. */
export const bannerTone = (c: Change): string =>
	c.colour === COLOURS.better ? "up" : c.colour === COLOURS.worse ? "dn" : "hl";

// --- Small SVGs --------------------------------------------------------------------------

export function sparkline(values: (number | null)[], colour = COLOURS.ink): string {
	const clean = values.filter((v): v is number => v != null && Number.isFinite(v));
	if (clean.length < 2) return "";
	const w = 84;
	const h = 28;
	const min = Math.min(...clean);
	const max = Math.max(...clean);
	const pts = values
		.map((v, i) => (v == null || !Number.isFinite(v) ? null : [(i * (w - 6)) / (values.length - 1) + 3, h - 3 - ((v - min) / (max - min || 1)) * (h - 8)]))
		.filter((p): p is number[] => p !== null);
	const last = pts[pts.length - 1];
	const line = pts.map((p) => p.map((n) => n.toFixed(1)).join(",")).join(" ");
	return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${line}" fill="none" stroke="${colour}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="3" fill="${colour}"/></svg>`;
}

// --- Flip cards --------------------------------------------------------------------------

export interface FlipCard {
	label: string;
	value: { value: string; unit: string };
	change: Change;
	vs: string;
	spark?: (number | null)[];
	backTitle: string;
	back: string;
	asOf?: string;
}

export function flipCard(c: FlipCard): string {
	return `<button type="button" class="fc" aria-pressed="false" aria-label="${esc(c.label)}: ${esc(c.value.value + c.value.unit)}. Tap for detail.">
		<span class="fc-inner">
			<span class="face front">
				<span class="lbl">${c.label}${c.asOf ? ` <span class="asof">· ${c.asOf}</span>` : ""}</span>
				<span class="val">${c.value.value}<small>${c.value.unit}</small></span>
				<span class="chg">${badge(c.change)}<span>${c.vs}</span></span>
				<span class="foot">${c.spark ? sparkline(c.spark) : "<span></span>"}<span class="hint">Tap for detail ↻</span></span>
			</span>
			<span class="face back">
				<span class="bt">${c.backTitle}</span>
				${c.back}
			</span>
		</span>
	</button>`;
}

// --- Banner ------------------------------------------------------------------------------

export function banner(kicker: string, sentences: string[]): string {
	return `<div class="ico" aria-hidden="true"><svg width="16" height="16" viewBox="0 0 16 16"><path d="M8 1.5a4.5 4.5 0 0 0-2.6 8.2V12h5.2V9.7A4.5 4.5 0 0 0 8 1.5zM6 13.2h4V14.5H6z" fill="#E2B53E"/></svg></div>
		<div class="kick">Key takeaway<br />${kicker}</div>
		<p class="txt">${sentences.filter(Boolean).join(" ")}</p>`;
}

export const hl = (text: string) => `<span class="hl">${text}</span>`;

// --- Freshness ---------------------------------------------------------------------------

export interface Clock {
	name: string;
	/** Month key ("2026-04") for monthly data, or a year ("2025") for yearly data. */
	latest: string;
	cadence: "monthly" | "yearly";
	dueDays: number;
	warnDays: number;
}

const DAY = 86_400_000;
// The export runs daily; older than this means the pipeline stopped publishing.
const REFRESH_MISSED_DAYS = 3;
const SEVERITY = ["On time", "Late", "Overdue", "Refresh missed"];

function periodEnd(clock: Clock): Date {
	return clock.cadence === "yearly" ? new Date(Date.UTC(Number(clock.latest), 11, 31)) : monthEnd(clock.latest);
}

function clockStatus(clock: Clock, today: Date): { label: string; due: Date } {
	const due = new Date(periodEnd(clock).getTime() + clock.dueDays * DAY);
	const late = Math.floor((today.getTime() - due.getTime()) / DAY);
	const label = late > clock.warnDays ? "Overdue" : late > 0 ? "Late" : "On time";
	return { label, due };
}

/** One pill for the worst clock; the text names each source's latest period. */
export function renderFreshness(clocks: Clock[], exportedAt: string, today: Date): string {
	const exported = new Date(exportedAt);
	const statuses = clocks.map((c) => ({ clock: c, ...clockStatus(c, today) }));
	let worst = statuses.reduce((a, b) => (SEVERITY.indexOf(b.label) > SEVERITY.indexOf(a.label) ? b : a)).label;
	if ((today.getTime() - exported.getTime()) / DAY > REFRESH_MISSED_DAYS) worst = "Refresh missed";
	const colour = worst === "On time" ? COLOURS.better : worst === "Late" ? COLOURS.equal : COLOURS.worse;
	const latest = statuses
		.map((s) => {
			const period = s.clock.cadence === "yearly" ? s.clock.latest : monthLabel(s.clock.latest, "medium");
			return clocks.length > 1 ? `${s.clock.name} ${period}` : period;
		})
		.join(" · ");
	const why = statuses
		.map(
			(s) =>
				`${s.clock.name}: a ${s.clock.cadence === "yearly" ? "year" : "month"} is expected within ${s.clock.dueDays} days after it ends; the next is expected by ${formatDate(s.due)} (${s.label.toLowerCase()}).`,
		)
		.join(" ");
	return `<span class="pill" style="background:${colour}">${worst}</span>
		<span class="msg">Latest data: ${latest}</span>
		<span class="facts" title="${esc(why)}">Updated ${formatDate(exported)}</span>`;
}

export const FAAC_CLOCK = (latest: string): Clock => ({ name: "FAAC", latest, cadence: "monthly", dueDays: 45, warnDays: 15 });
export const CPI_CLOCK = (latest: string): Clock => ({ name: "CPI", latest, cadence: "monthly", dueDays: 60, warnDays: 30 });
export const GDP_CLOCK = (latest: string): Clock => ({ name: "GDP", latest, cadence: "yearly", dueDays: 270, warnDays: 90 });

// --- "What it means" panels ----------------------------------------------------------------

/** Explanation side of a chart card: a definition, then what the chart says. */
export function explainPanel(definition: string, says: string): string {
	return `<div class="explain-cols"><div><p class="ex-h">What it is</p>${definition}</div><div><p class="ex-h">What the chart says</p>${says}</div></div>`;
}

/** Rows of president → value pairs for explanation panels. */
export function presidentRows(rows: { name: string; colour: string; from: string; to: string; note: string }[]): string {
	if (!rows.length) return `<p class="muted">No president with data in the selected range.</p>`;
	return `<ul class="pres-rows">${rows
		.map(
			(r) =>
				`<li><span class="dot" style="background:${r.colour}"></span><b>${esc(r.name)}</b><span class="ft">${r.from} → ${r.to}</span><span class="nt">${r.note}</span></li>`,
		)
		.join("")}</ul>`;
}

/** Colour legend, e.g. presidents or zones. */
export function legend(items: { name: string; colour: string }[]): string {
	return `<ul class="legend">${items.map((i) => `<li style="--c:${i.colour}">${esc(i.name)}</li>`).join("")}</ul>`;
}
