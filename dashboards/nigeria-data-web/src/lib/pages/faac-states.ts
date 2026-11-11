// FAAC States: map and ranking of the 36 states for one month.

import { cubeValue, type Currency, type FaacCube, toCurrency, ZONE_COLOURS, ZONES } from "../faac";
import { esc, money, monthLabel, percent } from "../format";
import { greenScale } from "../map";
import { type RankRow, rankBars } from "../charts";
import { badge, banner, bannerTone, change, hl, legend } from "../ui";

export interface StatesData {
	cube: FaacCube;
	exportedAt: string;
}

export interface StatesFilters {
	to: string;
	currency: Currency;
	state: string;
	zone: string;
	mode: "states" | "zones";
}

interface StateFigures {
	name: string;
	zone: string;
	gross: number;
	deductions: number;
	net: number;
	prev?: { gross: number; deductions: number; net: number };
	rank: number;
}

export interface StatesView {
	f: StatesFilters;
	month: number;
	states: StateFigures[];
	totalNet: number;
	totalGross: number;
	totalDeductions: number;
	prevTotalNet?: number;
}

export function buildStatesView(d: StatesData, f: StatesFilters): StatesView {
	const c = d.cube;
	let m = c.months.indexOf(f.to);
	if (m < 0) m = c.months.length - 1;
	const value = (line: "gross" | "deductions" | "net", month: number, s: number) =>
		toCurrency(cubeValue(c, line, month, s), c.rate[month], f.currency);
	const states = c.states
		.map((name, s) => ({
			name,
			zone: c.zones[s],
			gross: value("gross", m, s),
			deductions: value("deductions", m, s),
			net: value("net", m, s),
			prev: m > 0 ? { gross: value("gross", m - 1, s), deductions: value("deductions", m - 1, s), net: value("net", m - 1, s) } : undefined,
			rank: 0,
		}))
		.sort((a, b) => b.net - a.net);
	states.forEach((s, i) => (s.rank = i + 1));
	const sum = (k: "gross" | "deductions" | "net") => states.reduce((a, s) => a + s[k], 0);
	return {
		f,
		month: m,
		states,
		totalNet: sum("net"),
		totalGross: sum("gross"),
		totalDeductions: sum("deductions"),
		prevTotalNet: m > 0 ? states.reduce((a, s) => a + (s.prev?.net ?? 0), 0) : undefined,
	};
}

/**
 * Fill colour per state for the map: darker green = more net received. Shaded by rank, not
 * amount: the oil states receive several times the rest, which would leave most states pale.
 */
export function mapFills(v: StatesView): Record<string, string> {
	const n = v.states.length;
	const fills: Record<string, string> = {};
	for (const s of v.states) fills[s.name] = greenScale(0.08 + 0.92 * ((n - s.rank) / (n - 1 || 1)));
	return fills;
}

export const monthTitle = (v: StatesView, c: FaacCube) => monthLabel(c.months[v.month], "long");

export function renderRanking(v: StatesView): string {
	const cur = v.f.currency;
	if (v.f.mode === "zones" && !v.f.zone) {
		const rows: RankRow[] = ZONES.map((zone) => {
			const members = v.states.filter((s) => s.zone === zone);
			const net = members.reduce((a, s) => a + s.net, 0);
			return { label: zone, sub: `${members.length} states`, value: net, display: money(net, cur), colour: ZONE_COLOURS[zone], key: `zone:${zone}` };
		}).sort((a, b) => b.value - a.value);
		return rankBars(rows, { clickable: true, aria: "Net received by zone" });
	}
	const list = v.f.zone ? v.states.filter((s) => s.zone === v.f.zone) : v.states;
	const rows: RankRow[] = list.map((s) => ({
		label: `${s.rank}. ${s.name}`,
		sub: s.zone,
		subColour: ZONE_COLOURS[s.zone],
		value: s.net,
		display: money(s.net, cur),
		colour: ZONE_COLOURS[s.zone],
		faded: Boolean(v.f.state) && v.f.state !== s.name,
		key: s.name,
	}));
	return rankBars(rows, { clickable: true, aria: "Net received by state" });
}

