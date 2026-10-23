#!/usr/bin/env python3
"""
Measure the efficiency of the Baku bus network from the AYNA snapshot.

Writes to ./output/ (or --out):
  repairs.txt        data defects that were fixed automatically before measuring
  routes.csv         one row per route: length, stop spacing, directness, duplication,
                     detours, estimated round-trip time and fuel, population served
  detours.csv        every detour found, its cost per trip and whom it serves
  corridors.csv      stretches where 8 or more routes share the same links (trunk candidates)
  duplicates.csv     routes whose stops are mostly served by one other route (merge candidates)
  network.json       network-wide indicators and the assumptions behind them
  scenario.json      with --scenario: the same indicators before and after a change

Standard library only. Usage:
  python3 measure.py                                   # geometry, time and fuel metrics
  python3 measure.py --population data/external/kontur/kontur_population_AZ.gpkg
                                                       # adds coverage and door-to-door access
  python3 measure.py --population ... --scenario stop-balancing --min-gap 250
"""

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from busnet import Assumptions, load_network                                  # noqa: E402
from busnet.metrics import (detour_table, near_duplicates, network_summary,  # noqa: E402
                            route_table, trunk_corridors)
from busnet.population import load_population, stops_bbox                     # noqa: E402
from busnet.scenarios import balance_stops                                     # noqa: E402


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: Excel shows ə/ş/ç correctly
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})


def show(title, summary):
    print(f"\n{title}")
    for k, v in summary.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for k2, v2 in v.items():
                print(f"    {k2:<34} {v2:,.3f}" if isinstance(v2, float) else f"    {k2:<34} {v2}")
        else:
            print(f"  {k:<44} {v:,.3f}" if isinstance(v, float) else f"  {k:<44} {v}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="data/ayna.db")
    ap.add_argument("--population", help="population grid (.gpkg or .csv) for coverage and accessibility")
    ap.add_argument("--out", default="output")
    ap.add_argument("--od-origins", type=int, default=300,
                    help="origins sampled for door-to-door accessibility (more is slower and steadier)")
    ap.add_argument("--no-repair", action="store_true", help="measure the raw data without fixing defects")
    ap.add_argument("--scenario", choices=["stop-balancing"])
    ap.add_argument("--min-gap", type=float, default=250, help="stop-balancing: remove stops closer than this (m)")
    ap.add_argument("--max-gap", type=float, default=700, help="stop-balancing: never leave a gap longer than this (m)")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    a = Assumptions()
    t0 = time.time()

    net = load_network(args.db, repair=not args.no_repair)
    (out / "repairs.txt").write_text("\n".join(net.repairs) + "\n", encoding="utf-8")
    print(f"Loaded {len(net.routes)} routes, {len(net.patterns)} route directions; {len(net.repairs)} repairs")

    zones = None
    if args.population:
        zones = load_population(args.population, stops_bbox(net))
        print(f"Population zones: {len(zones):,} with {sum(z[2] for z in zones):,.0f} people")

    rows = route_table(net, a, zones)
    write_csv(out / "routes.csv", rows)
    write_csv(out / "detours.csv", detour_table(net, a, zones))
    write_csv(out / "corridors.csv", [{**c, "stop_ids": " ".join(map(str, c["stop_ids"]))} for c in trunk_corridors(net)])
    write_csv(out / "duplicates.csv", near_duplicates(net))
    summary = network_summary(net, a, zones, args.od_origins if zones else 0)
    report = {"network": summary, "assumptions": asdict(a), "repairs": net.repairs}
    (out / "network.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    show("Network", summary)

    if args.scenario == "stop-balancing":
        new, details = balance_stops(net, args.min_gap, args.max_gap)
        after = network_summary(new, a, zones, args.od_origins if zones else 0)
        removed = details.pop("removed_stops")
        details["removed_stops"] = len(removed)
        result = {"scenario": "stop-balancing", "details": details, "before": summary, "after": after}
        (out / "scenario.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        write_csv(out / "scenario_removed_stops.csv",
                  [{"stop_id": s, "name": net.stops[s].name, "lat": net.stops[s].lat, "lon": net.stops[s].lon}
                   for s in removed])
        show(f"After stop balancing ({details['removed_stops']} stops, {details['removed_stop_visits']} stop visits removed)",
             after)

    print(f"\nWrote {out.resolve()} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
