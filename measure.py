#!/usr/bin/env python3
"""
Measure the efficiency of the Baku bus network from the AYNA snapshot.

Settings and data paths come from busnet.toml; every input it names is committed under
data/, so `python3 measure.py` regenerates every result in output/. A missing input is
reported and the matching assumption is used instead.

Writes to ./output/ (or --out):
  repairs.txt          data defects that were fixed automatically before measuring
  routes.csv           one row per route: length, stop spacing, directness, duplication,
                       detours, headway and its source, daily service, fuel, people
                       served, observed boardings
  detours.csv          every detour found, its cost per trip and whom it serves
  corridors.csv        stretches where 8 or more routes share the same links (trunk candidates)
  duplicates.csv       routes whose stops are mostly served by one other route (merge candidates)
  ridership_check.csv  observed against modelled boardings per BakuBus route
  network.json         network-wide indicators, the settings used and which inputs were found
  scenario.json        with --scenario: the same indicators before and after a change

Standard library only. Usage:
  python3 measure.py                                   # everything, as configured in busnet.toml
  python3 measure.py --set default_headway_min=10      # change one assumption for this run
  python3 measure.py --config other.toml               # another settings file
  python3 measure.py --scenario stop-balancing --min-gap 250
"""

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from busnet.inputs import load_inputs                                          # noqa: E402
from busnet.metrics import (compare_ridership, detour_table, near_duplicates,  # noqa: E402
                            network_summary, route_table, trunk_corridors)
from busnet.scenarios import balance_stops                                     # noqa: E402


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: Excel shows ə/ş/ç correctly
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def show(title, summary):
    print(f"\n{title}")
    for k, v in summary.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for k2, v2 in v.items():
                print(f"    {k2:<34} {v2:,.3f}" if isinstance(v2, float) else f"    {k2:<34} {v2}")
        else:
            print(f"  {k:<44} {v:,.3f}" if isinstance(v, float) else f"  {k:<44} {v}")


def split_modelled(summary):
    """Take the per-route modelled boardings out of a summary (too long to print)."""
    acc = summary.get("accessibility")
    return acc.pop("modelled_boardings", None) if acc else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "busnet.toml"), help="settings file (TOML); 'none' for defaults only")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="override one setting or data path for this run; repeatable")
    ap.add_argument("--out", default=str(ROOT / "output"))
    ap.add_argument("--od-origins", type=int, default=300,
                    help="origins sampled for door-to-door accessibility (more is slower and steadier)")
    ap.add_argument("--no-repair", action="store_true", help="measure the raw data without fixing defects")
    ap.add_argument("--scenario", choices=["stop-balancing"])
    ap.add_argument("--min-gap", type=float, default=250, help="stop-balancing: remove stops closer than this (m)")
    ap.add_argument("--max-gap", type=float, default=700, help="stop-balancing: never leave a gap longer than this (m)")
    args = ap.parse_args()

    config = None if args.config.lower() == "none" or not Path(args.config).exists() else args.config
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print(f"Settings: {config or 'built-in defaults'}" + (f" with {len(args.set)} override(s)" if args.set else ""))
    try:
        inp = load_inputs(ROOT, config, args.set, repair=not args.no_repair)
    except (ValueError, TypeError) as e:
        sys.exit(f"Settings error: {e}")
    a, net, zones, observed, headways, attraction = inp.a, inp.network, inp.zones, inp.observed, inp.headways, inp.attraction
    (out / "repairs.txt").write_text("\n".join(net.repairs) + "\n", encoding="utf-8")
    print(f"Loaded {len(net.routes)} routes, {len(net.patterns)} route directions; {len(net.repairs)} repairs")
    if zones:
        print(f"Population zones: {len(zones):,} with {sum(z[2] for z in zones):,.0f} people")
    if observed:
        print(f"Ridership: {len(observed)} routes, weekday means for {inp.observed_month}")
    sources = {s: sum(1 for h in headways.values() if h[1] == s) for s in ("supplied", "ridership", "zone", "default")}
    print(f"Headways by source: {sources}")
    if inp.points:
        print(f"Destinations: {len(inp.points):,} points" + ("" if attraction else " (not used: no population zones)"))

    write_csv(out / "routes.csv", route_table(net, a, zones, observed, headways))
    write_csv(out / "detours.csv", detour_table(net, a, zones))
    write_csv(out / "corridors.csv", [{**c, "stop_ids": " ".join(map(str, c["stop_ids"]))} for c in trunk_corridors(net)])
    write_csv(out / "duplicates.csv", near_duplicates(net))
    summary = network_summary(net, a, zones, args.od_origins if zones else 0, headways, attraction)
    modelled = split_modelled(summary)
    if modelled is not None and observed:
        rows, fit = compare_ridership(net, modelled, observed)
        write_csv(out / "ridership_check.csv", rows)
        summary["ridership_fit"] = fit
    report = {"network": summary, "inputs": inp.found, "settings": asdict(a),
              "headway_sources": sources, "repairs": net.repairs}
    (out / "network.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    show("Network", summary)

    if args.scenario == "stop-balancing":
        new, details = balance_stops(net, args.min_gap, args.max_gap)
        after = network_summary(new, a, zones, args.od_origins if zones else 0, headways, attraction)
        split_modelled(after)
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
