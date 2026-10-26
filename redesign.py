#!/usr/bin/env python3
"""
Search for a better Baku bus network with today's fleet, and report what changed.

Reads the same settings and data as measure.py (busnet.toml; search settings are in its
[redesign] table). The search keeps a change only if it shortens the average door-to-door
trip without cutting people off from bus service; the result is then checked on a
different, finer sample of trips than the search used.

Writes to ./output/redesign/ (or --out):
  changes.csv        every change kept, in order, with its effect on average door-to-door time
  routes.csv         each route before and after: kept, straightened, merged or dropped; riders, buses, headway, length
  summary.json       riders, operator and network measures before and after (the independent check),
                     and how much of the fleet would give today's travel times
  network.geojson    redesigned routes and dropped routes, for any map tool (GitHub draws it)
  gtfs_today.zip     today's network as GTFS, with the estimated headways
  gtfs_redesign.zip  the redesigned network as GTFS

Standard library only. Usage:
  python3 redesign.py
  python3 redesign.py --set redesign_origins=200     # larger, slower search sample
  python3 redesign.py --set redesign_max_people_losing_stop=0
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

from busnet.destinations import zone_attraction                                # noqa: E402
from busnet.gtfs import write_gtfs                                             # noqa: E402
from busnet.inputs import load_inputs                                          # noqa: E402
from busnet.metrics import evaluate_od, network_summary                        # noqa: E402
from busnet.optimize import Context, Evaluator, Plan, fleet_for_same_time, search  # noqa: E402
from busnet.population import load_population, stops_bbox                     # noqa: E402
from busnet.service import operations                                          # noqa: E402


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def route_rows(before, after, a, log, riders, counted, protected):
    kinds = {}
    for change in log:
        for n in change["routes"].split():
            kinds.setdefault(n, []).append(change["kind"])
    hb, ha = before.headways(a), after.headways(a)
    rows = []
    for rid in sorted(before.fleet, key=lambda r: (len(before.network.number(r)), before.network.number(r))):
        n = before.network.number(rid)
        dropped = rid not in after.fleet
        straight = "straighten" in kinds.get(n, [])
        km = lambda plan: sum(p.length_m for p in plan.by_route[rid]) / len(plan.by_route[rid]) / 1000
        rows.append({
            "route": n,
            "status": ("merged" if "merge" in kinds.get(n, []) else "dropped") if dropped else ("straightened" if straight else "kept"),
            "protected": rid in protected,
            "boardings_per_day": riders.get(rid, 0.0),
            "boardings_source": "counted" if rid in counted else "estimated",
            "buses_before": before.fleet[rid], "buses_after": 0.0 if dropped else after.fleet[rid],
            "headway_min_before": hb[rid][0], "headway_min_after": None if dropped else ha[rid][0],
            "one_way_km_before": km(before), "one_way_km_after": None if dropped else km(after),
        })
    return rows


def geojson(before, after):
    features = []
    for (rid, d), p in sorted(before.network.patterns.items()):
        n = before.network.number(rid)
        if rid in after.fleet:
            new = after.network.patterns[(rid, d)]
            status = "straightened" if new.path != p.path else "kept"      # stop balancing keeps the path
            p = new
        else:
            status = "dropped"
        features.append({"type": "Feature",
                         "properties": {"route": n, "direction": d, "status": status,
                                        "stroke": {"kept": "#2a78d6", "straightened": "#1baf7a", "dropped": "#d03b3b"}[status]},
                         "geometry": {"type": "LineString", "coordinates": [[round(lon, 6), round(lat, 6)] for lat, lon in p.path]}})
    return {"type": "FeatureCollection", "features": features}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "busnet.toml"), help="settings file (TOML); 'none' for defaults only")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="override one setting for this run")
    ap.add_argument("--out", default=str(ROOT / "output" / "redesign"))
    args = ap.parse_args()

    config = None if args.config.lower() == "none" or not Path(args.config).exists() else args.config
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        inp = load_inputs(ROOT, config, args.set, split=False)
    except (ValueError, TypeError) as e:
        sys.exit(f"Settings error: {e}")
    a, net = inp.a, inp.network
    if not inp.zones:
        sys.exit("The redesign needs population data: set data.population in busnet.toml")
    fine = load_population(inp.data["population"], stops_bbox(net), split=True)
    fine_pull = zone_attraction(fine, inp.points, a.destination_share)

    today = Plan.from_headways(net, a, inp.headways)
    print(f"Today: {len(today.fleet)} routes, {today.total_fleet():,.0f} buses in service (estimated)")
    evaluator = Evaluator(net, a, inp.zones, inp.attraction, coverage_zones=fine,
                          n_origins=a.redesign_origins, seed=a.redesign_seed)
    ctx = Context(net, a, evaluator, observed=inp.observed)
    if ctx.protected:
        print(f"Protected routes: {', '.join(sorted(net.number(r) for r in ctx.protected))}")
    print(f"Searching ({a.redesign_origins} sample origins):")
    plan, log, before, after = search(today, evaluator, ctx)
    share = fleet_for_same_time(plan, evaluator, before["minutes"])
    print(f"Search done in {time.time() - t0:.0f}s: {len(log)} changes; "
          f"{before['minutes']:.2f} -> {after['minutes']:.2f} min on the search sample")

    print("Checking on an independent sample (finer zones, different origins) ...")
    check_before = network_summary(today.network, a, fine, 300, today.headways(a), fine_pull)
    check_after = network_summary(plan.network, a, fine, 300, plan.headways(a), fine_pull)
    for s in (check_before, check_after):
        s["accessibility"].pop("modelled_boardings", None)

    def capped(acc):
        """Average door-to-door minutes, counting trips that cannot be made in time at the limit."""
        r = acc["share_reachable"]
        return r * acc["mean_door_to_door_min"] + (1 - r) * a.max_trip_min

    target = capped(check_before["accessibility"])
    fleet_share = 1.0
    if capped(check_after["accessibility"]) < target:          # how far could the fleet shrink instead?
        lo, hi = 0.5, 1.0
        for _ in range(6):
            mid = (lo + hi) / 2
            scaled = plan.changed(fleet={r: f * mid for r, f in plan.fleet.items()})
            acc = evaluate_od(scaled.network, a, fine, 300, headways=scaled.headways(a), attraction=fine_pull)
            hi, lo = (mid, lo) if capped(acc) <= target else (hi, mid)
        fleet_share = hi
    saving_plan = plan.changed(fleet={r: f * fleet_share for r, f in plan.fleet.items()})
    saving_ops = operations(saving_plan.network, a, saving_plan.headways(a))[1]

    keep = ["served_stops", "route_km_one_way_total", "corridor_km", "duplication_ratio", "median_stop_gap_m",
            "share_stop_gaps_under_300m", "share_population_covered"]
    summary = {
        "fleet_buses": today.total_fleet(),
        "routes_before": len(today.fleet), "routes_after": len(plan.fleet),
        "changes": {k: sum(1 for c in log if c["kind"] == k) for k in ("merge", "drop", "straighten", "stops", "shift")},
        "search_sample": {"origins": a.redesign_origins, "seed": a.redesign_seed,
                          "minutes_before": before["minutes"], "minutes_after": after["minutes"],
                          "unreachable_before": before["unreachable"], "unreachable_after": after["unreachable"]},
        "minutes_counting_impossible_trips_at_limit": {"before": target, "after": capped(check_after["accessibility"])},
        "share_of_fleet_for_todays_travel_time": {"independent_check": fleet_share, "search_sample": share},
        "fleet_saving_option": {"buses": saving_plan.total_fleet(), "operations": saving_ops},
        "independent_check": {
            "before": {"accessibility": check_before["accessibility"], "operations": check_before["operations"],
                       **{k: check_before[k] for k in keep}},
            "after": {"accessibility": check_after["accessibility"], "operations": check_after["operations"],
                      **{k: check_after[k] for k in keep}},
        },
        "settings": asdict(a), "inputs": inp.found,
    }
    write_csv(out / "changes.csv", log)
    riders_today = ctx.riders_for(today, before["boardings"])
    write_csv(out / "routes.csv", route_rows(today, plan, a, log, riders_today, ctx.observed, ctx.protected))
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "network.geojson").write_text(json.dumps(geojson(today, plan), ensure_ascii=False), encoding="utf-8")
    write_gtfs(out / "gtfs_today.zip", today.network, a, today.headways(a), "today")
    write_gtfs(out / "gtfs_redesign.zip", plan.network, a, plan.headways(a), "redesign")

    b, f = check_before["accessibility"], check_after["accessibility"]
    print(f"\nIndependent check, before -> after:")
    print(f"  mean door-to-door (trips possible)  {b['mean_door_to_door_min']:.1f} -> {f['mean_door_to_door_min']:.1f} min")
    print(f"  trips possible within 45 min        {b['share_within_45_min']:.1%} -> {f['share_within_45_min']:.1%}")
    print(f"  trips possible within 2 hours       {b['share_reachable']:.1%} -> {f['share_reachable']:.1%}")
    print(f"  people within 400 m of a stop       {check_before['share_population_covered']:.2%} -> {check_after['share_population_covered']:.2%}")
    print(f"  bus-km a day                        {check_before['operations']['bus_km_per_day']:,.0f} -> {check_after['operations']['bus_km_per_day']:,.0f}")
    print(f"  fuel a day (L)                      {check_before['operations']['fuel_l_per_day']:,.0f} -> {check_after['operations']['fuel_l_per_day']:,.0f}")
    before_ops = check_before["operations"]
    print(f"\nOr keep today's travel times with {fleet_share:.0%} of the fleet "
          f"({before_ops['fleet'] - saving_ops['fleet']:,} fewer buses, rounded up per route):")
    print(f"  fuel a day (L)                      {before_ops['fuel_l_per_day']:,.0f} -> {saving_ops['fuel_l_per_day']:,.0f}")
    print(f"  CO2 a day (t)                       {before_ops['co2_t_per_day']:,.0f} -> {saving_ops['co2_t_per_day']:,.0f}")
    print(f"  bus-hours a day                     {before_ops['bus_hours_per_day']:,.0f} -> {saving_ops['bus_hours_per_day']:,.0f}")
    print(f"\nWrote {out.resolve()} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
