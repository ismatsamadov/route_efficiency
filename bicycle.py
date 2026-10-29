#!/usr/bin/env python3
"""
Put AYNA's bicycle lanes and parking points beside the bus network.

Reads the two opendata.az files that bicycle_lanes and bicycle_parking name in
busnet.toml (KMZ files saved from Google Earth), the network, the population grid, the
BakuBus counts and the metro exits, and writes to ./output/bicycle/ (or --out):
  summary.json      the lanes (km, streets, the lanes of January 2025 for comparison, the
                    km with a bus route beside them), the parking points by kind, the stops
                    and routes within reach of a lane, the parking near stops, lanes and
                    metro exits, and the people within the coverage radius of a lane beside
                    those within it of a stop
  lanes.csv         one row per street with a lane: km, segments, km beside a bus route, the
                    bus routes along it, served stops and parking points within 100 m
  routes.csv        the routes whose path runs along a lane: km along lanes, share of the
                    route, the streets, stops within 100 m of a lane, counted boardings
  stops.csv         the served stops within 200 m of a lane: nearest lane and distance,
                    routes, parking points within 100 m
  parking.csv       every parking point: kind, coordinates, nearest served stop and its
                    distance, nearest lane and distance, nearest metro exit and distance
  bicycle.geojson   the lanes and the parking points; GitHub draws this file as a map

Standard library only. Usage:
  python3 bicycle.py
  python3 bicycle.py --set coverage_radius_m=500
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from busnet.bicycle import LANES_2025_FOLDER, load_lanes, load_parking, measure   # noqa: E402
from busnet.destinations import read_exits                                         # noqa: E402
from busnet.inputs import load_inputs                                              # noqa: E402


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: Excel shows ə/ş/ç correctly
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "busnet.toml"), help="settings file (TOML); 'none' for defaults only")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="override one setting or data path for this run; repeatable")
    ap.add_argument("--out", default=str(ROOT / "output" / "bicycle"))
    args = ap.parse_args()

    config = None if args.config.lower() == "none" or not Path(args.config).exists() else args.config
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print(f"Settings: {config or 'built-in defaults'}" + (f" with {len(args.set)} override(s)" if args.set else ""))
    try:
        inp = load_inputs(ROOT, config, args.set)
    except (ValueError, TypeError) as e:
        sys.exit(f"Settings error: {e}")
    paths = {}
    for key in ("bicycle_lanes", "bicycle_parking"):
        p = inp.data.get(key)
        if not p or not Path(p).exists():
            sys.exit(f"{key} is missing: {p or 'not set in the settings'}; run python3 data/fetch_external.py --only opendata")
        paths[key] = Path(p)
        inp.found[key] = str(paths[key].relative_to(ROOT)) if paths[key].is_relative_to(ROOT) else str(paths[key])

    lanes, skipped = load_lanes(paths["bicycle_lanes"])
    lanes_2025, _ = load_lanes(paths["bicycle_parking"], LANES_2025_FOLDER)
    parking = load_parking(paths["bicycle_parking"])
    exits = read_exits(inp.data["metro_exits"]) if inp.found.get("metro_exits") else []
    print(f"Lanes: {len(lanes)} segments, {sum(lane.length_m for lane in lanes) / 1000:.2f} km"
          + (f"; skipped {', '.join(skipped)}" if skipped else "")
          + f"; January 2025: {len(lanes_2025)} segments, {sum(lane.length_m for lane in lanes_2025) / 1000:.2f} km")
    kinds = {k: sum(1 for p in parking if p.kind == k) for k in ("MPV", "MPS")}
    print(f"Parking points: {kinds['MPV']} MPV, {kinds['MPS']} MPS; metro exits: {len(exits)}")

    result = measure(inp.network, inp.a, inp.zones, inp.observed, lanes, lanes_2025, parking, exits, skipped)
    summary = result["summary"]
    summary["inputs"] = inp.found
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    for name in ("lanes", "routes", "stops", "parking"):
        write_csv(out / f"{name}.csv", result[name])
    (out / "bicycle.geojson").write_text(json.dumps(result["geojson"], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    b, pk, pe = summary["bus"], summary["parking"], summary["people"]
    print(f"\nServed stops within 50 / 100 / 200 m of a lane: "
          + " / ".join(f"{b['stops_within_m_of_lane'][str(r)]:,}" for r in (50, 100, 200)) + f" of {b['served_stops']:,}")
    print(f"Routes along the lanes (at least {summary['settings']['along_route_km']} km): {b['routes_along_lanes']}; "
          f"touching them at all: {b['routes_touching_lanes']}; route km along lanes: {b['route_km_along_lanes']:.1f}")
    print(f"Lane km with a bus route beside them: {summary['lanes']['km_beside_bus_route']:.1f} of {summary['lanes']['km']:.1f}")
    for kind in ("MPV", "MPS"):
        s = pk[kind]
        print(f"{kind}: {s['points']} points; within 50 m of a lane {s['within_50m_of_lane']}, within 100 m of a stop "
              f"{s['within_100m_of_stop']} (median {s['median_m_to_stop']:.0f} m), within 300 m of a metro exit {s['within_300m_of_metro_exit']}")
    if pe:
        r = summary["settings"]["coverage_radius_m"]
        print(f"People within {r} m: of a lane {pe['within_radius_of_lane']:,.0f}, of a stop {pe['within_radius_of_stop']:,.0f}, "
              f"of both {pe['within_radius_of_both']:,.0f}, of a bicycle parking point {pe['within_radius_of_mpv_parking']:,.0f}, "
              f"of {pe['study_area']:,.0f} in the study area")
    print(f"\nWrote {out.resolve()} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
