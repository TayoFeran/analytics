// Browser helpers shared by every page's script.

export const byId = <T extends HTMLElement = HTMLElement>(id: string): T => document.getElementById(id) as T;

export function readData<T>(id: string): T {
	return JSON.parse(byId(id).textContent ?? "{}") as T;
}

/** Keep filters in the address, so a shared link opens the same view. */
export function syncUrl(params: URLSearchParams): void {
	const query = params.toString();
	history.replaceState(null, "", query ? `?${query}` : location.pathname);
}

export const reducedMotion = (): boolean => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Flip cards and "What it means" buttons anywhere on the page. */
export function bindFlips(): void {
	document.addEventListener("click", (e) => {
		const target = e.target as HTMLElement;
		const card = target.closest<HTMLButtonElement>(".fc");
		if (card) {
			const flipped = card.classList.toggle("flipped");
			card.setAttribute("aria-pressed", String(flipped));
			return;
		}
		const toggle = target.closest<HTMLButtonElement>("[data-explain]");
		if (toggle) {
			const panel = toggle.closest(".swap");
			const open = panel?.classList.toggle("explaining") ?? false;
			panel?.querySelectorAll<HTMLButtonElement>("[data-explain]").forEach((b) => b.setAttribute("aria-expanded", String(open)));
		}
	});
}

/**
 * Tooltip for a chart container. For time charts the <svg> carries data-x0/dx/n and the
 * pointer's position picks the point; for bars and maps the element under the pointer
 * carries data-i.
 */
export function bindTooltip(chart: HTMLElement, html: (key: string) => string | null): void {
	const card = chart.closest<HTMLElement>(".card") ?? chart;
	const tip = document.createElement("div");
	tip.className = "ltt";
	tip.setAttribute("aria-hidden", "true");
	card.appendChild(tip);

	const hide = () => {
		tip.style.display = "none";
		chart.querySelector(".guide")?.setAttribute("visibility", "hidden");
		chart.querySelectorAll(".hover").forEach((el) => el.classList.remove("hover"));
	};

	const show = (e: PointerEvent) => {
		const target = e.target as Element;
		let key: string | null = null;
		const item = target.closest<HTMLElement | SVGElement>("[data-i]");
		const svg = chart.querySelector<SVGSVGElement>("svg[data-n]");
		if (item && chart.contains(item)) {
			key = item.getAttribute("data-i");
			chart.querySelectorAll(".hover").forEach((el) => el.classList.remove("hover"));
			item.classList.add("hover");
		} else if (svg) {
			const rect = svg.getBoundingClientRect();
			const ratio = (svg.viewBox.baseVal?.width || rect.width) / rect.width;
			const x = (e.clientX - rect.left) * ratio;
			const x0 = Number(svg.dataset.x0);
			const dx = Number(svg.dataset.dx);
			const n = Number(svg.dataset.n);
			const i = dx ? Math.max(0, Math.min(n - 1, Math.round((x - x0) / dx))) : 0;
			key = String(i);
			const guide = svg.querySelector(".guide");
			const gx = String(x0 + i * dx);
			guide?.setAttribute("x1", gx);
			guide?.setAttribute("x2", gx);
			guide?.setAttribute("visibility", "visible");
		}
		const content = key === null ? null : html(key);
		if (!content) return hide();
		tip.innerHTML = content;
		tip.style.display = "block";
		const cardRect = card.getBoundingClientRect();
		const px = e.clientX - cardRect.left;
		const py = e.clientY - cardRect.top;
		const w = tip.offsetWidth;
		const h = tip.offsetHeight;
		const left = px + 16 + w > cardRect.width ? Math.max(4, px - w - 16) : px + 16;
		const top = Math.max(4, Math.min(py - h / 2, cardRect.height - h - 4));
		tip.style.left = `${left}px`;
		tip.style.top = `${top}px`;
	};

	chart.addEventListener("pointermove", show);
	chart.addEventListener("pointerdown", show);
	chart.addEventListener("pointerleave", (e) => {
		if (e.pointerType !== "touch") hide();
	});
	document.addEventListener("pointerdown", (e) => {
		if (!chart.contains(e.target as Node)) hide();
	});
}

/** Call `draw` again when the element's width changes (rotating a phone, resizing a window). */
export function onWidthChange(el: HTMLElement, draw: () => void): void {
	let last = el.clientWidth;
	new ResizeObserver(() => {
		if (Math.abs(el.clientWidth - last) < 4) return;
		last = el.clientWidth;
		draw();
	}).observe(el);
}

/** Width to draw a chart at: the container's, with a sensible minimum. */
export const widthOf = (el: HTMLElement, fallback = 640): number => Math.max(280, el.clientWidth || fallback);

/** Fill a <select> with options, keeping the chosen value. */
export function setOptions(select: HTMLSelectElement, options: { value: string; label: string }[], value: string): void {
	select.innerHTML = options.map((o) => `<option value="${o.value}">${o.label}</option>`).join("");
	select.value = value;
}

/** Wire the shared FAAC filters (#from, #to, [data-cur]) to a filters object and a render function. */
export function bindFaacFilters(f: { from: string; to: string; currency: "NGN" | "USD" }, render: () => void): void {
	const from = document.getElementById("from") as HTMLSelectElement | null;
	const to = document.getElementById("to") as HTMLSelectElement | null;
	from?.addEventListener("change", () => {
		f.from = from.value;
		if (f.from > f.to) f.to = f.from;
		render();
	});
	to?.addEventListener("change", () => {
		f.to = to.value;
		if (f.from > f.to) f.from = f.to;
		render();
	});
	document.querySelectorAll<HTMLButtonElement>("[data-cur]").forEach((b) =>
		b.addEventListener("click", () => {
			f.currency = b.dataset.cur === "USD" ? "USD" : "NGN";
			render();
		}),
	);
}

/** Show the filters' current values in the controls. */
export function showFaacFilters(f: { from: string; to: string; currency: "NGN" | "USD" }): void {
	const from = document.getElementById("from") as HTMLSelectElement | null;
	const to = document.getElementById("to") as HTMLSelectElement | null;
	if (from) from.value = f.from;
	if (to) to.value = f.to;
	document.querySelectorAll<HTMLButtonElement>("[data-cur]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.cur === f.currency)));
}

/** Wire the shared Economy filters (#yfrom, #yto, #president). */
export function bindEconomyFilters(f: { from: number; to: number; president: string }, render: () => void): void {
	const from = document.getElementById("yfrom") as HTMLSelectElement | null;
	const to = document.getElementById("yto") as HTMLSelectElement | null;
	const president = document.getElementById("president") as HTMLSelectElement | null;
	from?.addEventListener("change", () => {
		f.from = Number(from.value);
		if (f.from > f.to) f.to = f.from;
		render();
	});
	to?.addEventListener("change", () => {
		f.to = Number(to.value);
		if (f.from > f.to) f.from = f.to;
		render();
	});
	president?.addEventListener("change", () => {
		f.president = president.value;
		render();
	});
}

export function showEconomyFilters(f: { from: number; to: number; president: string }): void {
	const set = (id: string, value: string) => {
		const el = document.getElementById(id) as HTMLSelectElement | null;
		if (el) el.value = value;
	};
	set("yfrom", String(f.from));
	set("yto", String(f.to));
	set("president", f.president);
}
