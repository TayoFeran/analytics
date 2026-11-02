"""Build the Nigeria states TopoJSON used by the States page shape map.

Source: geoBoundaries gbOpen NGA ADM1 (state boundaries from GRID3, 2022),
licensed CC BY 4.0, so the About page and README credit it. The download URL is
pinned to a release commit so a rebuild always gives the same map.

Power BI's shape map only reads TopoJSON. TopoJSON stores each shared border once,
so simplifying it keeps neighbouring states flush, without gaps or overlaps.

Usage, from this folder (topojson is only needed here, so it isn't a project dependency):
    uv run --no-project --with topojson python make_state_map.py

Writes maps/nigeria_states.json next to this script.
"""

import json
import urllib.request
from pathlib import Path

import topojson

SOURCE = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NGA/ADM1/"
    "geoBoundaries-NGA-ADM1_simplified.geojson"
)
OUT = Path(__file__).parent / "maps" / "nigeria_states.json"

# The map keys must equal dim_state[state]. The 36 states already match; the FCT
# gets a shorter name and stays on the map (grey, no FAAC data) so there is no hole.
RENAME = {"Abuja Federal Capital Territory": "Federal Capital Territory"}

# About 1 km in degrees: finer than a pixel on a ~520 px wide map of Nigeria
SIMPLIFY_DEGREES = 0.01


def main() -> None:
    with urllib.request.urlopen(SOURCE, timeout=60) as response:
        source = json.load(response)

    features = []
    for feature in source["features"]:
        name = feature["properties"]["shapeName"]
        name = RENAME.get(name, name)
        features.append(
            {"type": "Feature", "properties": {"name": name}, "geometry": feature["geometry"]}
        )
    if len(features) != 37:
        raise SystemExit(f"Error: expected 36 states and the FCT, got {len(features)} shapes")

    topology = topojson.Topology(
        {"type": "FeatureCollection", "features": features},
        object_name="states",
        prequantize=1e5,
        toposimplify=SIMPLIFY_DEGREES,
        prevent_oversimplify=True,
    )
    OUT.parent.mkdir(exist_ok=True)
    # Trailing newline, as the end-of-file pre-commit hook expects
    OUT.write_text(topology.to_json() + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {len(features)} shapes to {OUT.name} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
