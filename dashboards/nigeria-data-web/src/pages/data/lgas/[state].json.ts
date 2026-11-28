// One state's packed council data as a static JSON file (/data/lgas/<state>.json), so the
// Compare page downloads only the two states being compared, not all 774 councils.
import type { APIRoute } from "astro";
import info from "../../../data/export_info.json";
import lgaMonth from "../../../data/faac_lga_month.json";
import reportErrors from "../../../data/faac_lga_report_errors.json";
import lgaStates from "../../../data/faac_lga_states.json";
import national from "../../../data/faac_national_month.json";
import { type LgaMonthRow, type LgaReportError, type LgaStateData, packAllStates, stateSlug } from "../../../lib/pages/faac-lgas";

export function getStaticPaths() {
	return packAllStates(lgaMonth as LgaMonthRow[], reportErrors as LgaReportError[], lgaStates, national, info.exported_at).map((data) => ({
		params: { state: stateSlug(data.state) },
		props: { data },
	}));
}

export const GET: APIRoute = ({ props }) =>
	new Response(JSON.stringify((props as { data: LgaStateData }).data), { headers: { "Content-Type": "application/json" } });
