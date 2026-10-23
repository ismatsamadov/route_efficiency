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

from busnet import load_network                                               # noqa: E402
from busnet.config import load_config                                          # noqa: E402
from busnet.destinations import metro_points, osm_points, zone_attraction      # noqa: E402
from busnet.metrics import (compare_ridership, detour_table, near_duplicates,  # noqa: E402
                            network_summary, route_table, trunk_corridors)
from busnet.population import load_population, stops_bbox                     # noqa: E402
from busnet.ridership import latest_month, load_daily_boardings, weekday_mean  # noqa: E402
from busnet.scenarios import balance_stops                                     # noqa: E402
from busnet.service import load_headways, route_headways                       # noqa: E402


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


def available(path, what, inputs):
    """True if the file exists; otherwise note that an assumption stands in for it."""
    ok = bool(path) and Path(path).exists()
    inputs[what] = str(Path(path).relative_to(ROOT)) if ok and Path(path).is_relative_to(ROOT) else (path if ok else None)
    if path and not ok:
        print(f"  missing {what}: {path} (using assumptions instead)")
    return ok


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
    try:
        a, data = load_config(config, args.set)
    except (ValueError, TypeError) as e:
        sys.exit(f"Settings error: {e}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    inputs = {}
    print(f"Settings: {config or 'built-in defaults'}" + (f" with {len(args.set)} override(s)" if args.set else ""))

    db = data.get("db", str(ROOT / "data" / "ayna.db"))
    available(db, "db", inputs)
    net = load_network(db, repair=not args.no_repair)
    (out / "repairs.txt").write_text("\n".join(net.repairs) + "\n", encoding="utf-8")
    print(f"Loaded {len(net.routes)} routes, {len(net.patterns)} route directions; {len(net.repairs)} repairs")

    zones = None
    if available(data.get("population"), "population", inputs):
        zones = load_population(data["population"], stops_bbox(net))
        print(f"Population zones: {len(zones):,} with {sum(z[2] for z in zones):,.0f} people")
    observed = None
    if available(data.get("ridership"), "ridership", inputs):
        daily = load_daily_boardings(data["ridership"])
        year, month = latest_month(daily)
        observed = weekday_mean(daily, year, month)
        print(f"Ridership: {len(observed)} routes, weekday means for {year}-{month:02d}")
    supplied = load_headways(data["headways"]) if available(data.get("headways"), "headways", inputs) else None
    headways = route_headways(net, a, observed, supplied)
    sources = {s: sum(1 for h in headways.values() if h[1] == s) for s in ("supplied", "ridership", "zone", "default")}
    print(f"Headways by source: {sources}")

    points = []
    found = [p for p in data.get("destinations", []) if available(p, f"destinations:{Path(p).name}", inputs)]
    if found:
        points += osm_points(found, a.destination_weights)
    if available(data.get("metro_passengers"), "metro_passengers", inputs) and \
            available(data.get("metro_exits"), "metro_exits", inputs):
        metro, unmatched = metro_points(data["metro_passengers"], data["metro_exits"], a.metro_weight_per_1000_entries)
        points += metro
        if unmatched:
            print(f"  metro stations without exit coordinates: {', '.join(unmatched)}")
    attraction = zone_attraction(zones, points, a.destination_share) if zones else None
    if points:
        print(f"Destinations: {len(points):,} points" + ("" if attraction else " (not used: no population zones)"))

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
    report = {"network": summary, "inputs": inputs, "settings": asdict(a),
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
