// Nigeria state map: turns the TopoJSON used by the Power BI map into SVG paths at build
// time, so the browser gets plain paths and no map library.
// Boundaries: geoBoundaries gbOpen NGA ADM1 (GRID3, 2022), CC BY 4.0.

import { esc } from "./format";

interface Topology {
	transform: { scale: [number, number]; translate: [number, number] };
	arcs: [number, number][][];
	objects: { states: { geometries: { type: "Polygon"; properties: { name: string }; arcs: number[][] }[] } };
}

export interface StateShape {
	name: string;
	d: string;
	/** Label point (centre of the bounding box). */
	cx: number;
	cy: number;
}

export const MAP_WIDTH = 600;

/** Decode the shared arcs into longitude/latitude points. */
function decodeArcs(topo: Topology): [number, number][][] {
	const [sx, sy] = topo.transform.scale;
	const [tx, ty] = topo.transform.translate;
	return topo.arcs.map((arc) => {
		let x = 0;
		let y = 0;
		return arc.map(([dx, dy]) => {
			x += dx;
			y += dy;
			return [x * sx + tx, y * sy + ty];
		});
	});
}

export function buildStateShapes(topo: Topology): { shapes: StateShape[]; height: number } {
	const arcs = decodeArcs(topo);
	const rings = topo.objects.states.geometries.map((g) => ({
		name: g.properties.name,
		rings: g.arcs.map((ring) =>
			ring.flatMap((index, k) => {
				const arc = index >= 0 ? arcs[index] : [...arcs[~index]].reverse();
				return k === 0 ? arc : arc.slice(1);
			}),
		),
	}));

	// Simple equirectangular projection, with longitudes shrunk by cos(latitude) at
	// Nigeria's middle (about 9°N) so the country isn't stretched sideways.
	const all = rings.flatMap((s) => s.rings.flat());
	const lonMin = Math.min(...all.map((p) => p[0]));
	const lonMax = Math.max(...all.map((p) => p[0]));
	const latMin = Math.min(...all.map((p) => p[1]));
	const latMax = Math.max(...all.map((p) => p[1]));
	const k = Math.cos((((latMin + latMax) / 2) * Math.PI) / 180);
	const scale = (MAP_WIDTH - 8) / ((lonMax - lonMin) * k);
	const height = Math.round((latMax - latMin) * scale + 8);
	const project = ([lon, lat]: [number, number]) => [4 + (lon - lonMin) * k * scale, 4 + (latMax - lat) * scale];

	const shapes = rings.map((s) => {
		const pts = s.rings.map((ring) => ring.map(project));
		const flat = pts.flat();
		const xs = flat.map((p) => p[0]);
		const ys = flat.map((p) => p[1]);
		const d = pts.map((ring) => `M${ring.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join("L")}Z`).join("");
		return { name: s.name, d, cx: (Math.min(...xs) + Math.max(...xs)) / 2, cy: (Math.min(...ys) + Math.max(...ys)) / 2 };
	});
	return { shapes, height };
}

/** The map with a fill per state. States without a fill (FCT) are grey. */
export function renderMap(
	shapes: StateShape[],
	height: number,
	fill: (name: string) => string | null,
	options: { selected?: string; aria: string },
): string {
	const paths = shapes
		.map((s) => {
			const colour = fill(s.name);
			const selected = s.name === options.selected;
			return `<path d="${s.d}" fill="${colour ?? "#D5DDD9"}" class="st${colour ? "" : " nodata"}${selected ? " sel" : ""}" data-i="${esc(s.name)}"><title>${esc(s.name)}</title></path>`;
		})
		.join("");
	return `<svg class="map-svg" viewBox="0 0 ${MAP_WIDTH} ${height}" role="img" aria-label="${esc(options.aria)}">${paths}</svg>`;
}

/** Green scale from light to the dashboard's dark green, for a share between 0 and 1. */
export function greenScale(t: number): string {
	const a = [227, 244, 236];
	const b = [11, 61, 46];
	const c = a.map((v, i) => Math.round(v + (b[i] - v) * Math.max(0, Math.min(1, t))));
	return `rgb(${c.join(",")})`;
}
