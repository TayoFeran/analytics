// Formatting shared by the build and the browser, so both write numbers the same way.

export type Currency = "NGN" | "USD";

const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = [
	"January",
	"February",
	"March",
	"April",
	"May",
	"June",
	"July",
	"August",
	"September",
	"October",
	"November",
	"December",
];

/** "2026-04-01" -> "2026-04". Month keys sort correctly as plain strings. */
export const monthKey = (date: string): string => date.slice(0, 7);

function parts(key: string): [number, number] {
	return [Number(key.slice(0, 4)), Number(key.slice(5, 7))];
}

/** Month labels: "Apr 26" (dropdowns, axis), "Apr 2026", "April 2026", "April". */
export function monthLabel(key: string, style: "tick" | "medium" | "long" | "name"): string {
	const [year, month] = parts(key);
	if (style === "tick") return `${MONTHS_SHORT[month - 1]} ${String(year).slice(2)}`;
	if (style === "medium") return `${MONTHS_SHORT[month - 1]} ${year}`;
	if (style === "name") return MONTHS_LONG[month - 1];
	return `${MONTHS_LONG[month - 1]} ${year}`;
}

/** Last day of the month, as a UTC date. */
export function monthEnd(key: string): Date {
	const [year, month] = parts(key);
	return new Date(Date.UTC(year, month, 0));
}

export function formatDate(date: Date): string {
	return `${date.getUTCDate()} ${MONTHS_SHORT[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

const number = (value: number, decimals: number) =>
	value.toLocaleString("en-GB", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

/**
 * Money as a value and a unit, so cards can show the unit smaller.
 * Naira in billions; dollars in billions or, below $1bn, millions (FAAC months are $0.4-1bn).
 */
export function moneyParts(value: number, currency: Currency, decimals = 1): { value: string; unit: string } {
	const symbol = currency === "USD" ? "$" : "₦";
	if (!Number.isFinite(value)) return { value: "–", unit: "" };
	const abs = Math.abs(value);
	const sign = value < 0 ? "-" : "";
	if (abs >= 1e9 || currency === "NGN") return { value: `${sign}${symbol}${number(abs / 1e9, decimals)}`, unit: "bn" };
	return { value: `${sign}${symbol}${number(abs / 1e6, decimals)}`, unit: "m" };
}

export function money(value: number, currency: Currency, decimals = 1): string {
	const p = moneyParts(value, currency, decimals);
	return p.value + p.unit;
}

export const percent = (share: number, decimals = 1): string => `${number(share * 100, decimals)}%`;

export const naira = (value: number, decimals = 0): string => `₦${number(value, decimals)}`;

/** Escape text going into HTML strings. */
export function esc(text: string): string {
	return text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}