export function renderRankTools(v: StatesView): string {
	const zoneLegend = legend(ZONES.map((z) => ({ name: z, colour: ZONE_COLOURS[z] })));
	const mode = `<div class="seg" role="group" aria-label="Rank by">
		<button type="button" data-mode="states" aria-pressed="${v.f.mode === "states" && !v.f.zone}">36 states</button>
		<button type="button" data-mode="zones" aria-pressed="${v.f.mode === "zones" || Boolean(v.f.zone)}">6 zones</button>
	</div>`;
	const back = v.f.zone ? `<span>Showing ${esc(v.f.zone)} · <button type="button" class="linkish" data-mode="zones">all zones</button></span>` : "";
	return `<div class="rank-tools">${mode}${back}</div>${zoneLegend}`;
}

export function stateTooltip(v: StatesView, key: string, c: FaacCube): string | null {
	const cur = v.f.currency;
	const month = monthLabel(c.months[v.month], "long");
	if (key.startsWith("zone:")) {
		const zone = key.slice(5);
		const members = v.states.filter((s) => s.zone === zone);
		const net = members.reduce((a, s) => a + s.net, 0);
		return `<div class="m">${esc(zone)}</div>
			<div class="r"><span>States</span><b>${members.length}</b><span></span></div>
			<div class="r"><span>Net received</span><b>${money(net, cur)}</b><span></span></div>
			<div class="r"><span>Share of national</span><b>${percent(net / v.totalNet)}</b><span></span></div>
			<div class="vs">${month} · tap to see its states</div>`;
	}
	const s = v.states.find((x) => x.name === key);
	if (!s) return null;
	const row = (name: string, k: "gross" | "deductions" | "net", upGood: boolean) =>
		`<div class="r"><span>${name}</span><b>${money(s[k], cur)}</b>${badge(change(s[k], s.prev?.[k], upGood))}</div>`;
	return `<div class="m">${esc(s.name)} <span class="muted" style="font-weight:500">· ${esc(s.zone)}</span></div>
		<div class="r"><span>Rank</span><b>#${s.rank} of ${v.states.length}</b><span></span></div>
		${row("Gross", "gross", true)}${row("Deductions", "deductions", false)}${row("Net received", "net", true)}
		<div class="vs">${month} · change vs the previous month</div>`;
}

export function renderStatesInsight(v: StatesView, c: FaacCube): string {
	const cur = v.f.currency;
	const month = monthLabel(c.months[v.month], "long");
	const prevName = v.month > 0 ? monthLabel(c.months[v.month - 1], "name") : "";
	const s = v.states.find((x) => x.name === v.f.state);
	if (s) {
		const ch = change(s.net, s.prev?.net, true);
		const dedShare = s.deductions / s.gross;
		const nationalShare = v.totalDeductions / v.totalGross;
		return banner(month, [
			`${esc(s.name)} received ${hl(money(s.net, cur))} net in ${month}${ch.value !== null ? `, <span class="${bannerTone(ch)}">${ch.text}</span> on ${prevName}` : ""}, ranking ${hl(`#${s.rank} of ${v.states.length}`)}.`,
			`Deductions took ${hl(percent(dedShare))} of its gross, ${dedShare > nationalShare ? "more than" : dedShare < nationalShare ? "less than" : "the same as"} the ${percent(nationalShare)} for all states.`,
		]);
	}
	const first = v.states[0];
	const last = v.states[v.states.length - 1];
	const ch = change(v.totalNet, v.prevTotalNet, true);
	return banner(month, [
		`The ${v.states.length} states received ${hl(money(v.totalNet, cur))} net in ${month}${ch.value !== null ? `, <span class="${bannerTone(ch)}">${ch.text}</span> on ${prevName}` : ""}.`,
		`${esc(first.name)} received the most, ${hl(percent(first.net / v.totalNet))} of the total; ${esc(last.name)} the least, ${hl(percent(last.net / v.totalNet))}.`,
		`Tap a state on the map or in the ranking for its own story.`,
	]);
}
